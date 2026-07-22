import argparse
import io
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Windows 콘솔 UTF-8 강제
if sys.platform == "win32":
    os.system("")  # enable ANSI/VT100
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.adb import ADB
from src.tc_loader import load_tc, TCValidationError
from src.action_runner import ActionRunner, ManualStepAction, ManualStepContext
from src.reporter import Reporter, TCResult
from src.excel_converter import convert_excel_to_yaml
from src.mmi_converter.row_loader import load_mmi_rows
from src.mmi_converter.service import MMIConversionService
from src.mmi_converter.exporter import YAMLExporter, check_runnable
from src.app_explorer import AppExplorer
from src import preflight as preflight_mod
from src import catalog as catalog_mod
from src import catalog_delta as catalog_delta_mod
from src.catalog_delta import validate_run_id_for_filename


def _timed_input(prompt: str, timeout: int) -> str | None:
    """timeout 초 이내에 한 줄 입력을 받는다. 초과 시 None 반환.

    Windows에서는 msvcrt로 non-blocking 처리하여 daemon thread의
    stdin 점유 문제를 방지한다.
    """
    print(prompt, end='', flush=True)

    if sys.platform == "win32":
        import msvcrt
        chars: list[str] = []
        start = time.time()
        while time.time() - start < timeout:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ('\r', '\n'):
                    print()
                    return ''.join(chars)
                if ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                if ch == '\x08':  # Backspace
                    if chars:
                        chars.pop()
                        print('\b \b', end='', flush=True)
                    continue
                chars.append(ch)
                print(ch, end='', flush=True)
            time.sleep(0.1)
        print()
        return None
    else:
        import select
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.readline()
        print()
        return None


def _terminal_manual_handler(ctx: ManualStepContext) -> ManualStepAction:
    mode = ctx.execution_mode
    desc = ctx.step.get("description", ctx.step.get("text", ""))
    timeout = ctx.timeout_seconds or 300

    print(f"\n  !! [{mode}] 수동 개입 필요:")
    print(f"     {desc}")
    print(f"     제한 시간: {timeout}초")
    print(f"     [c] 계속  [s] 건너뛰기  [f] 실패 처리")

    deadline = time.time() + timeout
    while True:
        remaining = int(deadline - time.time())
        if remaining <= 0:
            print("     시간 초과")
            return ManualStepAction(decision="fail", reason=f"timeout ({timeout}s)")

        try:
            raw = _timed_input("     선택: ", remaining)
        except (EOFError, KeyboardInterrupt):
            return ManualStepAction(decision="fail")

        if raw is None:
            print("     시간 초과")
            return ManualStepAction(decision="fail", reason=f"timeout ({timeout}s)")

        choice = raw.strip().lower()
        if choice in ("c", "continue", ""):
            return ManualStepAction(decision="continue")
        if choice in ("s", "skip"):
            reason_raw = _timed_input("     사유: ", min(remaining, 60))
            reason = reason_raw.strip() if reason_raw else ""
            return ManualStepAction(decision="skip", reason=reason)
        if choice in ("f", "fail"):
            return ManualStepAction(decision="fail")


def _resolve_tc_files(
    patterns: list[str], *, strict: bool = False
) -> tuple[list[Path], list[Path]]:
    """입력 패턴들을 YAML 파일 목록으로 변환한다.

    .xlsx 파일은 임시 디렉토리에 YAML로 변환한다.

    Returns:
        (tc_files, temp_dirs) — 실행할 YAML 파일 목록과 정리할 임시 디렉토리 목록
    """
    tc_files = []
    temp_dirs = []

    def cleanup_temp_dirs() -> None:
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dirs.clear()

    for pattern in patterns:
        path = Path(pattern)

        if path.suffix.lower() == ".xlsx" and path.is_file():
            tmp_dir = Path(tempfile.mkdtemp(prefix="tc_runner_"))
            temp_dirs.append(tmp_dir)
            try:
                converted = convert_excel_to_yaml(path, tmp_dir)
                if strict and not converted:
                    raise TCValidationError(
                        f"{path}: 엑셀에서 변환된 T/C가 없습니다."
                    )
                print(f"엑셀 변환: {path.name} → {len(converted)}개 T/C")
                tc_files.extend(converted)
            except Exception as e:
                if strict:
                    cleanup_temp_dirs()
                    raise TCValidationError(
                        f"{path}: 엑셀 변환 실패 — {e}"
                    ) from e
                print(f"WARNING: 엑셀 변환 실패 ({path.name}) — {e}")
        elif path.is_file():
            tc_files.append(path)
        else:
            try:
                matched = list(Path(".").glob(pattern))
            except Exception as e:
                if strict:
                    cleanup_temp_dirs()
                    raise TCValidationError(
                        f"입력 패턴 해석 실패: {pattern} — {e}"
                    ) from e
                raise
            if strict and not matched:
                cleanup_temp_dirs()
                raise TCValidationError(f"입력 패턴과 일치하는 파일이 없습니다: {pattern}")
            tc_files.extend(matched)

    return tc_files, temp_dirs


