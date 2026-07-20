#!/usr/bin/env python3
"""
BUG #26510 미확인 부재중 배지 드리프트 헌트 (재부팅 중심, 무인)

목표 불변식:  mirror(loadUnreadData) == count(type=3 AND is_read=0)
이게 깨지면 = #26510 재현(미러가 시스템 is_read 에서 디커플).

설계 근거(실측 확정):
  - 미러 프로세스(com.hnlens.simplemode)는 NotificationListenerService(NotificationMonitor)로
    상시 유지 → lmkd/am kill 로 안 죽는다. force-stop 은 죽지만 재시작에 런처(모드전환 팝업)
    가 필요 = 비현실적·오염. → force-stop 폐기.
  - 현실적·clean·반복가능한 유일한 blind window = **재부팅**(부팅 초기, 미러가 옵저버/NLS
    바인드 전 구간). 그래서 op 를 전부 재부팅 기반으로.

drift 시도 = "재부팅 blind window 안에서 is_read 클리어" → 미러가 그 클리어를 놓치고
부팅 후 stale 를 유지하는지. (더미 행 한정. 실 증거 행은 불가침.)

robust 측정:
  - 미러 값 None(프로세스 미준비/adb 글리치) → 재시도. divergence 로 오판하지 않음.
  - is_read0 이 evidence_min 미만이면 provider 글리치로 간주 → 재시도(가짜 0 방지).
  - divergence 는 (측정 ok) AND (mirror != is_read0) 일 때만 기록.

사용:
  python missed_badge_drift_hunt.py --serial <SERIAL> [--cycles 20] [--keep-going]
"""
import argparse
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

CALL_LOG = "content://call_log/calls"
DUMMY_PREFIX = "990000"
MIRROR_PKG = "com.hnlens.simplemode"

# ---- adb helpers ------------------------------------------------------------

def adb(serial, *args, timeout=60):
    cmd = ["adb", "-s", serial] + list(args)
    try:
        # Windows 로케일(cp949)로 logcat UTF-8(em-dash·일본어) 디코딩 시 크래시 → utf-8 강제.
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "<timeout>"

def sh(serial, shell_cmd, timeout=60):
    return adb(serial, "shell", shell_cmd, timeout=timeout)

def mirror_pid(serial):
    rc, out = sh(serial, "pidof com.hnlens.simplemode")
    return out.strip() or None

