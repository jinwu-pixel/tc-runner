#!/usr/bin/env python3
"""Qualcomm Android AP log capture through reboot (무손실).

수동 플로우:
    1. 스크립트 실행 → Phase 1 실시간 수집 시작
    2. 아무 때나 단말 수동 재부팅 (파워키 / adb reboot 무관)
    3. adb 단절 자동 감지 → 재연결 대기 → ramoops/last_kmsg 회수
    4. 부팅 후 실시간 수집 재개 → Ctrl+C 로 종료

출력: Desktop\\QC_AP_Logs\\capture_<timestamp>\\
    01_pre_logcat.txt      재부팅 전 userspace (실시간)
    02_pre_kmsg.txt        재부팅 전 kernel (실시간)
    03_pstore_*.txt        재부팅 구간 kernel (핵심, ramoops)
    04_last_kmsg.txt       legacy 백업 (있을 때)
    05_post_dmesg.txt      부팅 직후 kernel snapshot
    06_boot_logcat.txt     부팅 직후 logcat buffer dump
    07_post_logcat.txt     부팅 후 userspace (실시간)
    SUMMARY.txt
"""

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

ADB = "adb"
REBOOT_WAIT_TIMEOUT = 180   # adb 재연결 최대 대기 (초)
BOOT_COMPLETED_TIMEOUT = 120
BOOT_SETTLE = 5             # boot_completed 이후 안정화


def _get_desktop():
    """OneDrive 동기화 등으로 Desktop 경로가 다를 수 있어 OS에 질의.

    한글 Windows의 powershell 출력은 기본 cp949라 UTF-8 디코드 시 깨진다.
    console encoding을 UTF-8로 강제하고, 그래도 실패하면 cp949/mbcs로 폴백.
    """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
             "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, timeout=10,
        )
        raw = r.stdout
        for enc in ("utf-8", "cp949", "mbcs"):
            try:
                p = raw.decode(enc).strip()
            except Exception:
                continue
            if p and Path(p).exists():
                return Path(p)
    except Exception:
        pass
    return Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"


def run_adb(args, timeout=30):
    return subprocess.run([ADB] + args, capture_output=True, timeout=timeout)


def adb_alive():
    try:
        r = run_adb(["get-state"], timeout=5)
        return r.returncode == 0 and b"device" in r.stdout
    except Exception:
        return False


def get_boot_id():
    """커널이 부팅 시마다 새로 발급하는 UUID. 재부팅 여부 판별에 사용."""
    try:
        r = run_adb(["shell", "cat", "/proc/sys/kernel/random/boot_id"], timeout=5)
        if r.returncode == 0:
            bid = r.stdout.decode("utf-8", errors="replace").strip()
            return bid or None
    except Exception:
        pass
    return None


def pull_text(remote_cmd, out_path, use_su=False):
    cmd = [ADB, "shell"]
    if use_su:
        cmd += ["su", "0"] + remote_cmd
    else:
        cmd += remote_cmd
    try:
        with open(out_path, "wb") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=60)
        return r.returncode == 0
    except Exception as e:
        print(f"  [WARN] {out_path.name}: {e}")
        return False