@dataclass(frozen=True)
class PreflightVerdict:
    path: Path
    passed: bool
    reasons: tuple[str, ...]
    tc_data: dict | None = None


@dataclass(frozen=True)
class PreflightReport:
    verdicts: tuple[PreflightVerdict, ...]

    @property
    def passed(self) -> bool:
        return bool(self.verdicts) and all(
            verdict.passed for verdict in self.verdicts
        )

    @property
    def loaded_tcs(self) -> tuple[tuple[Path, dict], ...]:
        """Return execution inputs only when the complete invocation passed."""
        if not self.passed:
            return ()
        return tuple(
            (verdict.path, verdict.tc_data)
            for verdict in self.verdicts
            if verdict.tc_data is not None
        )


def _canonical_gate_reasons(tc_data: dict) -> tuple[str, ...]:
    reasons: list[str] = []
    metadata = tc_data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    if metadata.get("runnable") is not True:
        reasons.append("NOT_RUNNABLE")
    if metadata.get("runnable_reason"):
        reasons.append("RUNNABLE_REASON_PRESENT")
    if metadata.get("has_unresolved_params") is True:
        reasons.append("METADATA_UNRESOLVED_PARAMS")
    if metadata.get("compile_status") == "UNRESOLVED_PARAMS":
        reasons.append("METADATA_UNRESOLVED_COMPILE_STATUS")
    if metadata.get("_unresolved_params"):
        reasons.append("METADATA_UNRESOLVED_PARAM_DETAILS")

    if tc_data.get("compile_status") == "UNRESOLVED_PARAMS":
        reasons.append("TOPLEVEL_UNRESOLVED_COMPILE_STATUS")
    if tc_data.get("_unresolved_params"):
        reasons.append("TOPLEVEL_UNRESOLVED_PARAMS")

    steps = tc_data.get("steps")
    if isinstance(steps, list):
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if step.get("compile_status") == "UNRESOLVED_PARAMS":
                reasons.append(f"STEP_UNRESOLVED_COMPILE_STATUS:{index + 1}")
            if step.get("_unresolved_params"):
                reasons.append(f"STEP_UNRESOLVED_PARAMS:{index + 1}")

    return tuple(reasons)


def host_preflight(
    tc_files: tuple[Path, ...] | list[Path],
    contract_mode: Literal["legacy", "canonical"],
) -> PreflightReport:
    """Resolve loader/contract acceptance without constructing or calling ADB."""
    if contract_mode not in ("legacy", "canonical"):
        raise ValueError(f"unsupported contract_mode: {contract_mode!r}")

    verdicts: list[PreflightVerdict] = []
    for source in tc_files:
        path = Path(source)
        try:
            tc_data = load_tc(path, contract_mode=contract_mode)
        except Exception as exc:
            reason = (
                "CANONICAL_LOAD_OR_VALIDATION_ERROR:"
                f"{type(exc).__name__}:{exc}"
            )
            verdicts.append(
                PreflightVerdict(
                    path=path,
                    passed=False,
                    reasons=(reason,),
                )
            )
            continue

        reasons = (
            _canonical_gate_reasons(tc_data)
            if contract_mode == "canonical"
            else ()
        )
        verdicts.append(
            PreflightVerdict(
                path=path,
                passed=not reasons,
                reasons=reasons,
                tc_data=tc_data,
            )
        )

    return PreflightReport(verdicts=tuple(verdicts))