def wait_mirror_alive(serial, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if mirror_pid(serial):
            return True
        time.sleep(2)
    return False

def wait_boot(serial, timeout=200):
    adb(serial, "wait-for-device", timeout=timeout)
    t0 = time.time()
    while time.time() - t0 < timeout:
        rc, out = sh(serial, "getprop sys.boot_completed")
        if out.strip() == "1":
            return True
        time.sleep(2)
    return False

def wait_provider_up(serial, timeout=120):
    """call_log provider 가 응답할 때까지(부팅 초기). 미러 바인드보다 이르다."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        rc, out = sh(serial, f'content query --uri {CALL_LOG} --projection _id --where "type=3"')
        if "Row:" in out or "No result" in out:
            return True
        time.sleep(0.3)
    return False

# ---- measurements -----------------------------------------------------------

def count_where(serial, where):
    rc, out = sh(serial, f'content query --uri {CALL_LOG} --projection _id --where "{where}"')
    return len(re.findall(r"^Row:", out, re.M))

def is_read0_count(serial):
    return count_where(serial, "type=3 AND is_read=0")

def dummy_ids(serial, is_read=None):
    where = f"type=3 AND number LIKE '{DUMMY_PREFIX}%'"
    if is_read is not None:
        where += f" AND is_read={is_read}"
    rc, out = sh(serial, f'content query --uri {CALL_LOG} --projection _id --where "{where}"')
    return [int(m) for m in re.findall(r"_id=(\d+)", out)]

def read_mirror_launcher(serial):
    """onChange 발화 후 logcat 파싱. is_read 는 절대 안 건드림(new 토글)."""
    ids = dummy_ids(serial)
    if not ids:
        return (None, None)
    adb(serial, "logcat", "-c")
    probe = ids[0]
    sh(serial, f'content update --uri {CALL_LOG} --bind new:i:0 --where "_id={probe}"')
    sh(serial, f'content update --uri {CALL_LOG} --bind new:i:1 --where "_id={probe}"')
    time.sleep(2.5)
    rc, out = adb(serial, "logcat", "-d")
    mirror = launcher = None
    for m in re.finditer(r"loadUnreadData unreadCallCount:\s*(\d+)", out):
        mirror = int(m.group(1))
    for m in re.finditer(r"Launcher.*getUnreadMissedCallCount cursor count:\s*(\d+)", out):
        launcher = int(m.group(1))
    if launcher is None:
        for m in re.finditer(r"updateNewMissedCallCount.*missedCallNotificationCount\s*=\s*(\d+)", out):
            launcher = int(m.group(1))
    return (mirror, launcher)

def read_counts(serial, evidence_min, log, retries=5):
    """robust: (dict, ok). ok=False 면 측정 신뢰불가 → divergence 판정 제외."""
    a = mirror = launcher = None
    for attempt in range(retries):
        a = is_read0_count(serial)
        mirror, launcher = read_mirror_launcher(serial)
        # sanity: 실 증거(evidence_min) 는 항상 is_read=0 → a<evidence_min 이면 provider 글리치.
        bad = (mirror is None) or (a < evidence_min)
        if not bad:
            return ({"is_read0": a, "mirror": mirror, "launcher": launcher}, True)
        log(f"    measure retry {attempt+1}/{retries} (is_read0={a} mirror={mirror}) "
            f"mirror_pid={mirror_pid(serial)}")
        wait_mirror_alive(serial, timeout=30)
        time.sleep(3)
    return ({"is_read0": a, "mirror": mirror, "launcher": launcher}, False)

# ---- mutations (더미 한정) --------------------------------------------------

def epoch_ms():
    return int(time.time() * 1000)

def insert_dummies(serial, n):
    base = epoch_ms()
    for i in range(n):
        num = f"{DUMMY_PREFIX}{(base + i) % 100000:05d}"
        sh(serial,
           f'content insert --uri {CALL_LOG} '
           f'--bind number:s:{num} --bind type:i:3 --bind is_read:i:0 --bind new:i:1 '
           f'--bind date:l:{base + i}')

def clear_dummy_is_read(serial, ids):
    if not ids:
        return 0
    idlist = ",".join(str(i) for i in ids)
    sh(serial, f'content update --uri {CALL_LOG} --bind is_read:i:1 --bind new:i:0 --where "_id IN ({idlist})"')
    return len(ids)

def delete_dummies(serial):
    sh(serial, f"content delete --uri {CALL_LOG} --where \"number LIKE '{DUMMY_PREFIX}%'\"")

# ---- reboot-centric ops -----------------------------------------------------

def op_reboot_plain(serial, log):
    """미확인 더미 잔존 상태로 재부팅 (blind window 존재, 클리어 없음). 부팅 후 미러 로드 관찰."""
    log("  op=reboot_plain")
    adb(serial, "reboot")
    time.sleep(5)
    wait_boot(serial)
    wait_mirror_alive(serial, timeout=90)
    time.sleep(6)

def op_reboot_clear_bootwindow(serial, log):
    """★ drift 시도: 재부팅 → provider up 직후(미러 바인드 전) 더미 is_read 절반 클리어 →
    부팅 완료. 미러가 그 클리어를 놓치면 mirror>is_read0 갭."""
    log("  op=reboot_clear_bootwindow")
    adb(serial, "reboot")
    adb(serial, "wait-for-device", timeout=200)
    if not wait_provider_up(serial):
        log("    provider not up in time")
    time.sleep(random.uniform(0.0, 2.5))          # 창 안 타이밍 무작위화
    ids = dummy_ids(serial, is_read=0)
    n = clear_dummy_is_read(serial, ids[: max(1, len(ids)//2)])
    log(f"    boot-window clear on {n} dummies (mirror_pid={mirror_pid(serial)})")
    wait_boot(serial)
    wait_mirror_alive(serial, timeout=90)
    time.sleep(6)

def op_reboot_clear_before(serial, log):
    """대조: 미러 실행 중 클리어 → 재부팅. (미러가 관측했으니 갭 없어야 정상.)"""
    log("  op=reboot_clear_before")
    ids = dummy_ids(serial, is_read=0)
    n = clear_dummy_is_read(serial, ids[: max(1, len(ids)//2)])
    log(f"    pre-reboot clear on {n} dummies")
    time.sleep(2)
    adb(serial, "reboot")
    time.sleep(5)
    wait_boot(serial)
    wait_mirror_alive(serial, timeout=90)
    time.sleep(6)

OPS = [op_reboot_clear_bootwindow, op_reboot_plain, op_reboot_clear_before]

# ---- dump -------------------------------------------------------------------

def dump_state(serial, out_dir, cycle, reason, snap):
    d = os.path.join(out_dir, f"DIVERGENCE_cycle{cycle:04d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(f"reason={reason}\ncycle={cycle}\nsnapshot={snap}\n"
                f"time={datetime.now(timezone.utc).isoformat()}\n")
    for name, cmd in [
        ("all_missed_rows.txt",
         f'content query --uri {CALL_LOG} --projection _id:number:is_read:new:date --where "type=3"'),
        ("notification.txt", "dumpsys notification --noredact"),
    ]:
        rc, out = sh(serial, cmd, timeout=60)
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(out)
    rc, out = adb(serial, "logcat", "-d", timeout=60)
    with open(os.path.join(d, "logcat.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    try:
        p = subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"], capture_output=True)
        with open(os.path.join(d, "screen.png"), "wb") as f:
            f.write(p.stdout)
    except Exception:
        pass
    return d

# ---- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--cycles", type=int, default=20)
    ap.add_argument("--out", default=None)
    ap.add_argument("--keep-going", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       f"run_{args.serial}_{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    logf = open(os.path.join(out_dir, "hunt.log"), "a", encoding="utf-8")

    def log(msg):
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    rc, ver = sh(args.serial, "getprop ro.build.version.incremental")
    log(f"=== drift hunt (reboot-centric) serial={args.serial} build={ver.strip()} "
        f"cycles={args.cycles} out={out_dir} ===")

    # 실 증거 baseline 자동 감지 (더미 삽입 전 is_read=0 개수).
    delete_dummies(args.serial)
    evidence_min = is_read0_count(args.serial)
    log(f"evidence_min (real unconfirmed baseline) = {evidence_min}")
    if not wait_mirror_alive(args.serial, timeout=60):
        log("WARN mirror not alive at start")

    divergences = 0
    try:
        for cycle in range(1, args.cycles + 1):
            insert_dummies(args.serial, 2 + (cycle % 6))
            base, ok = read_counts(args.serial, evidence_min, log)
            log(f"cycle {cycle:04d} baseline {base} ok={ok}")
            if ok and base["mirror"] != base["is_read0"]:
                divergences += 1
                d = dump_state(args.serial, out_dir, cycle, "baseline", base)
                log(f"  !!! DIVERGENCE(baseline) mirror={base['mirror']} is_read0={base['is_read0']} -> {d}")
                if not args.keep_going:
                    break

            OPS[cycle % len(OPS)](args.serial, log)

            post, ok = read_counts(args.serial, evidence_min, log)
            log(f"  post {post} ok={ok}")
            if not ok:
                log("  measure NOT ok after op — skipping divergence judgment this cycle")
            elif post["mirror"] != post["is_read0"]:
                divergences += 1
                d = dump_state(args.serial, out_dir, cycle, "post_op", post)
                log(f"  !!! DIVERGENCE(post_op) mirror={post['mirror']} is_read0={post['is_read0']} -> {d}")
                if not args.keep_going:
                    break

            delete_dummies(args.serial)
    except KeyboardInterrupt:
        log("interrupted")
    finally:
        delete_dummies(args.serial)
        log(f"=== end. divergences={divergences} ===")
        logf.close()

    sys.exit(2 if divergences else 0)

if __name__ == "__main__":
    main()
