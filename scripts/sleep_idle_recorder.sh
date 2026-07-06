#!/usr/bin/env bash
###############################################################################
# sleep_idle_recorder.sh — idle Sleep 미진입 장기 레코더 (P4, BTS #24941)
#
# 목적: 화면 OFF 후 장시간 방치하며 전원 상태를 주기 기록해
#       "suspend 로 못 들어가고 깨어있는" 구간을 잡는다.
#
# 위반 2종(유예 GRACE 경과 후만):
#   awake        : mWakefulness 가 Awake 로 남음(화면/유저액티비티/sleep키 무시)
#   wakelock_blk : WakeLockSuspendBlocker=true 가 지속(BLK_SUSTAIN 연속) = 'suspend 차단'
#                  직접 신호. wakefulness=Asleep 이어도 성립(partial wakelock 이 SoC 서스펜드를
#                  막는 가장 흔한 실제 형태 — Awake 만 보면 놓친다).
#
# 인프라 판정: 표본의 상당수가 adb_error(단말 미관측)면 exit 3.
#       '위반 0' 을 정상으로 오보하지 않기 위함(밤새 USB selective-suspend/단절 구분).
#
# 판독 주의: 알람·푸시·FOTA 등 정상 wake 도 위반으로 찍힐 수 있다. 위반 구간
#       스냅샷(dumpsys power)의 wake lock 보유자와 logcat 대조로 최종 판정할 것.
#
# 사용 예:
#   ./sleep_idle_recorder.sh -s <serial> -d 480          # 8시간 야간 기록
#   ./sleep_idle_recorder.sh -d 60 -i 15                 # 1시간, 15초 간격
# 종료코드: 위반 표본 있으면 1, 없으면 0, 인프라(미관측/adb 문제) 3
###############################################################################

SERIAL=""; DURATION_MIN=480; INTERVAL=30; GRACE=180; OUT_ROOT="./sleep_idle_logs"
MAX_SNAP=8              # dumpsys power 홀더 스냅샷 상한
SNAP_AT=3              # 위반이 이만큼 '연속(지속)'일 때만 스냅샷(초기 일시적 wake 로 예산 소진 방지)
BLK_SUSTAIN=3          # WakeLockSuspendBlocker=true 가 이만큼 연속이면 위반으로 승격
ADBERR_STREAK_GATE=10  # adb_error 연속 이만큼이면 인프라 이상(단말 미관측)
ADBERR_RATIO_GATE=30   # adb_error 비율(%) 이만큼이면 인프라 이상

usage(){ sed -n '3,24p' "$0"; cat <<EOF
옵션: -s <serial> / -d <분, 기본 480> / -i <초, 기본 30> / --grace <초, 기본 180> / -o <dir>
EOF
}
while [ $# -gt 0 ]; do
  case "$1" in
    -s) SERIAL="$2"; shift 2;;
    -d) DURATION_MIN="$2"; shift 2;;
    -i) INTERVAL="$2"; shift 2;;
    --grace) GRACE="$2"; shift 2;;
    -o) OUT_ROOT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "알 수 없는 옵션: $1"; usage; exit 3;;
  esac
done

# 무인 실행 가드: 숫자 인자 검증(오타로 0회/무한대기 방지)
for pair in "DURATION_MIN=$DURATION_MIN" "INTERVAL=$INTERVAL" "GRACE=$GRACE"; do
  v="${pair#*=}"; case "$v" in ''|*[!0-9]*) echo "숫자여야 함: $pair"; exit 3;; esac
done
[ "$INTERVAL" -lt 1 ] && { echo "-i 는 1 이상이어야 함"; exit 3; }

adbx(){ if [ -n "$SERIAL" ]; then adb -s "$SERIAL" "$@"; else adb "$@"; fi; }
adbx get-state >/dev/null 2>&1 || { echo "adb 단말 연결 확인 실패"; exit 3; }

RUN_DIR="$OUT_ROOT/run_$(date +%Y%m%d_%H%M%S)"; mkdir -p "$RUN_DIR" || exit 3
CSV="$RUN_DIR/samples.csv"; SNAPD="$RUN_DIR/snapshots"; mkdir -p "$SNAPD"
echo "epoch,time,wakefulness,display_blocker,cpu_blocker,partial_wakelocks,violation,vkind" > "$CSV"

# 실행 컨텍스트(스냅샷 업로드 시 build/serial 식별용 — 스냅샷만으론 귀속 불가)
{
  echo "scenario  : sleep_idle"
  echo "time      : $(date '+%Y-%m-%d %H:%M:%S')"
  echo "serial    : ${SERIAL:-auto}"
  echo "model     : $(adbx shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
  echo "build     : $(adbx shell getprop ro.build.display.id 2>/dev/null | tr -d '\r')"
  echo "params    : dur=${DURATION_MIN}m interval=${INTERVAL}s grace=${GRACE}s"
} > "$RUN_DIR/context.txt" 2>/dev/null

# 콘솔도 파일에 남긴다(무인 야간 창닫힘 대비)
exec > >(tee -a "$RUN_DIR/console.log") 2>&1

echo "[INFO] 화면 OFF 후 ${DURATION_MIN}분간 ${INTERVAL}s 간격 기록 (유예 ${GRACE}s). 산출물: $RUN_DIR"

# stay-awake 설정 경고: 켜져 있으면 화면이 안 꺼져 전 표본 Awake 오탐(#24941 오염)
stay="$(adbx shell settings get global stay_on_while_plugged_in 2>/dev/null | tr -d '\r')"
case "$stay" in
  ''|0|null) : ;;
  *) echo "[WARN] stay_on_while_plugged_in=$stay (충전 중 화면 항상 켜짐) — Awake 오탐 유발. 'adb shell settings put global stay_on_while_plugged_in 0' 후 재실행 권장.";;
