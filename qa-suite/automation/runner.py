# runner.py — 메인 실행기 (fail-fast / fail-closed)
# exit code: INFRA_FAILURE 존재 3 > FAIL 존재 1 > WARN 존재·전체 SKIP 2 > PASS(+SKIP) 0.
# 실행 결과 0건 = INFRA_FAILURE(3). 미등록 test·config 문제는 실행 전 차단.
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    yaml = None

from report_adapter import build_summary_payload, new_run_id, write_summary_json
from tests.base_test import VALID_STATUSES
from tests.bug_23025_harness import Bug23025Harness
# 신규 모듈은 여기 import + TEST_REGISTRY 등록 (CLAUDE.md 4장)

TEST_REGISTRY = {
    "bug_23025": Bug23025Harness,
    # "bug_24570": Bug24570GmailCrash,   # ../analysis/bugs/BUG-24570.md Q 해소 후
}

CONFIG_PATH = "config.local.yaml"   # 실 serial 등 로컬 식별자는 이 파일에만 (gitignore 대상)

EXIT_PASS, EXIT_FAIL, EXIT_WARN, EXIT_INFRA = 0, 1, 2, 3


class RunnerInfraError(Exception):
    """실행 전제 미충족 — 테스트를 시작하지 않고 INFRA_FAILURE(3) 로 종료."""


def load_config(path=CONFIG_PATH):
    if yaml is None:
        raise RunnerInfraError("PyYAML 미설치 — venv 에서 `pip install pyyaml` 후 재실행")
    if not os.path.isfile(path):
        raise RunnerInfraError(
            f"config 부재: {path} — config.example.yaml 을 복사해 작성하세요")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise RunnerInfraError(f"config 파싱 오류: {path}: {e}")
    if cfg is None:
        cfg = {}
    if not isinstance(cfg, dict):
        raise RunnerInfraError(f"config 형식 오류: {path} (mapping 이어야 함)")
    return cfg


def parse_adb_devices(output):
    """`adb devices` 출력에서 state 가 device 인 serial 만 반환."""
    serials = []
    for ln in output.splitlines()[1:]:
        parts = ln.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def _query_devices():
    try:
        r = subprocess.run(["adb", "devices"], shell=False, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        raise RunnerInfraError(f"adb devices 실행 실패: {e}")
    if r.returncode != 0:
        raise RunnerInfraError(
            f"adb devices rc={r.returncode}: {(r.stderr or b'').decode('utf-8', 'replace').strip()}")
    return parse_adb_devices((r.stdout or b"").decode("utf-8", errors="replace"))


def resolve_device(config, devices):
    """단말 검사: 명시 serial 은 연결 확인, 공란은 정확히 1대일 때만 자동 고정."""
    want = (config.get("device_id") or "").strip()
    if want:
        if want not in devices:
            raise RunnerInfraError(
                f"명시 serial {want} 가 device 상태가 아님 (연결: {devices or '없음'})")
        return want
    if len(devices) == 1:
        return devices[0]
    raise RunnerInfraError(
        f"연결 단말 {len(devices)}대 — 정확히 1대 필요. device_id 명시 또는 단말 정리 후 재실행")


def compute_exit(statuses):
    """닫힌 exit code 체계. 결과 0건 = INFRA(3)."""
    if not statuses:
        return EXIT_INFRA
    if any(s == "INFRA_FAILURE" for s in statuses):
        return EXIT_INFRA
    if any(s == "FAIL" for s in statuses):
        return EXIT_FAIL
    if any(s == "WARN" for s in statuses):
        return EXIT_WARN
    if all(s == "SKIP" for s in statuses):
        return EXIT_WARN
    return EXIT_PASS


def main(config_path=CONFIG_PATH, query_devices=None):
    # 최외곽 가드: 어떤 예외도 traceback+exit 1 로 새지 않게 전부 INFRA_FAILURE(3) 로 닫는다.
    try:
        config = load_config(config_path)

        targets = config.get("tests")
        if targets is None:
            targets = list(TEST_REGISTRY.keys())
        if not targets:
            raise RunnerInfraError("선택된 test 0건 — config 의 tests 목록 확인")
        unknown = [t for t in targets if t not in TEST_REGISTRY]
        if unknown:
            raise RunnerInfraError(
                f"미등록 test: {unknown} (등록: {sorted(TEST_REGISTRY)})")

        devices = (query_devices or _query_devices)()
        config["device_id"] = resolve_device(config, devices)

        run_id = new_run_id()
        run_dir = os.path.join("logs", run_id)
        os.makedirs(run_dir, exist_ok=True)
        config["run_dir"] = run_dir

        tests_results = {}
        all_statuses = []
        for name in targets:
            results = TEST_REGISTRY[name](config).run()
            normalized = []
            for status, reason, art in results:
                if status not in VALID_STATUSES:
                    status, reason = "INFRA_FAILURE", f"미등록 status {status!r}: {reason}"
                normalized.append((status, reason, art))
                all_statuses.append(status)
            tests_results[name] = normalized

        payload = build_summary_payload(
            run_id=run_id,
            device={"serial": config["device_id"]},
            tests_results=tests_results,
        )
        summary_path = write_summary_json("report", run_id, payload)

        print(f"\n{'='*54}\n검증 요약 (run_id={run_id})\n{'='*54}")
        for name, rows in tests_results.items():
            counts = {s: 0 for s in VALID_STATUSES}
            for s, _, _ in rows:
                counts[s] += 1
            mark = ("INFRA_FAILURE" if counts["INFRA_FAILURE"] else
                    "FAIL" if counts["FAIL"] else
                    "WARN" if counts["WARN"] else
                    "SKIP" if counts["SKIP"] == len(rows) and rows else "PASS")
            print(f"[{mark}] {name}: P{counts['PASS']} / W{counts['WARN']} / F{counts['FAIL']}"
                  f" / S{counts['SKIP']} / I{counts['INFRA_FAILURE']} (총 {len(rows)})")

        if not all_statuses:
            print("[INFRA_FAILURE] 실행 결과 0건")
        print(f"리포트: {summary_path}\n아티팩트: {run_dir}/")
        exit_code = compute_exit(all_statuses)
    except RunnerInfraError as e:
        print(f"[INFRA_FAILURE] {e}")
        sys.exit(EXIT_INFRA)
    except Exception as e:  # noqa: BLE001 — 경계 예외도 PASS/FAIL 로 위장 금지
        print(f"[INFRA_FAILURE] unhandled {type(e).__name__}: {e}")
        sys.exit(EXIT_INFRA)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
