#!/usr/bin/env bash
# =============================================================================
# THOR2_J ime_call — 하드키 숫자 이중(IME-CALL-002) 야생 포획 하니스
# -----------------------------------------------------------------------------
# 목적: 강제 재현 불가한 희귀 transient(하드 숫자키 1프레스 → 2회 입력)를
#       "평소 사용" 중 관측자 효과(=a11y 판독이 상태 교란) 없이 포획한다.
#
# 2중 무손상 캡처 (a11y 무개입, 온-디바이스 /sdcard 기록):
#   - getevent -lt : 물리 프레스 = 커널 1회 방출 증명 (deviceId=3 mtk-kpd)
#   - logcat -b all: IME/입력 파이프라인 벽시계 타임스탬프 로그 (회전 파일)
#   ※ 이중의 "검출"은 사용자 육안(터치 없이 화면 확인). 영상 캡처(screenrecord)는
#     본 폴더폰에서 동작 불안정하여 제외 — 검출은 눈, 증거는 로그.
#
# 온-디바이스 기록 → 캡처 시작 후 USB를 뽑고 단말을 평소처럼 사용 가능.
# (스트리밍이 이 기종 USB를 반복 끊었으므로 이 방식이 안전)
#
# 사용:
#   ./capture_harness.sh start   [serial]        캡처 시작 → 이후 USB 분리 가능
#   ./capture_harness.sh stop    [serial]        캡처 종료 + 로컬 pull + /sdcard 정리
#   ./capture_harness.sh extract <HH:MM:SS>      마지막 캡처에서 해당 분대 로그 추출
#   ./capture_harness.sh status  [serial]        캡처 프로세스 생존 확인
#
# 이중 목격 시:
#   1) 화면을 그대로 둔다(터치 금지 — 터치가 치유함)
#   2) 벽시계 시각(HH:MM:SS)을 적는다
#   3) USB 연결 → stop → extract <시각>
#
# 재현 유도 팁(원 정황): 메시지 앱에서 iWnn 일본어(かな) 입력 후, 화면 터치 없이
#   하드 숫자키로 다이얼러를 실행/입력하는 흐름을 평소 사용에 섞을 것.
# =============================================================================
set -u
export MSYS_NO_PATHCONV=1   # Git Bash가 remote /sdcard 경로를 Windows 경로로 망가뜨리는 것 방지 (§5.5)

CMD="${1:-}"
ARG2="${2:-}"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
SCRIPT_DIR="$(dirname "$SELF")"
OUTDIR="$SCRIPT_DIR/capture"
DEV_PREFIX="/sdcard/imecall"

pick_serial() {
  if [ -n "$ARG2" ]; then echo "$ARG2"; return; fi
  adb devices | awk 'NR>1 && $2=="device"{print $1; exit}'
}

case "$CMD" in
  start|stop|status)
    S="$(pick_serial)"
    [ -z "$S" ] && { echo "[ERR] 연결된 device 없음 (adb devices)"; exit 1; }
    ;;
esac
ADB() { adb -s "$S" "$@"; }