esac

adbx shell input keyevent KEYCODE_SLEEP >/dev/null 2>&1

T0=$(date +%s); END=$(( T0 + DURATION_MIN*60 ))
VIOL=0; STREAK=0; MAXSTREAK=0; SNAPS=0; SAMPLES=0
ADBERR=0; ADBERR_STREAK=0; MAXERR_STREAK=0; BLK_STREAK=0

trap 'summary; exit $EC' INT
summary(){
  EC=0; [ "$VIOL" -gt 0 ] && EC=1
  local infra=0
  if [ "$SAMPLES" -gt 0 ] && { [ "$MAXERR_STREAK" -ge "$ADBERR_STREAK_GATE" ] || [ $(( ADBERR * 100 / SAMPLES )) -ge "$ADBERR_RATIO_GATE" ]; }; then
    infra=1; EC=3
  fi
  {
    echo "=== sleep_idle 기록 결과 ==="
    echo "표본 $SAMPLES 개 / 위반 표본 $VIOL 개 / 최장 연속 위반 $(( MAXSTREAK * INTERVAL ))s"
    echo "adb_error 표본 $ADBERR 개 (최장 연속 $MAXERR_STREAK) / 스냅샷 $SNAPS 개"
    echo "CSV: $CSV / 스냅샷: $SNAPD / 컨텍스트: $RUN_DIR/context.txt"
    if [ "$infra" -eq 1 ]; then
      echo "[인프라] adb_error 과다 — 단말이 밤새 미관측(USB selective-suspend/단절 의심)."
      echo "         '위반 0' 은 정상 아님. USB 전원관리/케이블 점검 후 재실행. (exit 3)"
    elif [ "$VIOL" -gt 0 ]; then
      echo "[판독] 위반 구간 스냅샷의 wake lock 보유자 + logcat 대조로 정상 wake(알람/푸시) vs 실 미수면 판정."
    else
      echo "[판독] 위반 0 — 단, adb_error 표본수($ADBERR)로 관측 자체가 됐는지 먼저 확인."
    fi
  } | tee -a "$RUN_DIR/summary.txt"
}

while [ "$(date +%s)" -lt "$END" ]; do
  sleep "$INTERVAL"
  now=$(date +%s); el=$(( now - T0 ))

  # dumpsys power 1회 캡처 → 원자적 파싱(종전 3회 호출/비원자 제거 + 왕복 3배 완화)
  dp="$(adbx shell dumpsys power 2>/dev/null | tr -d '\r')"
  if [ -z "$dp" ]; then
    wf="adb_error"; db=0; cb=0; wl=0
  else
    wf="$(printf '%s' "$dp" | grep -m1 -oE 'mWakefulness=[A-Za-z]+' | cut -d= -f2)"
    [ -z "$wf" ] && wf="parse_error"
    db=$(printf '%s' "$dp" | grep -c 'DisplaySuspendBlocker=true')
    cb=$(printf '%s' "$dp" | grep -c 'WakeLockSuspendBlocker=true')
    wl=$(printf '%s' "$dp" | grep -c 'PARTIAL_WAKE_LOCK')
  fi

  # 위반 판정(유예 경과 + 관측 가능한 표본에서만)
  v=0; vkind=""
  if [ "$el" -ge "$GRACE" ] && [ "$wf" != "adb_error" ] && [ "$wf" != "parse_error" ]; then
    [ "$wf" = "Awake" ] && { v=1; vkind="awake"; }
    if [ "$cb" -ge 1 ]; then
      BLK_STREAK=$((BLK_STREAK+1))
      [ "$BLK_STREAK" -ge "$BLK_SUSTAIN" ] && { v=1; vkind="${vkind:+$vkind+}wakelock_block"; }
    else
      BLK_STREAK=0
    fi
  else
    BLK_STREAK=0
  fi

  # adb_error 누적(인프라 판정용)
  if [ "$wf" = "adb_error" ]; then
    ADBERR=$((ADBERR+1)); ADBERR_STREAK=$((ADBERR_STREAK+1))
    [ "$ADBERR_STREAK" -gt "$MAXERR_STREAK" ] && MAXERR_STREAK=$ADBERR_STREAK
  else
    ADBERR_STREAK=0
  fi

  if [ "$v" -eq 1 ]; then
    VIOL=$((VIOL+1)); STREAK=$((STREAK+1))
    [ "$STREAK" -gt "$MAXSTREAK" ] && MAXSTREAK=$STREAK
    # '지속'(SNAP_AT 연속) 위반일 때만 스냅샷 — 초기 일시적 wake 로 예산 소진 방지
    if [ "$STREAK" -eq "$SNAP_AT" ] && [ "$SNAPS" -lt "$MAX_SNAP" ]; then
      printf '%s\n' "$dp" > "$SNAPD/power_$(date +%H%M%S)_${vkind}.txt" 2>/dev/null
      SNAPS=$((SNAPS+1))
    fi
    # 화면이 깨어있으면 idle 관측 baseline 복귀(다시 재우기).
    # 정상 wake 는 여기서 회수되고, 진짜 '못 자는' 단말은 계속 Awake 로 남아 위반 지속.
    [ "$wf" = "Awake" ] && adbx shell input keyevent KEYCODE_SLEEP >/dev/null 2>&1
  else
    STREAK=0
  fi

  SAMPLES=$((SAMPLES+1))
  echo "$now,$(date '+%H:%M:%S'),$wf,$db,$cb,$wl,$v,${vkind:-}" >> "$CSV"
done

summary
exit $EC
