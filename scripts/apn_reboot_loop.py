#!/usr/bin/env python3
"""BUG-5426 APN 증가 감시 반복 테스트.

비행기 모드 ON + preferred network 변경 + 리부팅을 반복하면서
AT+CGDCONT 기준 APN 줄 수(기대: 4줄)가 증가하는지 추적한다.

사용법:
    python scripts/apn_reboot_loop.py --iterations 20
    python scripts/apn_reboot_loop.py --iterations 50 --scenario both
    python scripts/apn_reboot_loop.py --iterations 10 --scenario emcall_only

시나리오:
    reboot_only  : 비행기모드 + pref 변경 + 리부팅 반복
    emcall_only  : 비행기모드 + 긴급호(118) 반복
    both         : 리부팅 1회 → 긴급호 1회 교대
"""

import argparse
import datetime
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── 설정 ──
ADB = "adb"
APN_QUERY_CMD = (
    "su 0 content query"
    " --uri content://telephony/carriers"
    " --projection _id:name:apn:type:numeric:carrier_enabled"
    " --where \"numeric='45008'\""
)
RILJ_TAG = "RILJ"
REBOOT_WAIT = 80          # 리부팅 후 ADB 재연결 대기 (초)
EMCALL_SETTLE = 10        # 긴급호 종료 후 안정화 대기 (초)
EMCALL_DURATION = 15      # 긴급호 통화 유지 시간 (초)
EXPECTED_APN_LINES = 5    # content query 기준 KT APN 행 수
EXPECTED_CGDCONT = 4      # AT+CGDCONT 기준 PDP context 수
def _get_desktop():
    """OneDrive 동기화 등으로 바탕화면 경로가 다를 수 있으므로 OS에 직접 질의."""
    try:
        r = subprocess.run(
            ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, timeout=10
        )
        p = r.stdout.decode("utf-8", errors="replace").strip()
        if p and Path(p).exists():
            return Path(p)
    except Exception:
        pass
    return Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"

_DESKTOP = _get_desktop() / "BUG5426_logs"
LOG_DIR = _DESKTOP
BOOT_LOG_DIR = _DESKTOP / "boot_logs"
APN_SNAP_DIR = _DESKTOP / "apn_snapshots"
PERSIST_LOG_DIR = _DESKTOP / "persist_logs"


def ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pull_persist_logs():
    """디바이스 내 persist logcat 로그를 PC로 복사."""
    PERSIST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = PERSIST_LOG_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    try:
        import shutil, tempfile
        # 권한 문제 우회: su로 임시 복사 후 pull
        subprocess.run(
            [ADB, "shell", "su 0 cp -r /data/misc/logd/ /data/local/tmp/logd_backup"],
            capture_output=True, timeout=30
        )
        subprocess.run(
            [ADB, "shell", "su 0 chmod -R 755 /data/local/tmp/logd_backup"],
            capture_output=True, timeout=10
        )
        # adb pull은 한글 경로 실패 → ASCII 임시 폴더에 먼저 pull 후 이동
        tmp_dir = Path(tempfile.mkdtemp(prefix="logd_pull_"))
        r = subprocess.run(
            [ADB, "pull", "/data/local/tmp/logd_backup/", str(tmp_dir)],
            capture_output=True, timeout=300
        )
        # 임시 파일 정리 (단말)
        subprocess.run(
            [ADB, "shell", "su 0 rm -rf /data/local/tmp/logd_backup"],
            capture_output=True, timeout=10
        )
        if r.returncode == 0:
            # 임시 → 최종 경로로 이동
            pulled = tmp_dir / "logd_backup"
            src = pulled if pulled.is_dir() else tmp_dir
            shutil.copytree(src, dest, dirs_exist_ok=True)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"  persist 로그 저장 완료: {dest.resolve()}", flush=True)
            return dest
        else:
            err = r.stderr.decode("utf-8", errors="replace").strip()
            print(f"  persist 로그 pull 실패: {err}", flush=True)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return None
    except subprocess.TimeoutExpired:
        print("  persist 로그 pull 타임아웃", flush=True)
        subprocess.run(
            [ADB, "shell", "su 0 rm -rf /data/local/tmp/logd_backup"],
            capture_output=True, timeout=10
        )
        return None