case "$CMD" in
  start)
    mkdir -p "$OUTDIR"
    echo "[*] device=$S"
    MODEL="$(ADB shell getprop ro.product.model | tr -d '\r')"
    case "$MODEL" in AT-M140|AT_M140) : ;; *) echo "[ERR] 예상 밖 단말: $MODEL — 중단"; exit 1;; esac
    ADB shell "rm -f ${DEV_PREFIX}_* 2>/dev/null" >/dev/null 2>&1
    ADB logcat -c >/dev/null 2>&1
    {
      echo "host_start=$(date '+%Y-%m-%d %H:%M:%S')"
      echo "dev_walltime=$(ADB shell date '+%Y-%m-%d %H:%M:%S' | tr -d '\r')"
      echo "dev_uptime_s=$(ADB shell 'cat /proc/uptime | cut -d. -f1' | tr -d '\r')"
      echo "serial=$S"; echo "model=$MODEL"
    } > "$OUTDIR/meta.txt"
    # 온-디바이스 백그라운드 (adb 분리 후에도 생존하도록 nohup+detach)
    ADB shell "( nohup logcat -b all -v threadtime -r 4096 -n 8 -f ${DEV_PREFIX}_logcat.txt >/dev/null 2>&1 & )"
    ADB shell "( nohup getevent -lt > ${DEV_PREFIX}_getevent.txt 2>&1 & )"
    sleep 1
    echo "[*] 캡처 시작됨 (logcat + getevent, 온-디바이스)"
    echo "[*] 이제 USB를 분리하고 단말을 평소처럼 사용하세요."
    echo "[*] 이중 목격 → 화면 그대로 두고 시각 기록 → 재연결 후 'stop'."
    bash "$SELF" status "$S" || true
    ;;

  stop)
    mkdir -p "$OUTDIR"
    echo "[*] device=$S — 캡처 종료 중..."
    ADB shell "pkill -f 'logcat -b all'; pkill -f getevent" >/dev/null 2>&1
    sleep 1
    STAMP="$(date '+%Y%m%dT%H%M%S')"
    DEST="$OUTDIR/$STAMP"; mkdir -p "$DEST"
    cp "$OUTDIR/meta.txt" "$DEST/" 2>/dev/null || true
    echo "[*] pull → $DEST"
    # adb.exe(Windows)는 MSYS(/c/...) 경로·공백을 못 받음 → DEST로 cd 후 상대경로(.)로 pull
    PULLED=0
    ( cd "$DEST" && adb -s "$S" pull "${DEV_PREFIX}_getevent.txt" . ) >/dev/null 2>&1 \
      && { echo "    getevent.txt ✓"; PULLED=1; }
    for f in $(ADB shell "ls ${DEV_PREFIX}_logcat.txt* 2>/dev/null" | tr -d '\r'); do
      ( cd "$DEST" && adb -s "$S" pull "$f" . ) >/dev/null 2>&1
    done
    if ls "$DEST"/*logcat* >/dev/null 2>&1; then echo "    logcat ✓"; PULLED=1; else echo "    [WARN] logcat 없음"; fi
    # pull 성공 확인 후에만 device 정리 (실패 시 원본 보존 = 데이터 안전)
    if [ "$PULLED" = "1" ]; then
      ADB shell "rm -f ${DEV_PREFIX}_* 2>/dev/null" >/dev/null 2>&1
      echo "    device 정리됨"
    else
      echo "    [WARN] pull 실패 → device 파일 보존(rm 생략). 수동 확인 요망."
    fi
    echo "$DEST" > "$OUTDIR/last_capture.txt"
    echo "[*] 완료. 이중 목격 시각으로:  bash $SELF extract <HH:MM:SS>"
    ;;

  extract)
    TS="$ARG2"
    [ -z "$TS" ] && { echo "사용: $0 extract <HH:MM:SS>"; exit 1; }
    DEST="$(cat "$OUTDIR/last_capture.txt" 2>/dev/null)"
    [ -z "$DEST" ] && { echo "[ERR] 최근 캡처 없음 (먼저 stop)"; exit 1; }
    HHMM="${TS%:*}"
    echo "[*] $DEST — $TS 부근 추출"
    echo "=== 입력/IME 관련 logcat ($HHMM 분대) ==="
    cat "$DEST"/*logcat*.txt* 2>/dev/null | grep -E "$HHMM" \
      | grep -iE "keycode|keyevent|commit|inputmethod|iwnn|dialer|dialpad|interceptKey|getDefaultLsDialer|InputConnection" \
      | head -80
    echo "=== getevent 물리 프레스 (숫자/기호) ==="
    grep -E "KEY_[0-9]|NUMERIC_STAR|NUMERIC_POUND" "$DEST/imecall_getevent.txt" 2>/dev/null | tail -60
    echo "[*] getevent=monotonic. meta.txt 의 dev_walltime↔dev_uptime_s 로 벽시계 보정."
    ;;

  status)
    echo "[*] device=$S 캡처 프로세스:"
    ADB shell "ps -A -o NAME 2>/dev/null | grep -E 'logcat|getevent'" | tr -d '\r' | sort -u | sed 's/^/    /'
    N="$(ADB shell "ls ${DEV_PREFIX}_* 2>/dev/null | wc -l" | tr -d '\r ')"
    echo "    /sdcard 캡처 파일: ${N:-0}"
    ;;

  *)
    grep -E '^#( |=)' "$0" | sed 's/^# \{0,1\}//'
    ;;
esac