def cmd_run(args):
    """T/C 실행 커맨드."""
    contract_mode = getattr(args, "contract_mode", "legacy")
    if contract_mode not in ("legacy", "canonical"):
        raise ValueError(f"unsupported contract_mode: {contract_mode!r}")

    tc_files: list[Path] = []
    temp_dirs: list[Path] = []
    canonical_report: PreflightReport | None = None
    try:
        if contract_mode == "canonical":
            try:
                tc_files, temp_dirs = _resolve_tc_files(
                    args.tc_files, strict=True
                )
            except TCValidationError as e:
                print(f"ERROR: canonical host preflight — {e}", file=sys.stderr)
                sys.exit(1)

            if not tc_files:
                print("ERROR: T/C 파일을 찾을 수 없습니다.")
                sys.exit(1)

            canonical_report = host_preflight(tc_files, contract_mode)
            if not canonical_report.passed:
                print("ERROR: canonical host preflight blocked:", file=sys.stderr)
                for verdict in canonical_report.verdicts:
                    if verdict.passed:
                        continue
                    print(f"  {verdict.path}:", file=sys.stderr)
                    for reason in verdict.reasons:
                        print(f"    - {reason}", file=sys.stderr)
                sys.exit(1)

        adb = ADB()
        if not adb.is_connected():
            print("ERROR: ADB에 연결된 단말이 없습니다.")
            print("USB 케이블과 USB 디버깅 설정을 확인해주세요.")
            sys.exit(1)

        report_dir = Path("reports")
        run_id_raw = getattr(args, "run_id", None) or preflight_mod._now_run_id()
        try:
            run_id = validate_run_id_for_filename(run_id_raw)
        except ValueError as e:
            print(f"ERROR: --run-id 부적합: {e}", file=sys.stderr)
            sys.exit(1)

        reporter = Reporter(
            report_dir=report_dir,
            run_id=run_id,
            contract_mode=contract_mode,
        )
        reporter.device_info = adb.get_device_info()
        screenshot_dir = reporter.screenshot_dir
        runner = ActionRunner(
            adb=adb,
            screenshot_dir=screenshot_dir,
            on_manual_step=_terminal_manual_handler,
            contract_mode=contract_mode,
        )

        if contract_mode == "legacy":
            tc_files, temp_dirs = _resolve_tc_files(args.tc_files)
            if not tc_files:
                print("ERROR: T/C 파일을 찾을 수 없습니다.")
                sys.exit(1)

        canonical_tcs = (
            dict(canonical_report.loaded_tcs)
            if canonical_report is not None
            else {}
        )

        print(f"Device: {reporter.device_info.get('model', '?')} "
              f"(Android {reporter.device_info.get('android_version', '?')})")
        print(f"T/C files: {len(tc_files)}")

        aborted_fail_closed = False
        for tc_file in tc_files:
            if contract_mode == "canonical":
                tc_data = canonical_tcs[tc_file]
                tc_name = tc_data["tc_name"]
            else:
                try:
                    tc_data = load_tc(tc_file)
                except TCValidationError as e:
                    print(f"\nSKIP: {tc_file} — {e}")
                    continue
                tc_name = tc_data["name"]

            reporter.print_tc_header(tc_name)
            tc_result = TCResult(
                name=tc_name,
                description=tc_data.get("description", ""),
            )

            for i, step in enumerate(tc_data["steps"]):
                step_result = runner.run_step(step)
                tc_result.steps.append(step_result)
                reporter.print_step(tc_name, i, step_result)

                if not step_result.passed:
                    if contract_mode == "canonical":
                        aborted_fail_closed = True
                        break
                    # legacy: verify action 실패 시 이 T/C 중단, 다음 T/C로
                    if step["action"].startswith("verify"):
                        break

            reporter.print_tc_result(tc_result)
            reporter.results.append(tc_result)
            if aborted_fail_closed:
                break

        if not reporter.results:
            print("\nERROR: 실행된 T/C가 없습니다.")
            sys.exit(1)

        reporter.run_status = (
            "ABORTED_FAIL_CLOSED" if aborted_fail_closed else "COMPLETED"
        )
        reporter.print_summary()
        print(f"\nRun bundle: {reporter.bundle_dir}")
        try:
            html_path = reporter.generate_html()
            print(f"  HTML report: {html_path}")
        except Exception as e:
            print(f"  WARNING: HTML 리포트 생성 실패 — {e}")
        try:
            summary_path = reporter.write_summary_json()
            print(f"  Summary JSON: {summary_path}")
        except Exception as e:
            if contract_mode == "canonical":
                print(
                    f"ERROR: canonical summary.json persistence failed — {e}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"  WARNING: summary.json 생성 실패 — {e}")

        if aborted_fail_closed:
            sys.exit(1)
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

        # 병목 분석: 레거시 분류기가 차단한 경우
        if preview.automation_class in ("AMBIGUOUS_NL", "OUT_OF_SCOPE") and preview.classified_intents:
            step_class = svc.step_classifier.summarize_tc_class(preview.classified_intents)
            if step_class in ("FULL_AUTO", "SEMI_AUTO"):
                print(f"  Bottleneck: 레거시 분류기가 차단 (StepClassifier 판정: {step_class})")

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

    # 병목 통계
    legacy_blocked = 0
    for row in rows:
        preview = svc.convert_row(row)
        if preview.automation_class in ("AMBIGUOUS_NL", "OUT_OF_SCOPE") and preview.classified_intents:
            step_class = svc.step_classifier.summarize_tc_class(preview.classified_intents)
            if step_class in ("FULL_AUTO", "SEMI_AUTO"):
                legacy_blocked += 1
    if legacy_blocked:
        print(f"  {'Legacy blocked':20s}: {legacy_blocked:4d} (StepClassifier로는 자동화 가능)")



def cmd_explore(args):
    """앱 자동 탐색 커맨드: 앱의 화면 구조를 수집하여 JSON 맵으로 저장한다."""
    adb = ADB()
    if not adb.is_connected():
        print("ERROR: ADB에 연결된 단말이 없습니다.")
        sys.exit(1)

    package = args.package
    activity = args.activity or ".MainActivity"
    output = Path(args.output) if args.output else Path(f"app_map_{package.split('.')[-1]}.json")

    print(f"앱 탐색 시작: {package}")
    print(f"Device: {adb.get_device_info().get('model', '?')}")

    explorer = AppExplorer(
        adb=adb,
        wait_after_tap=args.wait,
        max_elements=args.max_elements,
    )
    app_map = explorer.explore(package, activity)
    explorer.save(app_map, output)
    explorer.print_summary(app_map)
    print(f"\n  저장 완료: {output}")


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


def cmd_preflight(args):
    """Runtime preflight: TC 실행 전 단말 상태 스냅샷 수집.

    tc_file 단일 또는 --dir 디렉토리 중 정확히 하나 지정.
    """
    if bool(args.tc_file) == bool(args.dir):
        print(
            "ERROR: tc_file 또는 --dir 중 정확히 하나만 지정해야 합니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    adb = ADB()
    if not adb.is_connected():
        print("ERROR: ADB에 연결된 단말이 없습니다.", file=sys.stderr)
        print("USB 케이블과 USB 디버깅 설정을 확인해주세요.", file=sys.stderr)
        sys.exit(1)

    run_id = args.run_id or preflight_mod._now_run_id()
    base_out = Path("reports") / "preflight" / run_id

    if args.tc_file:
        tc_path = Path(args.tc_file)
        if not tc_path.is_file():
            print(f"ERROR: TC 파일을 찾을 수 없습니다: {tc_path}", file=sys.stderr)
            sys.exit(1)
        manifest = preflight_mod.run_preflight(
            tc_path=tc_path,
            output_dir=base_out,
            adb=adb,
            run_id=run_id,
            take_screenshot=not args.no_screenshot,
        )
        level = manifest["preflight_status"]["level"]
        reasons = manifest["preflight_status"]["reasons"]
        print(f"preflight {level} — {tc_path.name}")
        if reasons:
            print(f"  reasons: {', '.join(reasons)}")
        print(f"  manifest: {base_out / 'manifest.json'}")
        return

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(f"ERROR: 디렉토리를 찾을 수 없습니다: {dir_path}", file=sys.stderr)
        sys.exit(1)

    tc_files = preflight_mod._resolve_dir_tc_files(dir_path)
    if not tc_files:
        print(f"ERROR: {dir_path} 안에 *.yaml 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    print(f"preflight run_id={run_id}, TC {len(tc_files)}개")
    for tc_path in tc_files:
        sub_out = base_out / tc_path.stem
        manifest = preflight_mod.run_preflight(
            tc_path=tc_path,
            output_dir=sub_out,
            adb=adb,
            run_id=run_id,
            take_screenshot=not args.no_screenshot,
        )
        level = manifest["preflight_status"]["level"]
        reasons = manifest["preflight_status"]["reasons"]
        suffix = f" ({', '.join(reasons)})" if reasons else ""
        print(f"  [{level}] {tc_path.name}{suffix}")

    print(f"\n출력: {base_out}")


def cmd_catalog_build(args):
    """Catalog build: preflight manifest를 누적하여 screens.json + visits.jsonl 작성."""
    app_dir = Path(args.app_dir)

    from_reports = Path(args.from_reports) if args.from_reports else None
    manifest = Path(args.manifest) if args.manifest else None

    if from_reports is not None and manifest is not None:
        print(
            "ERROR: --from-reports 와 --manifest 는 동시 지정할 수 없습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    target_package = args.target_package or None

    try:
        summary = catalog_mod.cmd_build(
            app_dir,
            from_reports=from_reports,
            manifest=manifest,
            target_package=target_package,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"app_dir: {app_dir}")
    print(f"catalog: {app_dir / 'catalog'}")
    print(f"target_package: {summary['target_package']}")
    print(f"discovered: {summary['discovered']}")
    print(f"  added: {summary['added']}")
    print(f"  updated: {summary['updated']}")
    print(f"  skipped_duplicate: {summary['skipped_duplicate']}")
    print(f"  skipped_missing_run_id: {summary['skipped_missing_run_id']}")
    print(f"  skipped_no_xml_hash: {summary['skipped_no_xml_hash']}")
    print(f"  skipped_invalid_json: {summary['skipped_invalid_json']}")
    if summary["mixed_package_warning"]:
        print("WARNING: 입력 manifest 들에 다중 package_name이 섞여있습니다 (PR 4 후속)")


def cmd_catalog_show(args):
    """Catalog show: screens.json 요약 출력."""
    app_dir = Path(args.app_dir)
    try:
        text = catalog_mod.cmd_show(app_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_catalog_delta(args):
    """Catalog delta: 단일 manifest 와 catalog 비교 → reports/catalog_delta/<run_id>.json."""
    catalog_dir = Path(args.catalog_dir)
    manifest = Path(args.manifest)
    output_dir = Path(args.output) if args.output else catalog_delta_mod.DEFAULT_OUTPUT_DIR
    threshold = args.jaccard_threshold

    try:
        report = catalog_delta_mod.cmd_delta(
            catalog_dir,
            manifest,
            output_dir=output_dir,
            threshold=threshold,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    run_id = report.get("run_id")
    verdict = (report.get("delta") or {}).get("verdict")
    flags = report.get("interpretation_flags") or []
    reasons = report.get("insufficient_reasons") or []
    output_path = output_dir / f"{run_id}.json"

    print(f"catalog_delta {verdict} — run_id={run_id}")
    if flags:
        print(f"  flags: {', '.join(flags)}")
    if reasons:
        print(f"  insufficient_reasons: {', '.join(reasons)}")
    print(f"  report: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="tc-runner: Android T/C 자동 실행 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python -m src.cli devices                              # 연결된 단말 확인
  python -m src.cli explore com.example.app              # 앱 화면 구조 탐색
  python -m src.cli run exported_tc1/SS_*.yaml           # TC 실행
  python -m src.cli run tc_samples/TC_1.xlsx             # 엑셀 TC 직접 실행
  python -m src.cli convert tc_samples/TC_1.xlsx         # 엑셀 → YAML 변환
  python -m src.cli preview-mmi tc_samples/TC_1.xlsx     # MMI TC 분석 미리보기
  python -m src.cli export-mmi tc_samples/TC_1.xlsx      # MMI TC → YAML export
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # devices
    devices_parser = subparsers.add_parser("devices", help="연결된 단말 확인")
    devices_parser.set_defaults(func=cmd_devices)

    # explore
    explore_parser = subparsers.add_parser(
        "explore", help="앱 화면 구조 자동 탐색 → JSON 맵 저장")
    explore_parser.add_argument("package", help="앱 패키지명 (예: com.example.seniorshield)")
    explore_parser.add_argument("--activity", help="시작 액티비티 (기본: .MainActivity)")
    explore_parser.add_argument("--output", "-o", help="출력 JSON 경로 (기본: app_map_<앱명>.json)")
    explore_parser.add_argument("--wait", type=float, default=2.0, help="탭 후 대기 시간 (초, 기본: 2.0)")
    explore_parser.add_argument("--max-elements", type=int, default=20, help="최대 탐색 요소 수 (기본: 20)")
    explore_parser.set_defaults(func=cmd_explore)

    # run
    run_parser = subparsers.add_parser("run", help="YAML/엑셀 T/C 실행")
    run_parser.add_argument("tc_files", nargs="+", help="YAML 또는 엑셀(.xlsx) T/C 파일 경로")
    run_parser.add_argument(
        "--run-id",
        dest="run_id",
        default=None,
        help="run_id override (기본: 현재 UTC 타임스탬프 %%Y%%m%%dT%%H%%M%%SZ)",
    )
    run_parser.add_argument(
        "--contract-mode",
        choices=("legacy", "canonical"),
        default="legacy",
        help="execution contract mode (기본: legacy)",
    )
    run_parser.set_defaults(func=cmd_run)

    # preflight
    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Runtime preflight: TC 실행 전 단말 상태 스냅샷 수집",
    )
    preflight_parser.add_argument(
        "tc_file", nargs="?", help="단일 TC YAML 파일 경로 (--dir 와 상호배타)"
    )
    preflight_parser.add_argument(
        "--dir", help="디렉토리 모드: 디렉토리 내 *.yaml 전부 처리"
    )
    preflight_parser.add_argument(
        "--no-screenshot", action="store_true", help="screenshot 생략 (XML dump는 수행)"
    )
    preflight_parser.add_argument(
        "--run-id", help="run_id override (기본: %%Y%%m%%dT%%H%%M%%SZ UTC)"
    )
    preflight_parser.set_defaults(func=cmd_preflight)

    # catalog
    catalog_parser = subparsers.add_parser(
        "catalog",
        help="Screen Identity Catalog (build / show / delta)",
    )
    catalog_subparsers = catalog_parser.add_subparsers(dest="catalog_cmd", required=True)

    catalog_build_parser = catalog_subparsers.add_parser(
        "build",
        help="preflight manifest를 누적하여 <app_dir>/catalog/ 생성",
    )
    catalog_build_parser.add_argument(
        "--app-dir", required=True, help="catalog 대상 앱 루트 (예: 'ODIN2 - My gallary')"
    )
    catalog_build_input = catalog_build_parser.add_mutually_exclusive_group()
    catalog_build_input.add_argument(
        "--from-reports",
        help="manifest.json 디렉토리 (기본: reports/preflight)",
    )
    catalog_build_input.add_argument(
        "--manifest",
        help="단일 manifest.json 경로 (--from-reports 와 상호배타)",
    )
    catalog_build_parser.add_argument(
        "--target-package",
        help="target package 명시 (기본: 첫 valid manifest.app.package_name)",
    )
    catalog_build_parser.set_defaults(func=cmd_catalog_build)

    catalog_show_parser = catalog_subparsers.add_parser(
        "show",
        help="<app_dir>/catalog/screens.json 요약 출력",
    )
    catalog_show_parser.add_argument("--app-dir", required=True, help="catalog 대상 앱 루트")
    catalog_show_parser.set_defaults(func=cmd_catalog_show)

    def _threshold_type(s: str) -> float:
        try:
            v = float(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"jaccard threshold 는 float 여야 합니다: {s}")
        if not (0.0 <= v <= 1.0):
            raise argparse.ArgumentTypeError(
                f"jaccard threshold 는 0.0 ~ 1.0 범위여야 합니다: {v}"
            )
        return v

    catalog_delta_parser = catalog_subparsers.add_parser(
        "delta",
        help="단일 preflight manifest 와 catalog 비교 → delta report",
    )
    catalog_delta_parser.add_argument(
        "--catalog-dir", required=True, help="catalog 디렉토리 (예: 'ODIN2 - My gallary/catalog')"
    )
    catalog_delta_parser.add_argument(
        "--manifest", required=True, help="preflight manifest.json 경로"
    )
    catalog_delta_parser.add_argument(
        "--jaccard-threshold",
        type=_threshold_type,
        default=catalog_delta_mod.DEFAULT_JACCARD_THRESHOLD,
        help=f"changed_texts 판정 임계값 (기본: {catalog_delta_mod.DEFAULT_JACCARD_THRESHOLD})",
    )
    catalog_delta_parser.add_argument(
        "--output",
        help=f"출력 디렉토리 (기본: {catalog_delta_mod.DEFAULT_OUTPUT_DIR})",
    )
    catalog_delta_parser.set_defaults(func=cmd_catalog_delta)

    # convert
    convert_parser = subparsers.add_parser("convert", help="엑셀 → YAML 변환")
    convert_parser.add_argument("xlsx_file", help="엑셀 파일 경로")
    convert_parser.add_argument("-o", "--output", help="출력 디렉토리 (기본: tc_samples/)")
    convert_parser.set_defaults(func=cmd_convert)

    # preview-mmi
    preview_parser = subparsers.add_parser("preview-mmi", help="MMI 엑셀 T/C 분석 미리보기")
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
