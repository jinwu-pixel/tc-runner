"""CallLog 타이밍 실측 스크립트.

통화 전/중/후 CallLog를 1초 간격으로 폴링하여
엔트리 생성 시점, 필드 변화를 추적한다.

사용법:
  python scripts/calllog_timing.py          # 기본 90초 관찰
  python scripts/calllog_timing.py --duration 120
"""
import argparse
import time
import sys
import os
import subprocess
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def adb_shell(cmd, timeout=10):
    try:
        r = subprocess.run(
            ["adb", "shell", cmd],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "<timeout>"


def query_recent_calllog(limit=3):
    """최근 CallLog 엔트리를 조회한다."""
    raw = adb_shell(
        "content query --uri content://call_log/calls "
        "--projection _id:number:type:date:duration",
        timeout=10,
    )
    # Row 파싱 후 date 역순 정렬하여 최신 limit개 반환
    lines = [l for l in raw.split('\n') if l.startswith('Row:')]
    # 마지막이 최신 (기본 ascending)
    lines.reverse()
    return '\n'.join(lines[:limit]) if lines else "(empty)"


def get_phone_state():
    """현재 전화 상태를 반환한다."""
    # dumpsys telephony로 상태 확인
    raw = adb_shell(
        "dumpsys telephony.registry | grep -E 'mCallState|mForegroundCallState'",
        timeout=5,
    )
    return raw.strip()


def get_calllog_count():
    """CallLog 총 건수."""
    raw = adb_shell(
        "content query --uri content://call_log/calls --projection _id --sort 'date DESC' --limit 1",
        timeout=5,
    )
    return raw


def main():
    parser = argparse.ArgumentParser(description="CallLog 타이밍 실측")
    parser.add_argument("--duration", type=int, default=90, help="관찰 시간(초)")
    parser.add_argument("--interval", type=float, default=1.0, help="폴링 간격(초)")
    args = parser.parse_args()

    print("=" * 70)
    print("  CallLog 타이밍 실측 테스트")
    print("=" * 70)
    print(f"  관찰 시간: {args.duration}초, 폴링 간격: {args.interval}초")
    print()

    # 초기 상태
    print("[초기 상태] 최근 CallLog:")
    initial = query_recent_calllog(3)
    print(f"  {initial}")
    print()

    initial_state = get_phone_state()
    print(f"[초기 전화상태] {initial_state}")
    print()

    print("-" * 70)
    print("  지금 전화를 걸거나 받으세요. CallLog 변화를 추적합니다.")
    print("  Ctrl+C로 중단 가능")
    print("-" * 70)
    print()

    # 이전 CallLog 스냅샷 (변화 감지용)
    prev_log = initial
    prev_state = "UNKNOWN"
    start = time.time()
    events = []

    try:
        while time.time() - start < args.duration:
            elapsed = time.time() - start
            now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # 전화 상태
            state_raw = get_phone_state()
            # mCallState 파싱
            if "mCallState=2" in state_raw:
                cur_state = "OFFHOOK"
            elif "mCallState=1" in state_raw:
                cur_state = "RINGING"
            else:
                cur_state = "IDLE"

            # 상태 전환 감지
            if cur_state != prev_state:
                msg = f"[{now_str}] +{elapsed:6.1f}s  ☎ 상태 전환: {prev_state} → {cur_state}"
                print(msg)
                events.append((elapsed, "STATE", f"{prev_state}→{cur_state}"))
                prev_state = cur_state

            # CallLog 변화 감지
            cur_log = query_recent_calllog(1)
            if cur_log != prev_log:
                msg = f"[{now_str}] +{elapsed:6.1f}s  📋 CallLog 변화 감지!"
                print(msg)
                print(f"  이전: {prev_log[:120]}")
                print(f"  현재: {cur_log[:200]}")
                events.append((elapsed, "CALLLOG", cur_log[:200]))
                prev_log = cur_log
            else:
                # 주기적 heartbeat (10초마다)
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    sys.stdout.write(f"\r  [{now_str}] +{elapsed:5.0f}s  상태={cur_state}  (변화 없음)")
                    sys.stdout.flush()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n  Ctrl+C — 중단")

    # 최종 상태
    elapsed = time.time() - start
    print()
    print("=" * 70)
    print("  최종 CallLog:")
    final = query_recent_calllog(3)
    print(f"  {final}")
    print()

    # 이벤트 요약
    print("=" * 70)
    print("  이벤트 타임라인")
    print("=" * 70)
    for t, typ, detail in events:
        icon = "☎" if typ == "STATE" else "📋"
        print(f"  +{t:6.1f}s  {icon} [{typ:8s}] {detail[:120]}")

    # CallLog 생성 타이밍 분석
    offhook_time = None
    idle_time = None
    calllog_time = None
    for t, typ, detail in events:
        if typ == "STATE" and "OFFHOOK" in detail and offhook_time is None:
            offhook_time = t
        if typ == "STATE" and detail.endswith("IDLE") and offhook_time is not None:
            idle_time = t
        if typ == "CALLLOG" and offhook_time is not None:
            calllog_time = t

    print()
    if offhook_time is not None:
        print(f"  OFFHOOK 시점: +{offhook_time:.1f}s")
    if idle_time is not None:
        print(f"  IDLE 시점   : +{idle_time:.1f}s")
    if calllog_time is not None:
        print(f"  CallLog 변화: +{calllog_time:.1f}s")
        if offhook_time is not None:
            print(f"  OFFHOOK → CallLog: {calllog_time - offhook_time:.1f}s")
        if idle_time is not None:
            print(f"  IDLE → CallLog   : {calllog_time - idle_time:.1f}s")
    print()


if __name__ == "__main__":
    main()