class LogStream:
    """백그라운드 adb 스트림 → 파일.

    - 재시작 지원 (USB 글리치 복구 시 append 모드로 세션 경계 표시)
    - fallback args 지원 (권한 문제 시 su 0 버전으로 전환)
    - broken 플래그 (즉사하는 스트림은 더 이상 재시작하지 않음)
    """

    FAST_DEATH_SEC = 3  # 시작 N초 내 종료면 '근본적으로 실패'로 간주

    def __init__(self, adb_args, out_path, label, fallback_args=None):
        self.adb_args = adb_args
        self.fallback_args = fallback_args  # [ADB args] or None
        self.out_path = out_path
        self.label = label
        self.proc = None
        self.fh = None
        self._started_once = False
        self._last_start_ts = 0.0
        self._used_fallback = False
        self.broken = False

    def start(self):
        if self.broken:
            return
        mode = "ab" if self._started_once else "wb"
        self.fh = open(self.out_path, mode)
        if self._started_once:
            marker = f"\n\n=== [{_now()}] stream restarted ===\n\n".encode()
            self.fh.write(marker)
            self.fh.flush()
        args = self.adb_args
        self.proc = subprocess.Popen(
            [ADB] + args,
            stdout=self.fh,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        self._started_once = True
        self._last_start_ts = time.time()
        print(f"  [{self.label}] start pid={self.proc.pid} → {self.out_path.name} ({mode})")

    def try_recover(self):
        """죽은 스트림 재시작 시도.

        - 즉사(3초 내)이면 fallback_args 로 전환 시도
        - fallback도 즉사하면 broken=True 로 고정
        - 정상 수명 이후 죽은 경우는 그냥 재시작
        """
        if self.broken or self.alive():
            return
        lifespan = time.time() - self._last_start_ts
        if lifespan < self.FAST_DEATH_SEC:
            # 즉사 — 권한/호환성 문제 가능
            if self.fallback_args and not self._used_fallback:
                print(f"  [{self.label}] 즉사 감지 (lifespan={lifespan:.1f}s) → fallback args 로 전환")
                self.adb_args = self.fallback_args
                self._used_fallback = True
                self.start()
                return
            print(f"  [{self.label}] 즉사 반복 → 스트림 비활성 (broken)")
            self.broken = True
            return
        # 정상 수명 후 죽음 → 단순 재시작
        self.start()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if self.fh:
            try:
                self.fh.flush()
                self.fh.close()
            except Exception:
                pass
        size = self.out_path.stat().st_size if self.out_path.exists() else 0
        print(f"  [{self.label}] stopped ({size:,} bytes)")


GLITCH_RECONNECT_TIMEOUT = 30   # USB 재열거 허용 시간 (초). 이 안에 돌아오면 글리치로 간주.


def wait_for_reboot(pre_streams, initial_boot_id, events):
    """Phase 2-3: 단절 이벤트를 USB 글리치 vs 실제 재부팅으로 구분.

    판별 로직:
        - 스트림 또는 adb 단절 감지 → 재연결 대기 (GLITCH_RECONNECT_TIMEOUT)
        - 재연결 성공 + boot_id 동일  → USB 글리치 (USB 구성 변경 등). 스트림 append 재시작하고 Phase 1 계속.
        - 재연결 성공 + boot_id 변경  → 실제 재부팅. Phase 3 진입.
        - 재연결 실패                  → 장시간 단절, 실제 재부팅으로 간주.
    """
    print("\n=== Phase 2: 재부팅 대기 (단말 리부트 해주세요) ===")
    print("    (USB 설정 변경 등으로 인한 일시 단절은 자동 복구됩니다)")

    def active_streams():
        """broken 은 제외. broken 이 아닌 스트림만 감시 대상."""
        return [s for s in pre_streams if not s.broken]

    while True:
        act = active_streams()
        # 활성 스트림이 전부 broken이면 adb 단절만 감시
        if not act:
            if not adb_alive():
                pass  # 아래 단절 처리로 내려감
            else:
                time.sleep(2)
                continue

        # 정상: 모든 (active) 스트림 + adb 살아있음
        if all(s.alive() for s in act) and adb_alive():
            time.sleep(1)
            continue

        dead_labels = [s.label for s in act if not s.alive()]
        print(f"  [{_now()}] 단절 감지 (dead: {dead_labels or 'none'}, adb={'up' if adb_alive() else 'down'})")

        for s in pre_streams:
            if not s.alive() and s.fh and not s.fh.closed:
                try:
                    s.fh.flush()
                    s.fh.close()
                except Exception:
                    pass

        # 재연결 대기 (짧은 타임아웃)
        deadline = time.time() + GLITCH_RECONNECT_TIMEOUT
        reconnected = False
        while time.time() < deadline:
            if adb_alive():
                reconnected = True
                break
            time.sleep(1)

        if not reconnected:
            print(f"  [{_now()}] {GLITCH_RECONNECT_TIMEOUT}s 내 재연결 없음 → 실제 재부팅으로 간주")
            events.append((_now(), "reboot assumed (long disconnect)"))
            break

        # 재연결됨 → boot_id 로 판별
        current_boot_id = get_boot_id()
        if current_boot_id and initial_boot_id and current_boot_id == initial_boot_id:
            print(f"  [{_now()}] boot_id 동일 → 스트림 재시작 시도")
            events.append((_now(), "stream recover (boot_id unchanged)"))
            for s in pre_streams:
                s.try_recover()
            continue

        # boot_id 변경 또는 조회 실패 (보통 재부팅 직후)
        if current_boot_id:
            print(f"  [{_now()}] boot_id 변경 → 재부팅 확정")
            print(f"    {initial_boot_id} → {current_boot_id}")
            events.append((_now(), f"reboot confirmed (boot_id changed)"))
        else:
            print(f"  [{_now()}] boot_id 조회 불가 → 재부팅으로 간주")
            events.append((_now(), "reboot assumed (boot_id read failed)"))
        break

    # Phase 1 스트림 최종 정리
    for s in pre_streams:
        s.stop()

    print("\n=== Phase 3: 재연결 / boot_completed 대기 ===")
    deadline = time.time() + REBOOT_WAIT_TIMEOUT
    while time.time() < deadline:
        if adb_alive():
            print(f"  [{_now()}] adb 연결 확인")
            break
        time.sleep(2)
    else:
        print("  [ERROR] 재연결 타임아웃")
        return False

    bc_deadline = time.time() + BOOT_COMPLETED_TIMEOUT
    while time.time() < bc_deadline:
        r = run_adb(["shell", "getprop", "sys.boot_completed"], timeout=10)
        if r.returncode == 0 and r.stdout.strip() == b"1":
            print(f"  [{_now()}] boot_completed=1")
            time.sleep(BOOT_SETTLE)
            return True
        time.sleep(2)
    print("  [WARN] boot_completed 타임아웃, 그래도 회수 진행")
    return True


def recover_reboot_gap(capture_dir):
    """Phase 4: 재부팅 구간 커널 로그 회수."""
    print("\n=== Phase 4: 재부팅 구간 회수 ===")

    # pstore (ramoops) — 재부팅 구간의 커널 로그
    r = run_adb(["shell", "ls", "/sys/fs/pstore/"], timeout=10)
    if r.returncode == 0:
        names = r.stdout.decode("utf-8", errors="replace").split()
        got_any = False
        for n in names:
            if not n:
                continue
            if n.startswith("console-ramoops") or n.startswith("dmesg-ramoops"):
                dst = capture_dir / f"03_pstore_{n}.txt"
                ok = pull_text(["cat", f"/sys/fs/pstore/{n}"], dst)
                if not ok or dst.stat().st_size == 0:
                    pull_text(["cat", f"/sys/fs/pstore/{n}"], dst, use_su=True)
                size = dst.stat().st_size if dst.exists() else 0
                if size > 0:
                    print(f"  pstore/{n}: {size:,} bytes → {dst.name}")
                    got_any = True
                else:
                    if dst.exists():
                        dst.unlink()
        if not got_any:
            print("  [WARN] pstore 파일이 비어있거나 접근 불가 (권한 필요 가능)")
    else:
        print("  [WARN] /sys/fs/pstore/ 접근 불가")

    # last_kmsg (legacy 백업 경로)
    dst = capture_dir / "04_last_kmsg.txt"
    pull_text(["cat", "/proc/last_kmsg"], dst)
    if not dst.exists() or dst.stat().st_size == 0:
        if dst.exists():
            dst.unlink()
        # 일부 기기는 /sys/fs/pstore 를 대신 씀
    else:
        print(f"  last_kmsg → {dst.name}")

    # 현재 커널 스냅샷
    dst = capture_dir / "05_post_dmesg.txt"
    pull_text(["dmesg"], dst)
    if dst.exists():
        print(f"  dmesg → {dst.name} ({dst.stat().st_size:,} bytes)")

    # 부팅 직후 logcat 전체 버퍼 덤프 (early userspace 회수)
    dst = capture_dir / "06_boot_logcat.txt"
    pull_text(["logcat", "-b", "all", "-d", "-v", "threadtime"], dst)
    if dst.exists():
        print(f"  boot logcat → {dst.name} ({dst.stat().st_size:,} bytes)")


def _now():
    return datetime.datetime.now().strftime("%H:%M:%S")


def write_summary(capture_dir, started_at, events):
    summary = capture_dir / "SUMMARY.txt"
    with open(summary, "w", encoding="utf-8") as f:
        f.write("QC AP Log Capture\n")
        f.write(f"started : {started_at}\n")
        f.write(f"finished: {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"dir     : {capture_dir}\n\n")
        f.write("=== events ===\n")
        for t, msg in events:
            f.write(f"{t}  {msg}\n")
        f.write("\n=== files ===\n")
        for p in sorted(capture_dir.iterdir()):
            if p.name == "SUMMARY.txt":
                continue
            f.write(f"{p.name}\t{p.stat().st_size:,} bytes\n")


def main():
    ap = argparse.ArgumentParser(description="Qualcomm AP log capture through reboot")
    ap.add_argument("-o", "--output-dir", help="출력 루트 (기본: Desktop\\QC_AP_Logs)")
    args = ap.parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(args.output_dir) if args.output_dir else _get_desktop() / "QC_AP_Logs"
    capture_dir = root / f"capture_{ts}"
    capture_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.datetime.now().isoformat(timespec="seconds")
    events = [(_now(), f"capture dir: {capture_dir}")]
    print(f"출력: {capture_dir}")

    if not adb_alive():
        print("[ERROR] adb 단말 미연결")
        return 1

    # 모델/빌드 정보 기록
    for prop in ("ro.product.model", "ro.build.fingerprint",
                 "ro.build.version.release", "ro.build.type"):
        r = run_adb(["shell", "getprop", prop], timeout=5)
        val = r.stdout.decode("utf-8", errors="replace").strip()
        events.append((_now(), f"{prop}={val}"))

    # 재부팅 판별 기준: 초기 boot_id 캡처
    initial_boot_id = get_boot_id()
    if initial_boot_id:
        events.append((_now(), f"initial boot_id={initial_boot_id}"))
        print(f"initial boot_id: {initial_boot_id}")
    else:
        print("[WARN] boot_id 조회 실패 — USB 글리치 판별이 동작하지 않을 수 있음")
        events.append((_now(), "initial boot_id read failed"))

    # logcat 버퍼 클리어는 하지 않음 (기존 누적 로그도 가치 있음)

    print("\n=== Phase 1: 재부팅 전 실시간 수집 시작 ===")
    pre_logcat = LogStream(
        ["logcat", "-b", "all", "-v", "threadtime"],
        capture_dir / "01_pre_logcat.txt", "logcat",
    )
    # dmesg -w: stock Android 에서는 klogctl 권한 거부될 수 있음 → userdebug 이면 su 0 폴백.
    # 둘 다 안 되면 broken 처리되어 재시작 루프에서 빠짐 (재부팅 구간은 last_kmsg 로 회수).
    pre_kmsg = LogStream(
        ["shell", "dmesg", "-w"],
        capture_dir / "02_pre_kmsg.txt", "kmsg",
        fallback_args=["shell", "su", "0", "dmesg", "-w"],
    )
    pre_logcat.start()
    pre_kmsg.start()
    events.append((_now(), "Phase 1 started"))

    print("\n>> 준비 완료. 아무 때나 단말을 재부팅하세요.")
    print(">> (중단하려면 Ctrl+C)\n")

    post_logcat = None
    try:
        if not wait_for_reboot([pre_logcat, pre_kmsg], initial_boot_id, events):
            events.append((_now(), "reboot wait failed"))
            return 1
        events.append((_now(), "reconnected"))

        recover_reboot_gap(capture_dir)
        events.append((_now(), "gap recovered"))

        print("\n=== Phase 5: 부팅 후 실시간 수집 재개 ===")
        post_logcat = LogStream(
            ["logcat", "-b", "all", "-v", "threadtime"],
            capture_dir / "07_post_logcat.txt", "logcat",
        )
        post_logcat.start()
        events.append((_now(), "Phase 5 started"))

        print("\n>> 종료하려면 Ctrl+C\n")
        while post_logcat.alive():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[중단됨]")
        events.append((_now(), "user interrupted"))
    finally:
        for s in (pre_logcat, pre_kmsg, post_logcat):
            if s is not None:
                s.stop()
        write_summary(capture_dir, started_at, events)
        print(f"\n완료: {capture_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
