import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from src.adb import ADB
from src.tc_loader import load_tc, TCValidationError
from src.action_runner import ActionRunner, ManualStepAction, ManualStepContext
from src.reporter import Reporter, TCResult
from src.excel_converter import convert_excel_to_yaml
from src.mmi_converter.row_loader import load_mmi_rows
from src.mmi_converter.service import MMIConversionService
from src.mmi_converter.exporter import YAMLExporter, check_runnable


def _terminal_manual_handler(ctx: ManualStepContext) -> ManualStepAction:
    mode = ctx.execution_mode
    desc = ctx.step.get("description", ctx.step.get("text", ""))
    timeout = ctx.timeout_seconds or 300

    print(f"\n  !! [{mode}] 수동 개입 필요:")
    print(f"     {desc}")
    print(f"     제한 시간: {timeout}초")
    print(f"     [c] 계속  [s] 건너뛰기  [f] 실패 처리")

    while True:
        try:
            choice = input("     선택: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ManualStepAction(decision="fail")
        if choice in ("c", "continue", ""):
            return ManualStepAction(decision="continue")
        if choice in ("s", "skip"):
            reason = input("     사유: ").strip()
            return ManualStepAction(decision="skip", reason=reason)
        if choice in ("f", "fail"):
            return ManualStepAction(decision="fail")


def _resolve_tc_files(patterns: list[str]) -> tuple[list[Path], list[Path]]:
    """입력 패턴들을 YAML 파일 목록으로 변환한다.

    .xlsx 파일은 임시 디렉토리에 YAML로 변환한다.

    Returns:
        (tc_files, temp_dirs) — 실행할 YAML 파일 목록과 정리할 임시 디렉토리 목록
    """
    tc_files = []
    temp_dirs = []

    for pattern in patterns:
        path = Path(pattern)

        if path.suffix.lower() == ".xlsx" and path.is_file():
            tmp_dir = Path(tempfile.mkdtemp(prefix="tc_runner_"))
            temp_dirs.append(tmp_dir)
            try:
                converted = convert_excel_to_yaml(path, tmp_dir)
                print(f"엑셀 변환: {path.name} → {len(converted)}개 T/C")
                tc_files.extend(converted)
            except Exception as e:
                print(f"WARNING: 엑셀 변환 실패 ({path.name}) — {e}")
        elif path.is_file():
            tc_files.append(path)
        else:
            tc_files.extend(Path(".").glob(pattern))

    return tc_files, temp_dirs


def cmd_run(args):
    """T/C 실행 커맨드."""
    adb = ADB()

    if not adb.is_connected():
        print("ERROR: ADB에 연결된 단말이 없습니다.")
        print("USB 케이블과 USB 디버깅 설정을 확인해주세요.")
        sys.exit(1)

    report_dir = Path("reports")
    screenshot_dir = report_dir / "screenshots"
    reporter = Reporter(report_dir=report_dir)
    reporter.device_info = adb.get_device_info()
    runner = ActionRunner(adb=adb, screenshot_dir=screenshot_dir,
                         on_manual_step=_terminal_manual_handler)

    tc_files, temp_dirs = _resolve_tc_files(args.tc_files)

    if not tc_files:
        for d in temp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        print("ERROR: T/C 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"Device: {reporter.device_info.get('model', '?')} "
          f"(Android {reporter.device_info.get('android_version', '?')})")
    print(f"T/C files: {len(tc_files)}")

    try:
        for tc_file in tc_files:
            try:
                tc_data = load_tc(tc_file)
            except TCValidationError as e:
                print(f"\nSKIP: {tc_file} — {e}")
                continue

            reporter.print_tc_header(tc_data["name"])
            tc_result = TCResult(
                name=tc_data["name"],
                description=tc_data.get("description", ""),
            )

            for i, step in enumerate(tc_data["steps"]):
                step_result = runner.run_step(step)
                tc_result.steps.append(step_result)
                reporter.print_step(tc_data["name"], i, step_result)

                # verify action 실패 시 이 T/C 중단, 다음 T/C로
                if not step_result.passed and step["action"].startswith("verify"):
                    break

            reporter.print_tc_result(tc_result)
            reporter.results.append(tc_result)

        if not reporter.results:
            print("\nERROR: 실행된 T/C가 없습니다.")
            sys.exit(1)

        reporter.print_summary()
        try:
            html_path = reporter.generate_html()
            print(f"\nHTML report: {html_path}")
        except Exception as e:
            print(f"\nWARNING: HTML 리포트 생성 실패 — {e}")
    finally:
        for d in temp_dirs:
            shutil.rmtree(d, ignore_errors=True)


def cmd_convert(args):
    """엑셀 → YAML 변환 커맨드."""
    xlsx_path = Path(args.xlsx_file)
    if not xlsx_path.exists():
        print(f"ERROR: 파일을 찾을 수 없습니다: {xlsx_path}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else Path("tc_samples")
    files = convert_excel_to_yaml(xlsx_path, output_dir)
    print(f"변환 완료: {len(files)}개 T/C 파일 생성")
    for f in files:
        print(f"  → {f}")


def cmd_devices(args):
    """연결된 단말 확인 커맨드."""
    adb = ADB()
    if adb.is_connected():
        info = adb.get_device_info()
        print(f"Connected: {info.get('model', '?')} (Android {info.get('android_version', '?')})")
    else:
        print("연결된 단말이 없습니다.")


def _parse_row_filter(rows_arg: str | None, total: int) -> set[int] | None:
    """--rows 인자를 파싱하여 인덱스 set을 반환한다."""
    if not rows_arg:
        return None
    indices = set()
    for part in rows_arg.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            indices.update(range(int(start), int(end) + 1))
        else:
            indices.add(int(part))
    return indices


def cmd_preview_mmi(args):
    """MMI 엑셀 T/C 변환 미리보기."""
    xlsx_path = Path(args.xlsx_file)
    if not xlsx_path.exists():
        print(f"ERROR: {xlsx_path} not found")
        sys.exit(1)

    try:
        rows = load_mmi_rows(xlsx_path, sheet_name=args.sheet)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not rows:
        print("ERROR: No rows loaded")
        sys.exit(1)

    svc = MMIConversionService()
    row_filter = _parse_row_filter(args.rows, len(rows))

    stats = {"FULL_AUTO": 0, "SEMI_AUTO": 0, "MANUAL_REQUIRED": 0, "AMBIGUOUS_NL": 0, "OUT_OF_SCOPE": 0}
    warning_count = 0
    displayed = 0

    for i, row in enumerate(rows, 1):
        if row_filter and i not in row_filter:
            continue

        preview = svc.convert_row(row)
        stats[preview.automation_class] = stats.get(preview.automation_class, 0) + 1

        if preview.warnings:
            warning_count += 1

        if args.only_class and preview.automation_class != args.only_class:
            continue

        if args.show_warnings_only and not preview.warnings:
            continue

        if args.limit and displayed >= args.limit:
            continue

        displayed += 1

        # 출력
        class_label = preview.automation_class
        print(f"\n{'='*60}")
        print(f"  [{i}] {preview.tc_name}  [{class_label}]")
        print(f"{'='*60}")
        print(f"  Procedure : {preview.source_procedure[:120]}")
        print(f"  Expected  : {preview.source_expected[:100]}")

        if preview.parsed_intents:
            print(f"  Intents   :")
            for intent in preview.parsed_intents:
                extra = f" target={intent.target}" if intent.target else ""
                extra += f" value={intent.value}" if intent.value else ""
                print(f"    - {intent.type}{extra}")

        if preview.classified_intents:
            print(f"  Step Classes:")
            for ci in preview.classified_intents:
                extra = f" target={ci.intent.target}" if ci.intent.target else ""
                print(f"    - [{ci.execution_mode}|{ci.step_role}] {ci.intent.type}{extra}")

        if preview.compiled_steps:
            print(f"  Steps     :")
            for step in preview.compiled_steps:
                print(f"    - {step}")

        if preview.warnings:
            print(f"  Warnings  :")
            for w in preview.warnings:
                print(f"    ! {w[:100]}")

        if preview.reasons:
            print(f"  Reasons   : {'; '.join(preview.reasons)}")

    # 요약
    total = sum(stats.values())
    print(f"\n{'='*60}")
    print(f"  SUMMARY ({total} rows)")
    print(f"{'='*60}")
    for cls, cnt in stats.items():
        if cnt > 0:
            pct = cnt / total * 100 if total else 0
            print(f"  {cls:20s}: {cnt:4d} ({pct:.1f}%)")
    print(f"  {'Warnings':20s}: {warning_count:4d}")
    print(f"  {'Displayed':20s}: {displayed:4d}")


def cmd_export_mmi(args):
    """MMI 엑셀 T/C 변환 및 YAML export."""
    xlsx_path = Path(args.xlsx_file)
    if not xlsx_path.exists():
        print(f"ERROR: {xlsx_path} not found")
        sys.exit(1)

    try:
        rows = load_mmi_rows(xlsx_path, sheet_name=args.sheet)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not rows:
        print("ERROR: No rows loaded")
        sys.exit(1)

    svc = MMIConversionService()
    previews = []
    for row in rows:
        preview = svc.convert_row(row)
        previews.append((row, preview))

    # Filter by class
    target_classes = {"FULL_AUTO"}
    if args.include_semi:
        target_classes.add("SEMI_AUTO")
    if args.only_class:
        target_classes = {args.only_class}

    filtered = [(r, p) for r, p in previews if p.automation_class in target_classes]

    if args.dry_run:
        for _, preview in filtered:
            runnable, issues = check_runnable(preview)
            status = "RUNNABLE" if runnable else "UNRUNNABLE"
            print(f"  [{status}] {preview.tc_name} [{preview.automation_class}]")
            for issue in issues:
                print(f"    ! {issue}")
        print(f"\nTotal: {len(filtered)} TCs")
        return

    # Check runnable (fail-fast)
    unrunnable = [(r, p) for r, p in filtered if not check_runnable(p)[0]]
    if unrunnable and not args.skip_unrunnable and not args.export_unrunnable:
        print(f"Export aborted: unrunnable TC {len(unrunnable)}개 발견")
        for _, p in unrunnable:
            _, issues = check_runnable(p)
            print(f"  {p.tc_name}: {'; '.join(issues)}")
        print(f"\n힌트:")
        print(f"  --skip-unrunnable         제외하고 계속 진행")
        print(f"  --export-unrunnable       placeholder 포함 export")
        sys.exit(1)

    if args.skip_unrunnable:
        filtered = [(r, p) for r, p in filtered if check_runnable(p)[0]]

    output_dir = Path(args.output_dir)
    exporter = YAMLExporter(output_dir=output_dir, overwrite=args.overwrite)

    created = 0
    skipped = 0
    for row, preview in filtered:
        path = exporter.export_one(
            preview,
            source_file=xlsx_path.name,
            source_sheet=args.sheet,
            source_row=row.row_index,
        )
        if path:
            created += 1
        else:
            skipped += 1

    print(f"\nExport 완료:")
    print(f"  생성      : {created}개")
    print(f"  건너뜀    : {skipped}개")
    print(f"  출력 디렉토리: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Android T/C 자동 실행 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="T/C 실행")
    run_parser.add_argument("tc_files", nargs="+", help="YAML 또는 엑셀(.xlsx) T/C 파일 경로")
    run_parser.set_defaults(func=cmd_run)

    # convert
    convert_parser = subparsers.add_parser("convert", help="엑셀 → YAML 변환")
    convert_parser.add_argument("xlsx_file", help="엑셀 파일 경로")
    convert_parser.add_argument("-o", "--output", help="출력 디렉토리 (기본: tc_samples/)")
    convert_parser.set_defaults(func=cmd_convert)

    # devices
    devices_parser = subparsers.add_parser("devices", help="연결된 단말 확인")
    devices_parser.set_defaults(func=cmd_devices)

    # preview-mmi
    preview_parser = subparsers.add_parser("preview-mmi", help="MMI 엑셀 T/C 변환 미리보기")
    preview_parser.add_argument("xlsx_file", help="MMI 엑셀 파일 경로")
    preview_parser.add_argument("--sheet", default="ODIN 기본기능 TC(MMI 내용추가)(4번)", help="시트명")
    preview_parser.add_argument("--rows", help="행 범위 (예: 1-20, 5,10,15)")
    preview_parser.add_argument("--only-class", help="분류 필터 (예: FULL_AUTO, SEMI_AUTO, MANUAL_REQUIRED)")
    preview_parser.add_argument("--limit", type=int, help="최대 출력 건수")
    preview_parser.add_argument("--show-warnings-only", action="store_true", help="경고가 있는 건만 출력")
    preview_parser.set_defaults(func=cmd_preview_mmi)

    # export-mmi
    export_parser = subparsers.add_parser("export-mmi", help="MMI 엑셀 T/C → YAML export")
    export_parser.add_argument("xlsx_file", help="MMI 엑셀 파일 경로")
    export_parser.add_argument("--sheet", default="ODIN 기본기능 TC(MMI 내용추가)(4번)", help="시트명")
    export_parser.add_argument("--output-dir", default="exported", help="출력 디렉토리")
    export_parser.add_argument("--dry-run", action="store_true", help="미리보기만 (파일 생성 없음)")
    export_parser.add_argument("--only-class", help="분류 필터")
    export_parser.add_argument("--include-semi", action="store_true", help="SEMI_AUTO도 포함")
    export_parser.add_argument("--skip-unrunnable", action="store_true", help="unrunnable 제외")
    export_parser.add_argument("--export-unrunnable", action="store_true", help="unrunnable도 export")
    export_parser.add_argument("--overwrite", action="store_true", help="기존 파일 덮어쓰기")
    export_parser.set_defaults(func=cmd_export_mmi)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