# Ctrl+C 핸들러용 전역 상태
_log_path = None
_interrupted = False


def handle_sigint(signum, frame):
    """Ctrl+C 시 로그 저장 여부 확인 후 종료."""
    global _interrupted
    _interrupted = True
    print(f"\n\n{'='*60}", flush=True)
    print(f"  [{ts()}] Ctrl+C 감지 — 테스트 중단", flush=True)
    print(f"{'='*60}", flush=True)

    if _log_path:
        print(f"\n  CSV 로그: {Path(_log_path).resolve()}", flush=True)
        print(f"  부팅 로그: {BOOT_LOG_DIR.resolve()}", flush=True)
        print(f"  APN 스냅샷: {APN_SNAP_DIR.resolve()}", flush=True)

    print()
    try:
        choice = input("  디바이스 persist 로그를 저장하시겠습니까? (Y/N): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        print("\n  종료합니다.", flush=True)
        sys.exit(1)

    if choice == "Y":
        print(f"  [{ts()}] persist 로그 복사 중...", flush=True)
        dest = pull_persist_logs()
        if dest:
            print(f"\n  전체 로그 위치:", flush=True)
            print(f"    CSV      : {Path(_log_path).resolve()}", flush=True)
            print(f"    부팅 로그 : {BOOT_LOG_DIR.resolve()}", flush=True)
            print(f"    APN 스냅샷: {APN_SNAP_DIR.resolve()}", flush=True)
            print(f"    persist  : {dest.resolve()}", flush=True)
    else:
        print("  persist 로그 저장 생략", flush=True)

    print(f"\n  종료합니다.", flush=True)
    sys.exit(0)


def adb(shell_cmd, timeout=30):
    """단일 문자열로 adb shell 실행. 내부 따옴표/파이프 안전."""
    cmd = [ADB, "shell", shell_cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", errors="replace").strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR] {e}"


def adb_wait(max_wait=120):
    """ADB 재연결 대기."""
    print(f"  [{ts()}] ADB 재연결 대기 (최대 {max_wait}초)...", flush=True)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = subprocess.run(
                [ADB, "shell", "getprop", "sys.boot_completed"],
                capture_output=True, timeout=5
            )
            if r.stdout.decode("utf-8", errors="replace").strip() == "1":
                time.sleep(3)  # 추가 안정화
                print(f"  [{ts()}] ADB 재연결 완료", flush=True)
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass
        time.sleep(3)
    print(f"  [{ts()}] ADB 재연결 실패!", flush=True)
    return False


def get_apn_count():
    """content query 기준 KT APN 행 수 반환."""
    result = adb(APN_QUERY_CMD)
    if not result or result.startswith("["):
        return -1, result
    lines = [l for l in result.splitlines() if l.startswith("Row:")]
    return len(lines), result


def get_apn_snapshot():
    """APN 전체 목록 문자열 반환."""
    result = adb(APN_QUERY_CMD)
    return result


def get_airplane_mode():
    return adb("settings get global airplane_mode_on")


def set_airplane_on():
    adb("su 0 settings put global airplane_mode_on 1")
    adb("su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true")
    time.sleep(3)


def set_airplane_off():
    adb("su 0 settings put global airplane_mode_on 0")
    adb("su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false")
    time.sleep(5)


def set_preferred_network(mode):
    """mode: 2=WCDMA Only, 9=LTE/WCDMA"""
    adb(f"settings put global preferred_network_mode1 {mode}")


def clear_logcat():
    adb("logcat -c")


def dump_rilj():
    return adb("logcat -d -s RILJ", timeout=10)


def dump_boot_logs(iteration, scenario_name):
    """부팅 직후 radio+main 버퍼 덤프 (SIM EF 읽기 로그 포함)."""
    BOOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{iteration:03d}_{scenario_name}_{timestamp}"

    # 현재 부팅의 radio+main 버퍼 (SIM EF, CarrierConfig, TelephonyProvider 포함)
    radio_main = adb("logcat -b radio -b main -d", timeout=30)
    radio_main_path = BOOT_LOG_DIR / f"{prefix}_radio_main.txt"
    radio_main_path.write_text(radio_main, encoding="utf-8")

    # 이전 부팅의 radio 버퍼 (logcat -L)
    last_radio = adb("logcat -b radio -L -d", timeout=15)
    if last_radio and not last_radio.startswith("["):
        last_path = BOOT_LOG_DIR / f"{prefix}_last_boot_radio.txt"
        last_path.write_text(last_radio, encoding="utf-8")

    print(f"  [{ts()}] 부팅 로그 저장: {radio_main_path}", flush=True)
    return radio_main


def save_apn_snapshot(iteration, phase, snapshot_text):
    """APN 스냅샷을 파일로 저장 (before/after 비교용)."""
    APN_SNAP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = APN_SNAP_DIR / f"{iteration:03d}_{phase}_{timestamp}.txt"
    path.write_text(snapshot_text, encoding="utf-8")
    return path


def check_rilj_anomalies(rilj_log):
    """RILJ 로그에서 비정상 항목 카운트."""
    radio_power_on = rilj_log.count("RADIO_POWER on = true")
    reg_home = rilj_log.count("REG_HOME")
    return radio_power_on, reg_home


def reboot_device():
    adb("su 0 reboot", timeout=10)


# ── 시나리오 ──

def scenario_reboot(iteration, log_file, baseline_snapshot):
    """시나리오 A: 비행기모드 + pref 변경 + 리부팅."""
    print(f"\n{'='*60}", flush=True)
    print(f"  [반복 #{iteration}] 시나리오: REBOOT", flush=True)
    print(f"  [{ts()}] 시작", flush=True)

    # 1. Airplane ON
    set_airplane_on()
    airplane = get_airplane_mode()
    print(f"  [{ts()}] 비행기 모드: {airplane}", flush=True)

    # 2. logcat 초기화 + 리부팅
    clear_logcat()
    print(f"  [{ts()}] 리부팅 시작...", flush=True)
    reboot_device()

    # 3. 재연결 대기
    time.sleep(10)
    if not adb_wait(REBOOT_WAIT):
        log_file.write(f"{iteration},REBOOT,FAIL,ADB_RECONNECT_FAIL,-1,0,0\n")
        log_file.flush()
        return False

    # 3-1. 부팅 직후 radio+main 버퍼 즉시 덤프 (SIM EF 읽기 로그 캡처)
    boot_log = dump_boot_logs(iteration, "REBOOT")

    # 3-2. SIM 초기화 + CarrierConfig 로드 완료 대기
    time.sleep(10)

    # 4. 비행기 모드 유지 상태에서 긴급호 발신 (BUG-5426 핵심 트리거)
    airplane = get_airplane_mode()
    if airplane == "1":
        print(f"  [{ts()}] 비행기 모드 ON 확인 → 긴급호(118) 발신...", flush=True)
        call_ok, call_msg = make_emergency_call("118", call_duration=EMCALL_DURATION)
        if not call_ok:
            print(f"  [{ts()}] 긴급호 발신 실패: {call_msg}", flush=True)
            log_file.write(f"{iteration},REBOOT,FAIL,EMCALL_{call_msg},-1,0,0\n")
            log_file.flush()
            set_airplane_off()
            return False
        print(f"  [{ts()}] 긴급호 종료 완료", flush=True)
        time.sleep(EMCALL_SETTLE)
    else:
        print(f"  [{ts()}] WARNING: 비행기 모드 OFF 상태 (airplane={airplane}), 긴급호 스킵", flush=True)

    # 5. 검증
    airplane = get_airplane_mode()
    apn_count, apn_raw = get_apn_count()
    rilj = dump_rilj()
    radio_on, reg_home = check_rilj_anomalies(rilj)

    result = "PASS"
    details = []

    if airplane != "1":
        details.append(f"WARN:airplane={airplane}")

    # 핵심 판정: APN 증가 여부
    if apn_count != EXPECTED_APN_LINES:
        result = "FAIL"
        details.append(f"apn_count={apn_count}(expected={EXPECTED_APN_LINES})")

    # APN 내용 변경 확인
    current_snapshot = get_apn_snapshot()
    if current_snapshot != baseline_snapshot:
        result = "FAIL"
        details.append("APN_CONTENT_CHANGED")
        save_apn_snapshot(iteration, "after_reboot", current_snapshot)

    # 보조 지표 (FAIL 판정에는 사용하지 않고 기록만)
    if radio_on > 0:
        details.append(f"RADIO_POWER_ON={radio_on}")
    if reg_home > 0:
        details.append(f"REG_HOME={reg_home}")

    detail_str = "|".join(details) if details else "OK"
    print(f"  [{ts()}] 결과: {result} (APN={apn_count}, airplane={airplane}, RADIO_ON={radio_on}, REG_HOME={reg_home})", flush=True)
    log_file.write(f"{iteration},REBOOT,{result},{detail_str},{apn_count},{radio_on},{reg_home}\n")
    log_file.flush()

    # 6. 다음 반복을 위해 비행기 모드 ON (긴급호가 해제했을 수 있음)
    set_airplane_on()

    return result == "PASS"


def make_emergency_call(number="118", call_duration=10):
    """긴급호 자동 발신 + 대기 + 종료."""
    # 발신 (root 필요: CALL_PRIVILEGED)
    adb(f"su 0 am start -a android.intent.action.CALL_EMERGENCY -d tel:{number}", timeout=10)
    time.sleep(3)

    # 통화 상태 확인
    telecom = adb("dumpsys telecom", timeout=10)
    if "isEmergency: true" not in telecom:
        return False, "CALL_NOT_ESTABLISHED"

    # 통화 유지
    time.sleep(call_duration)

    # 통화 종료 (pkill phone process)
    adb("su 0 pkill -f com.android.phone", timeout=10)
    time.sleep(3)

    # 종료 확인
    telecom = adb("dumpsys telecom", timeout=10)
    if "state=ACTIVE" in telecom:
        # 재시도
        adb("su 0 pkill -f com.android.phone", timeout=10)
        time.sleep(3)

    return True, "OK"


def scenario_emcall(iteration, log_file, baseline_snapshot):
    """시나리오 B: 비행기모드 중 긴급호 발신."""
    print(f"\n{'='*60}", flush=True)
    print(f"  [반복 #{iteration}] 시나리오: EMERGENCY CALL", flush=True)
    print(f"  [{ts()}] 시작", flush=True)

    # 1. Airplane ON
    set_airplane_on()
    airplane = get_airplane_mode()
    print(f"  [{ts()}] 비행기 모드: {airplane}", flush=True)

    # 2. logcat 초기화
    clear_logcat()

    # 2-1. 비행기 모드 재확인
    airplane = get_airplane_mode()
    if airplane != "1":
        print(f"  [{ts()}] 비행기 모드 재설정 (현재: {airplane})", flush=True)
        set_airplane_on()
        time.sleep(2)

    # 3. 긴급호 자동 발신
    print(f"  [{ts()}] 긴급호(118) 자동 발신...", flush=True)
    call_ok, call_msg = make_emergency_call("118", call_duration=EMCALL_DURATION)
    if not call_ok:
        print(f"  [{ts()}] 긴급호 발신 실패: {call_msg}", flush=True)
        log_file.write(f"{iteration},EMCALL,FAIL,{call_msg},-1,0,0\n")
        log_file.flush()
        set_airplane_off()
        return False
    print(f"  [{ts()}] 긴급호 종료 완료", flush=True)

    time.sleep(EMCALL_SETTLE)

    # 4. 검증
    apn_count, apn_raw = get_apn_count()
    rilj = dump_rilj()
    radio_on, reg_home = check_rilj_anomalies(rilj)

    result = "PASS"
    details = []

    if apn_count != EXPECTED_APN_LINES:
        result = "FAIL"
        details.append(f"apn_count={apn_count}(expected={EXPECTED_APN_LINES})")

    if reg_home > 0:
        details.append(f"REG_HOME={reg_home}")

    current_snapshot = get_apn_snapshot()
    if current_snapshot != baseline_snapshot:
        result = "FAIL"
        details.append("APN_CONTENT_CHANGED")
        save_apn_snapshot(iteration, "after_emcall", current_snapshot)

    detail_str = "|".join(details) if details else "OK"
    print(f"  [{ts()}] 결과: {result} (APN={apn_count}, RADIO_ON={radio_on}, REG_HOME={reg_home})", flush=True)
    log_file.write(f"{iteration},EMCALL,{result},{detail_str},{apn_count},{radio_on},{reg_home}\n")
    log_file.flush()

    # 5. 복구
    set_airplane_off()

    return result == "PASS"


def main():
    parser = argparse.ArgumentParser(description="BUG-5426 APN 증가 감시 반복 테스트")
    parser.add_argument("--iterations", "-n", type=int, default=20, help="반복 횟수 (기본: 20)")
    parser.add_argument("--scenario", "-s", choices=["reboot_only", "emcall_only", "both"],
                        default="reboot_only", help="시나리오 선택")
    parser.add_argument("--stop-on-fail", action="store_true",
                        help="FAIL 발생 시 즉시 중단")
    parser.add_argument("--skip-confirm", action="store_true",
                        help="QXDM 준비 확인 프롬프트 스킵")
    args = parser.parse_args()

    global _log_path

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    BOOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    APN_SNAP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"apn_loop_{timestamp}.csv"
    _log_path = log_path

    # Ctrl+C 핸들러 등록
    signal.signal(signal.SIGINT, handle_sigint)

    print(f"{'='*60}")
    print(f"  BUG-5426 APN 증가 감시 반복 테스트")
    print(f"{'='*60}")
    print()
    print(f"  시나리오  : {args.scenario}")
    print(f"  반복 횟수 : {args.iterations}")
    print(f"  중단 조건 : {'FAIL 시 즉시 중단' if args.stop_on_fail else '끝까지 실행'}")
    print()
    print(f"  [사전 설정 확인]")
    print(f"    1. logcat 버퍼 확장 (persist.logd.size = 16MB)")
    print(f"       adb shell getprop persist.logd.size")
    print(f"    2. logcat persist 로깅 활성화")
    print(f"       adb shell getprop persist.logd.logpersistd  (logcatd 여야 함)")
    print(f"    3. QXDM 연결 + QPST COM 포트 등록")
    print(f"    4. WWAN AutoConfig 중지 (sc stop WwanSvc)")
    print()
    print(f"  [로그 저장 경로]")
    print(f"    CSV 결과  : {log_path}")
    print(f"    부팅 로그  : {BOOT_LOG_DIR}/")
    print(f"    APN 스냅샷 : {APN_SNAP_DIR}/")
    print(f"    persist   : 종료 시 저장 여부 선택")
    print()
    print(f"  [종료] Ctrl+C → persist 로그 저장 여부 확인 후 종료")
    print(f"{'='*60}")

    # baseline
    print(f"\n[{ts()}] APN baseline 취득 중...", flush=True)
    baseline_count, baseline_snapshot = get_apn_count()
    print(f"[{ts()}] baseline APN 행 수: {baseline_count}", flush=True)
    print(f"[{ts()}] baseline 내용:\n{baseline_snapshot}\n", flush=True)

    # baseline 스냅샷 파일 저장
    save_apn_snapshot(0, "baseline", baseline_snapshot)

    if baseline_count != EXPECTED_APN_LINES:
        print(f"[WARNING] baseline이 예상({EXPECTED_APN_LINES})과 다릅니다: {baseline_count}")
        confirm = input("계속 진행하시겠습니까? (y/n): ")
        if confirm.lower() != "y":
            sys.exit(1)

    # QXDM 확인
    if not args.skip_confirm:
        print(f"\n[{ts()}] QXDM 연결 상태를 확인하세요.")
        print("  - QXDM OTA filter 설정 (F12 > OTA > LTE > NAS)")
        print("  - PC: WWAN AutoConfig 중지 (sc stop WwanSvc)")
        input("준비 완료 후 Enter... ")
    else:
        print(f"\n[{ts()}] QXDM 확인 스킵 (--skip-confirm)", flush=True)

    pass_count = 0
    fail_count = 0

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("iteration,scenario,result,detail,apn_count,radio_power_on,reg_home\n")
        log_file.flush()

        for i in range(1, args.iterations + 1):
            if args.scenario == "reboot_only":
                ok = scenario_reboot(i, log_file, baseline_snapshot)
            elif args.scenario == "emcall_only":
                ok = scenario_emcall(i, log_file, baseline_snapshot)
            else:  # both
                if i % 2 == 1:
                    ok = scenario_reboot(i, log_file, baseline_snapshot)
                else:
                    ok = scenario_emcall(i, log_file, baseline_snapshot)

            if ok:
                pass_count += 1
            else:
                fail_count += 1
                if args.stop_on_fail:
                    print(f"\n[{ts()}] FAIL 발생 — 즉시 중단", flush=True)
                    break

            # 반복 간 상태 리포트
            print(f"\n  --- 누적: PASS={pass_count} / FAIL={fail_count} / 진행={i}/{args.iterations} ---", flush=True)

            # 매 반복 APN 추이 출력
            current_count, _ = get_apn_count()
            print(f"  --- 현재 APN 행 수: {current_count} (baseline: {baseline_count}) ---", flush=True)
            if current_count != baseline_count:
                print(f"  *** APN 개수 변화 감지! {baseline_count} -> {current_count} ***", flush=True)

    # 최종 리포트
    print(f"\n{'='*60}")
    print(f"최종 결과")
    print(f"  총 반복: {pass_count + fail_count}")
    print(f"  PASS: {pass_count}")
    print(f"  FAIL: {fail_count}")
    print(f"  로그: {log_path}")
    print(f"{'='*60}")

    # 최종 APN 상태
    final_count, final_snapshot = get_apn_count()
    print(f"\n최종 APN 상태 (행 수: {final_count}):")
    print(final_snapshot)

    if final_count != baseline_count:
        print(f"\n*** APN 증가 감지: {baseline_count} -> {final_count} ***")
    else:
        print(f"\nAPN 변화 없음 (유지: {final_count}줄)")

    # 정상 종료 시에도 persist 로그 저장 여부 확인
    print()
    try:
        choice = input("디바이스 persist 로그를 저장하시겠습니까? (Y/N): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        choice = "N"

    if choice == "Y":
        print(f"[{ts()}] persist 로그 복사 중...", flush=True)
        dest = pull_persist_logs()
        if dest:
            print(f"\n전체 로그 위치:", flush=True)
            print(f"  CSV      : {log_path.resolve()}", flush=True)
            print(f"  부팅 로그 : {BOOT_LOG_DIR.resolve()}", flush=True)
            print(f"  APN 스냅샷: {APN_SNAP_DIR.resolve()}", flush=True)
            print(f"  persist  : {dest.resolve()}", flush=True)


if __name__ == "__main__":
    main()
