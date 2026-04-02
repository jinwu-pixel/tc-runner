import argparse
import sys
from pathlib import Path

from src.adb import ADB
from src.tc_loader import load_tc, TCValidationError
from src.action_runner import ActionRunner
from src.reporter import Reporter, TCResult
from src.excel_converter import convert_excel_to_yaml


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
    runner = ActionRunner(adb=adb, screenshot_dir=screenshot_dir)

    tc_files = []
    for pattern in args.tc_files:
        path = Path(pattern)
        if path.is_file():
            tc_files.append(path)
        else:
            tc_files.extend(Path(".").glob(pattern))

    if not tc_files:
        print("ERROR: T/C 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"Device: {reporter.device_info.get('model', '?')} "
          f"(Android {reporter.device_info.get('android_version', '?')})")
    print(f"T/C files: {len(tc_files)}")

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


def main():
    parser = argparse.ArgumentParser(description="Android T/C 자동 실행 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="T/C 실행")
    run_parser.add_argument("tc_files", nargs="+", help="YAML T/C 파일 경로")
    run_parser.set_defaults(func=cmd_run)

    # convert
    convert_parser = subparsers.add_parser("convert", help="엑셀 → YAML 변환")
    convert_parser.add_argument("xlsx_file", help="엑셀 파일 경로")
    convert_parser.add_argument("-o", "--output", help="출력 디렉토리 (기본: tc_samples/)")
    convert_parser.set_defaults(func=cmd_convert)

    # devices
    devices_parser = subparsers.add_parser("devices", help="연결된 단말 확인")
    devices_parser.set_defaults(func=cmd_devices)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
