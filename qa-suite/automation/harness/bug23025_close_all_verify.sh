#!/usr/bin/env bash
###############################################################################
# bug23025_close_all_verify.sh
#
# BUG #23025 검증 자동화 스크립트  (THOR2-JAPAN / Simple mode)
#   증상: Simple mode 에서 Recents 의 "Close all" 탭 시 홈이 빈 화면(blank)으로
#         표시되는 확률적 타이밍 버그 (WindowManager 전환 Race Condition)
#
# 설계 원칙 (이슈 분석/댓글 기반):
#   1) 댓글에서 확인된 재현 패턴을 개별 시나리오 함수로 분리하여 고반복(기본 100회) 수행
#   2) 단순 "빈 화면" 외 변형 증상까지 판정
#        - ANR (Input dispatching timed out / ANR 다이얼로그)
#        - empty RecentsActivity 잔존(전면)
#        - Recent 버튼 무반응(recents 미표시)
#        - 느린 복귀(slow recovery)
#   3) logcat 상시 캡처(전체+필터) + 비정상 시 즉시 스냅샷(스크린샷/dumpsys/logcat tail)
#   4) "하드 FAIL" 과 "의심 WARN" 을 분리 집계 → 과대계상 방지(스크린샷 수동검토 유도)
#
# 핵심 판정 신호(개발자 분석 로그와 동일):
#   FAIL : mCurrentFocus=null(=focus none) / empty RecentsActivity 전면 미복귀 / ANR
#   WARN : 느린 복귀 / blank 픽셀(자동의심) / Recent 무반응  → 산출물 수동확인 후 최종판정
#
# ── 사용 전 준비 ────────────────────────────────────────────────────────────
#   - 대상 단말이 "Simple mode" 상태여야 함 (스크립트가 강제하지 않음)
#   - USB 디버깅 허용 / 화면 잠금(보안 잠금) 해제 권장 / 가능하면 "화면 항상 켜기" ON
#   - HOME(SimpleLauncher) 컴포넌트 자동탐지 실패 시 --home 으로 직접 지정
#   - clear-all 버튼 UI 탐색 실패 대비 CLEAR_ALL_X / CLEAR_ALL_Y 폴백좌표 설정 가능
#   - 하드웨어 키 경합 경로(전화/메시지/연락처/즐겨찾기)를 실제로 검증하려면
#       `adb shell getevent -lt` 로 키코드 확인 후 --hwkeys 로 지정
#   - blank 픽셀 자동판정에는 ImageMagick(convert/magick) 필요(없으면 자동 생략)
###############################################################################

############################# [ 설정 기본값 ] ##################################
COUNT=100                 # 시나리오당 반복 횟수
ITER_GAP=0.6              # 반복 간 간격(초)
RECENTS_SETTLE=0.8        # APP_SWITCH 후 recents 안정 대기
RECENTS_PREKEY_QUIET=0.6  # APP_SWITCH 전 정지시간: 직전 키 입력의 차단 윈도우(eventInBlockTime, ~500ms) 경과 보장
CHECK_EARLY=0.3           # close-all 직후 1차 상태확인 시점
CHECK_LATE=1.5            # 추가입력 없이 자연복귀 여부 확인하는 2차 시점
LAUNCH_WAIT=0.5           # 앱 1개 실행 후 대기
APPS_PER_ITER=3           # 매 반복마다 recents 적재용으로 실행할 앱 수
TOGGLE_BURST=12           # toggle 시나리오의 Recent<->Home 연타 횟수
POST_BOOT_WAIT=8          # 부팅 완료 후 안정 대기
BOOT_TIMEOUT=180          # 부팅 완료 대기 한도(초)
BUGREPORT_ON_FAIL=0       # FAIL 시 full bugreport 수집 여부 (-b 로 ON; 수 분 소요)
ENABLE_PIXEL_CHECK=1      # blank 픽셀 자동의심 판정 사용(ImageMagick 필요)
MAIN_DISPLAY=0            # 판정 대상 메인 디스플레이 ID (듀얼 디스플레이 단말 대응; 서브 화면은 무시)

# ── 스트레스 시나리오(옵션) 파라미터 ───────────────────────────────────────────
BURST_COUNT=10            # closeall_keymash/switchstorm: 전환 창에 쏟을 키 입력 횟수
BURST_KEY_GAP=0.04        # (배치 단발 연사로 전환되어 현재 미사용. 참고용으로 남김)
BURST_PROBE_DELAY=0.25    # 버스트 직후 "복구 키 누르기 전" 상태 확인까지 대기(초)
NOFOCUS_PERSIST_GATE=0.5  # no_focus 재확인 간격(초): 이 시간 뒤에도 null이면 진짜 stall 로 판정
WITNESS_PROBE=0           # 1이면 no-focus 위트니스를 FAIL 없이 카운트만 보고(캘리브레이션용)
BURST_START_DELAY=0.05    # 모두닫기 탭 후 버스트 시작까지(전환 취약창 ~50~150ms 진입)
CYCLE_REPEAT=6            # rapid_close_cycle: 한 회차 내 Recent↔Close all 반복 횟수
RAPID_CYCLE_GAP=0.15      # rapid_close_cycle: 사이클 간 최소 간격(초)
BURST_KEYS=()             # 버스트 전용 키코드(미지정 시 HW_KEYS, 그것도 없으면 표준 내비키 사용)

# recents 적재용 앱 후보(설치 안 된 패키지는 자동 skip). --apps 로 교체 가능
APPS=(com.android.settings com.android.contacts com.android.dialer \
      com.android.messaging com.android.deskclock com.android.calculator2 \
      com.android.documentsui)

# 하드웨어 키 키코드(기본 비움 → 미설정 시 앱직접실행으로 대체). --hwkeys 로 지정
# 예) --hwkeys "KEYCODE_CALL,KEYCODE_F1,KEYCODE_F2,KEYCODE_F3"
HW_KEYS=()

# close-all 버튼 식별자(텍스트/리소스ID/일본어). 디바이스에 맞게 추가/수정 가능
CLEAR_ALL_RE='clear_all|clearAll|clear_all_button|clearAllButton|すべて閉じる|全て閉じる|すべて消去|Clear all|Clear All|Close all|Close All|CLEAR ALL'

# close-all 좌표 폴백(UI 탐색 실패 시 사용). 빈 값이면 폴백 안 함
CLEAR_ALL_X=""
CLEAR_ALL_Y=""

# recents 액티비티 식별 정규식(close-all 후 전면에 남으면 버그). 디바이스에 맞게 조정
RECENTS_RE='RecentsActivity|QuickstepLauncher|Quickstep'

SCENARIOS_DEFAULT="basic,hwkeys,toggle,reentry,screenoff"
###############################################################################

############################# [ 인자 파싱 ] ####################################
SERIAL=""
SCENARIOS=""
SCENARIOS_EXPLICIT=0      # -S 로 시나리오를 명시했는지(메뉴 표시 여부 판단)
MENU_MODE=auto            # 대화형 메뉴: auto(TTY+무인자 시 표시) / on / off
OUTROOT="./bug23025_logs"
HOME_COMPONENT_OVERRIDE=""

usage() {
  cat <<EOF
사용법: $0 [옵션]
       (인자 없이 더블클릭/실행 시 대화형 메뉴로 시나리오·횟수·단말을 선택)

  -s, --serial    <id>     대상 단말 시리얼 (adb -s)
  -n, --count     <n>      시나리오당 반복 횟수 (기본 ${COUNT})
  -S, --scenarios <list>   실행 시나리오 콤마구분
                           (기본: ${SCENARIOS_DEFAULT}; 추가: reboot)
  -o, --out       <dir>    산출물 루트 디렉토리 (기본 ${OUTROOT})
  -d, --delay     <sec>    반복 간 간격 (기본 ${ITER_GAP})
      --home      <comp>   HOME 컴포넌트 강제지정 (예: com.hnlens.simplelauncher/.MainActivity)
      --apps      <list>   recents 적재용 패키지 콤마구분
      --hwkeys    <list>   하드웨어 키 키코드 콤마구분 (전화/메시지/연락처/즐겨찾기 경로 검증)
      --clearxy   <x,y>    "모두 닫기" 버튼 폴백 좌표 (UI 탐색 실패 시 사용; 예: --clearxy 240,720)
      --display   <id>     판정 대상 메인 디스플레이 ID (기본 ${MAIN_DISPLAY}; 듀얼 디스플레이 단말 대응)
      --burstkeys <list>   스트레스 버스트 전용 키코드 콤마구분(미지정 시 --hwkeys, 그것도 없으면 표준 내비키)
      --no-pixel           blank 픽셀 자동판정 비활성
      --witness-probe      no-focus 위트니스를 FAIL 없이 카운트만 보고(캘리브레이션; 예: -S basic 로 오탐률 측정)
  -b, --bugreport          FAIL 시 full bugreport 수집(수 분 소요)
      --menu               대화형 메뉴 강제 표시(시나리오/횟수/단말 선택)
      --no-menu            대화형 메뉴 생략(무인자 실행 시 기본 시나리오로 진행; CI용)
  -h, --help               도움말

시나리오:
  basic      : 앱 다수 실행 → Recent → Close all (기본 경로)
  hwkeys     : 전화/메시지/연락처/즐겨찾기 키 → Home 반복 후 Close all
  toggle     : Recent<->Home 고속 연타(압력) 후 Close all
  reentry    : Close all 전환 진행 중 APP_SWITCH 재입력(50~150ms 윈도우)
  screenoff  : 화면 OFF 상태 APP_SWITCH → 즉시 HOME → 깨움
  reboot     : 재부팅 후 홈 정상표시 확인(방전→충전부팅의 일부 대체, 저반복 권장)

스트레스 시나리오(옵션, 기본 미포함 — -S 로 선택):
  closeall_keymash     : 모두닫기 직후 전환 취약창에 하드키/내비키 난타(키 경쟁/오라우팅)
  closeall_switchstorm : 모두닫기 전환 중 APP_SWITCH 연타(빈 Recents 재진입; reentry 포화)
  rapid_close_cycle    : 한 회차 내 Recent↔모두닫기 연속 반복(dismiss 재진입/startHome 중복)

수동 병행 권장(자동화 불가/부분만 가능):
  · 완전 방전 후 충전 케이블 연결 자동부팅  (reboot 로 부팅직후 홈만 부분 대체)
  · 홈 배경화면 변경 후 키조작+Close all     (변경은 수동, 키조작 경로는 toggle/basic 으로 커버)
  · 플래시 후 최초 진입 + Menu 수회 + Home    (reboot 시나리오에서 Menu+Home 부분 모사)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--serial)    SERIAL="$2"; shift 2;;
    -n|--count)     COUNT="$2"; shift 2;;
    -S|--scenarios) SCENARIOS="$2"; SCENARIOS_EXPLICIT=1; shift 2;;
    -o|--out)       OUTROOT="$2"; shift 2;;
    -d|--delay)     ITER_GAP="$2"; shift 2;;
    --home)         HOME_COMPONENT_OVERRIDE="$2"; shift 2;;
    --apps)         IFS=',' read -r -a APPS <<<"$2"; shift 2;;
    --hwkeys)       IFS=',' read -r -a HW_KEYS <<<"$2"; shift 2;;
    --clearxy)      IFS=',' read -r CLEAR_ALL_X CLEAR_ALL_Y <<<"$2"; shift 2;;
    --display)      MAIN_DISPLAY="$2"; shift 2;;
    --burstkeys)    IFS=',' read -r -a BURST_KEYS <<<"$2"; shift 2;;
    --no-pixel)     ENABLE_PIXEL_CHECK=0; shift;;
    --witness-probe) WITNESS_PROBE=1; shift;;
    -b|--bugreport) BUGREPORT_ON_FAIL=1; shift;;
    --menu)         MENU_MODE=on; shift;;
    --no-menu)      MENU_MODE=off; shift;;
    -h|--help)      usage; exit 0;;
    *) echo "알 수 없는 옵션: $1" >&2; usage; exit 1;;
  esac
done
SCENARIOS="${SCENARIOS:-$SCENARIOS_DEFAULT}"

############################# [ ADB 래퍼/로깅 ] ################################
ADB=(adb)
[ -n "$SERIAL" ] && ADB=(adb -s "$SERIAL")
adbx() { "${ADB[@]}" "$@"; }

# NO_COLOR 환경변수가 있으면 ANSI 색 코드 제거(cmd 콘솔/.bat 더블클릭 시 깨짐 방지)
if [ -n "${NO_COLOR:-}" ]; then
  info(){ printf '[INFO] %s\n' "$*"; }
  warn(){ printf '[WARN] %s\n' "$*"; }
  err (){ printf '[FAIL] %s\n' "$*"; }
else
  info(){ printf '\033[36m[INFO]\033[0m %s\n' "$*"; }
  warn(){ printf '\033[33m[WARN]\033[0m %s\n' "$*"; }
  err (){ printf '\033[31m[FAIL]\033[0m %s\n' "$*"; }
fi

############################# [ 산출물 디렉토리 ] ##############################
OUTDIR="$OUTROOT/run_$(date +%Y%m%d_%H%M%S)"
ARTIFACT_DIR="$OUTDIR/artifacts"
LOGCAT_FILE="$OUTDIR/logcat_full.log"
LOGCAT_FILTERED="$OUTDIR/logcat_filtered.log"
RESULT_CSV="$OUTDIR/results.csv"
SUMMARY_FILE="$OUTDIR/summary.txt"
mkdir -p "$ARTIFACT_DIR"
echo "scenario,index,level,reason,artifact_dir" > "$RESULT_CSV"
# 모든 콘솔 출력을 console.log 에도 기록
exec > >(tee -a "$OUTDIR/console.log") 2>&1

TMP="$(mktemp -d)"
LOGCAT_PID=""
LOGCAT_FILT_PID=""
cleanup() {
  [ -n "$LOGCAT_PID" ]      && kill "$LOGCAT_PID"      >/dev/null 2>&1
  [ -n "$LOGCAT_FILT_PID" ] && kill "$LOGCAT_FILT_PID" >/dev/null 2>&1
  [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
}
trap cleanup EXIT INT TERM

############################# [ ImageMagick 탐지 ] #############################
HAVE_MAGICK=0
MAGICK=""
if command -v magick >/dev/null 2>&1; then MAGICK="magick"; HAVE_MAGICK=1
elif command -v convert >/dev/null 2>&1; then MAGICK="convert"; HAVE_MAGICK=1
fi

############################# [ 상태 조회 헬퍼 ] ###############################
# 듀얼 디스플레이 단말 대응: 판정은 항상 메인 디스플레이(MAIN_DISPLAY)로 한정한다.
# dumpsys 의 디스플레이 출력 순서가 일정치 않아(window=서브 먼저, activity=메인 먼저 등)
# grep -m1 은 서브 디스플레이의 상태를 잘못 집을 수 있으므로 awk 로 해당 디스플레이 블록을 특정한다.

# 메인 디스플레이의 현재 포커스 윈도우 라인 (dumpsys window)
get_focus() {
  adbx shell dumpsys window 2>/dev/null | tr -d '\r' \
    | awk -v d="$MAIN_DISPLAY" '
        $0 ~ ("Display: mDisplayId=" d) {f=1}
        f && /mCurrentFocus=/           {print; exit}'
}

# 메인 디스플레이의 최상위 Resumed 액티비티 라인 (dumpsys activity activities)
get_resumed() {
  adbx shell dumpsys activity activities 2>/dev/null | tr -d '\r' \
    | awk -v d="$MAIN_DISPLAY" '
        $0 ~ ("Display #" d)        {f=1; next}
        /^Display #[0-9]+/          {f=0}
        f && /(topResumedActivity|mResumedActivity|ResumedActivity)=/ {print; exit}'
}

# 메인 디스플레이 포커스 없음(=빈 화면 신호)인지 판정.
# 메인 블록 식별 실패(단일 디스플레이 구형 등) 시: 비-null 포커스가 하나라도 있으면 정상으로 폴백.
focus_is_none() {
  local f; f="$(get_focus)"
  if [ -z "$f" ]; then
    if adbx shell dumpsys window 2>/dev/null | grep -E 'mCurrentFocus=' | grep -qv '=null'; then
      return 1
    fi
    f="null"
  fi
  [[ "$f" == *"=null"* || "$f" == *"<none>"* ]]
}

recents_is_up() { get_resumed | grep -qE "$RECENTS_RE"; }

# close-all 직후 비정상 상태 판정 (BAD_REASON 에 사유 기록)
check_bad_state() {
  BAD_REASON=""
  if focus_is_none; then BAD_REASON="no_focus(mCurrentFocus=null)"; return 0; fi
  if get_resumed | grep -qE "$RECENTS_RE"; then
    BAD_REASON="empty_recents_foreground"
    return 0
  fi
  return 1
}

# ANR 키워드 누적 카운트(전체 logcat 기준)
anr_count() {
  local c
  c="$(grep -cE 'ANR in |Input dispatching timed out|Reason: Input dispatching' "$LOGCAT_FILE" 2>/dev/null)"
  echo "${c:-0}"
}

# (B-1) 메인 디스플레이의 "포커스 윈도우 상실(=빈 화면/무포커스)" 신호 누적 카운트.
# 복구됐더라도 회차 중 한 번이라도 떴으면 잡기 위한 logcat 위트니스.
nofocus_count() {
  # 고신뢰 신호만: 입력 디스패치 타임아웃 수준의 "포커스 윈도우 없음".
  # 정상 전환 중 잠깐 찍히는 'Changing focus ... to null' churn 은 오탐이라 제외한다.
  local c
  c="$(grep -cE 'does not have a focused window' "$LOGCAT_FILE" 2>/dev/null)"
  echo "${c:-0}"
}
anr_dialog_present() {
  adbx shell dumpsys window 2>/dev/null | grep -qiE 'Application Not Responding|Not Responding|ANRDialog'
}

# blank 픽셀 의심 판정(그레이 표준편차 매우 낮음). 도구 없거나 실패 시 false
screen_is_blank() {
  [ "$HAVE_MAGICK" -eq 1 ] || return 1
  local png="$1"
  adbx exec-out screencap -p > "$png" 2>/dev/null
  [ -s "$png" ] || return 1
  local sd
  sd="$("$MAGICK" "$png" -colorspace Gray -format '%[fx:standard_deviation]' info: 2>/dev/null)"
  [ -n "$sd" ] || return 1
  awk -v s="$sd" 'BEGIN{ exit !(s < 0.02) }'
}

############################# [ 동작 헬퍼 ] ####################################
ensure_awake() {
  adbx shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1
  adbx shell wm dismiss-keyguard >/dev/null 2>&1
}

open_recents() { adbx shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1; }

# recents 열고 표시 확인. 미표시 시 WARN(Recent 무반응) 설정 후 1 반환
open_recents_checked() {
  local attempt
  for attempt in 1 2 3; do
    # 직전 키(특히 HOME) 직후 APP_SWITCH 를 쏘면 런처 키 차단 윈도우(eventInBlockTime, ~500ms)에 먹혀
    # overview 가 안 열린다. APP_SWITCH "전"에 정지시간을 둬서 차단 윈도우를 확실히 넘긴 뒤 누른다.
    sleep "$RECENTS_PREKEY_QUIET"
    open_recents
    sleep "$RECENTS_SETTLE"
    recents_is_up && return 0
  done
  RES_STATUS="WARN"; RES_REASON="recents_not_shown(unresponsive?)"
  return 1
}

launch_some_apps() {
  local n="${1:-3}" launched=0 pkg
  for pkg in "${APPS[@]}"; do
    [ "$launched" -ge "$n" ] && break
    if adbx shell monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; then
      launched=$((launched+1)); sleep "$LAUNCH_WAIT"
    fi
  done
  adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  sleep 0.4
}

# uiautomator dump 로 clear-all 탐색 후 탭. 실패 시 폴백좌표, 그래도 실패 시 1 반환
find_and_tap_clear_all() {
  local tries=0 node bounds x1 y1 x2 y2 cx cy
  while [ "$tries" -lt 3 ]; do
    # Git Bash(MSYS) 경로변환 회피: adb pull 미사용. dump→cat 을 "단일 따옴표 문자열"로
    # 단말에서 실행하면 인자가 '/'로 시작하지 않아 호스트가 /sdcard 를 Windows 경로로 바꾸지 않음.
    # 출력 리다이렉션(> "$TMP/...")은 셸이 직접 처리하므로 안전.
    adbx shell 'uiautomator dump /sdcard/uidump.xml >/dev/null 2>&1; cat /sdcard/uidump.xml 2>/dev/null' > "$TMP/uidump.xml" 2>/dev/null
    if [ -s "$TMP/uidump.xml" ]; then
      node="$(grep -oE "<node[^>]*(${CLEAR_ALL_RE})[^>]*>" "$TMP/uidump.xml" | head -1)"
      if [ -n "$node" ]; then
        bounds="$(printf '%s' "$node" | grep -oE 'bounds="\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]"' | head -1)"
        if [ -n "$bounds" ]; then
          read -r x1 y1 x2 y2 <<<"$(printf '%s' "$bounds" | grep -oE '[0-9]+' | tr '\n' ' ')"
          cx=$(( (x1 + x2) / 2 )); cy=$(( (y1 + y2) / 2 ))
          adbx shell input tap "$cx" "$cy" >/dev/null 2>&1
          return 0
        fi
      fi
    fi
    tries=$((tries+1)); sleep 0.4
  done
  if [ -n "$CLEAR_ALL_X" ] && [ -n "$CLEAR_ALL_Y" ]; then
    adbx shell input tap "$CLEAR_ALL_X" "$CLEAR_ALL_Y" >/dev/null 2>&1
    return 0
  fi
  return 1
}

############################# [ 부팅 대기 ] ####################################
wait_boot_complete() {
  local t=0 b
  adbx wait-for-device
  while [ "$t" -lt "$BOOT_TIMEOUT" ]; do
    b="$(adbx shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
    [ "$b" = "1" ] && return 0
    sleep 3; t=$((t+3))
  done
  return 1
}

############################# [ 시나리오 정의 ] ################################
# 각 시나리오는 동작만 수행. 조기 WARN 시 RES_STATUS/RES_REASON 설정 후 return.
# 정상 진행 시 RES_STATUS 는 PENDING 유지 → 루프가 evaluate_iteration 호출.

scn_basic() {
  launch_some_apps "$APPS_PER_ITER"
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
}

HWKEY_WARNED=0
scn_hwkeys() {
  local kc p
  if [ "${#HW_KEYS[@]}" -gt 0 ]; then
    for kc in "${HW_KEYS[@]}"; do
      adbx shell input keyevent "$kc" >/dev/null 2>&1; sleep 0.25
      adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1; sleep 0.2
    done
  else
    if [ "$HWKEY_WARNED" -eq 0 ]; then
      warn "HW_KEYS 미설정 → 앱 직접실행으로 대체(하드웨어 키 경합 경로는 미검증). getevent 로 키코드 확인 후 --hwkeys 권장."
      HWKEY_WARNED=1
    fi
    for p in "${APPS[@]:0:4}"; do
      adbx shell monkey -p "$p" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; sleep 0.3
      adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1; sleep 0.2
    done
  fi
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
}

scn_toggle() {
  local j
  # Menu(=APP_SWITCH) <-> Home 고속 연타 압력
  for (( j=0; j<TOGGLE_BURST; j++ )); do
    adbx shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1
    adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  done
  launch_some_apps "$APPS_PER_ITER"
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
}

scn_reentry() {
  launch_some_apps "$APPS_PER_ITER"
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
  # 전환 진행 중(50~150ms) APP_SWITCH 재입력 → 빈 RecentsActivity 재진입 유도
  sleep 0.05; adbx shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1
  sleep 0.05; adbx shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1
  recover_home_after_burst   # HOME 으로 복귀 → 홈 정상 복귀해야 PASS (빈 최근앱 자체는 정상)
}

scn_screenoff() {
  launch_some_apps "$APPS_PER_ITER"          # recents 적재
  adbx shell input keyevent KEYCODE_SLEEP >/dev/null 2>&1   # 화면 OFF
  sleep 0.6
  adbx shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1   # 꺼진 상태 APP_SWITCH
  sleep 0.3
  adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1         # 바로 HOME
  sleep 0.4
  adbx shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1       # 깨움 + 키가드 해제
  adbx shell wm dismiss-keyguard >/dev/null 2>&1
}

scn_reboot() {
  local k
  info "  단말 재부팅 중... (부팅 완료 대기)"
  adbx reboot
  if ! wait_boot_complete; then RES_STATUS="WARN"; RES_REASON="boot_timeout"; return; fi
  sleep "$POST_BOOT_WAIT"
  ensure_awake
  # 플래시 후 최초진입 패턴 일부 모사: Menu 수회 + Home
  for k in 1 2 3; do adbx shell input keyevent KEYCODE_MENU >/dev/null 2>&1; sleep 0.2; done
  adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  sleep 0.5
}

# ── 스트레스 시나리오용 헬퍼 ──────────────────────────────────────────────────
# 회차 간 하드 리셋: 남은 다이얼러/팝업을 닫고 알려진 홈 상태로 복귀(다음 회차 오염 방지).
hard_reset_home() {
  adbx shell input keyevent KEYCODE_BACK >/dev/null 2>&1; sleep 0.15
  adbx shell input keyevent KEYCODE_BACK >/dev/null 2>&1
  sleep "$RECENTS_PREKEY_QUIET"           # 차단 윈도우 경과 후 HOME(먹힘 방지)
  adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  sleep 0.4
}

# 모두닫기 전환 창에 키 난타. 우선순위: BURST_KEYS > HW_KEYS(+내비키) > 표준 내비키.
# 의도적으로 차단 윈도우를 때리는 단계라 pre-key quiet 를 적용하지 않는다.
keymash_burst() {
  local keys=()
  if   [ "${#BURST_KEYS[@]}" -gt 0 ]; then keys=("${BURST_KEYS[@]}")
  elif [ "${#HW_KEYS[@]}"    -gt 0 ]; then keys=("${HW_KEYS[@]}" KEYCODE_MENU KEYCODE_HOME KEYCODE_BACK)
  else keys=(KEYCODE_APP_SWITCH KEYCODE_MENU KEYCODE_HOME KEYCODE_BACK)
  fi
  # BURST_COUNT 길이만큼 시퀀스를 만들어 "한 번의 input keyevent"로 단발 연사
  # (키마다 adb 왕복/sleep 제거 → 단말 내부에서 back-to-back 주입)
  local seq=() i klen="${#keys[@]}"
  for (( i=0; i<BURST_COUNT; i++ )); do seq+=("${keys[$(( i % klen ))]}"); done
  adbx shell input keyevent "${seq[@]}" >/dev/null 2>&1
}

# 전환 스트레스 후 HOME 으로 복귀 시도. 버스트 키의 차단창(~500ms) 경과 후 HOME 을 눌러
# "사용자가 홈으로 나오려 할 때 정상 복귀하는가"를 본다(이후 evaluate_iteration 이 판정).
# 빈 최근앱에 있는 것 자체는 정상이므로 감점하지 않고, HOME 복귀 실패/빈 홈만 잡는다.
recover_home_after_burst() {
  RECOVERY_MODE=1
  # (B-2) 복구 키 누르기 "전" 상태 확인 — 단, 정상 포커스 핸드오프(수십 ms)를 잘못 집지 않도록
  # 지속성 게이트: no_focus 가 보이면 짧게 대기 후 재확인해 "여전히 null일 때만" 기록한다.
  # (키를 눌러야 풀리는 진짜 stall 만 잡고, 전환 순간의 일시적 null 은 거른다)
  sleep "$BURST_PROBE_DELAY"
  BURST_BROKEN=""
  if focus_is_none; then
    sleep "$NOFOCUS_PERSIST_GATE"
    if focus_is_none; then BURST_BROKEN="no_focus(버스트 직후 지속, 복구 전)"; fi
  fi
  sleep "$RECENTS_PREKEY_QUIET"
  adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
}

# (스트레스1) 모두닫기 직후 전환 취약창에 하드키/내비키 난타
#   겨냥: 애니 종료 콜백 vs 키 startHome 경쟁, KEYCODE_F1→Contacts 오라우팅, Home/Contacts/Keyguard 충돌
scn_closeall_keymash() {
  if [ "${#BURST_KEYS[@]}" -eq 0 ] && [ "${#HW_KEYS[@]}" -eq 0 ] && [ "${BURST_HWKEY_WARNED:-0}" -eq 0 ]; then
    warn "BURST_KEYS/HW_KEYS 미설정 → 표준 내비키로 난타(벤더 키 라우팅 경로는 미검증). getevent 후 --hwkeys/--burstkeys 권장."
    BURST_HWKEY_WARNED=1
  fi
  hard_reset_home
  launch_some_apps "$APPS_PER_ITER"
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
  sleep "$BURST_START_DELAY"
  keymash_burst
  recover_home_after_burst   # HOME 으로 복귀 → 홈 정상 복귀해야 PASS
}

# (스트레스2) 모두닫기 전환 중 APP_SWITCH 연타(reentry 포화판)
#   겨냥: 전환 중 재진입으로 빈 RecentsActivity 노출, dismiss-all 닫힘 기간 새 Recent 진입 차단
scn_closeall_switchstorm() {
  hard_reset_home
  launch_some_apps "$APPS_PER_ITER"
  open_recents_checked || return
  find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
  sleep "$BURST_START_DELAY"
  # APP_SWITCH 를 BURST_COUNT 회 "한 번의 input keyevent"로 단발 연사
  local seq=() i
  for (( i=0; i<BURST_COUNT; i++ )); do seq+=(KEYCODE_APP_SWITCH); done
  adbx shell input keyevent "${seq[@]}" >/dev/null 2>&1
  recover_home_after_burst   # HOME 으로 복귀 → 홈 정상 복귀해야 PASS (빈 최근앱 자체는 정상)
}

# (스트레스3) 한 회차 내 Recent↔모두닫기 최소 settle 로 연속 반복(back-to-back dismiss 부하)
#   겨냥: onTaskRemoved dismiss 재진입, startHome 중복 호출, postDelayed 50ms 창
scn_rapid_close_cycle() {
  hard_reset_home
  local c
  for (( c=0; c<CYCLE_REPEAT; c++ )); do
    launch_some_apps "$APPS_PER_ITER"
    open_recents_checked || return
    find_and_tap_clear_all || { RES_STATUS="WARN"; RES_REASON="clear_all_not_found"; return; }
    sleep "$RAPID_CYCLE_GAP"
  done
}

############################# [ 판정 ] #########################################
# 결과를 RES_STATUS(PASS|WARN|FAIL), RES_REASON 에 기록
evaluate_iteration() {
  local anr_before="$1" nofocus_before="${2:-0}"
  RES_STATUS="PASS"; RES_REASON="ok"

  # (B-2) 버스트 직후 복구 키 누르기 전에 잡힌 no_focus — 가장 확실한 깨짐. 복구 키로 가려져도 FAIL.
  if [ -n "${BURST_BROKEN:-}" ]; then
    RES_STATUS="FAIL"; RES_REASON="$BURST_BROKEN"; return
  fi

  sleep "$CHECK_EARLY"
  local early_bad=0 early_reason=""
  if check_bad_state; then early_bad=1; early_reason="$BAD_REASON"; fi

  # 추가입력 없이 자연 복귀 여부 확인
  sleep "$CHECK_LATE"
  local late_bad=0 late_reason=""
  if check_bad_state; then late_bad=1; late_reason="$BAD_REASON"; fi

  local anr_after; anr_after="$(anr_count)"
  if [ "$anr_after" -gt "$anr_before" ] || anr_dialog_present; then
    RES_STATUS="FAIL"; RES_REASON="ANR(+$((anr_after-anr_before)))"; return
  fi
  if [ "$late_bad" -eq 1 ]; then
    RES_STATUS="FAIL"; RES_REASON="${late_reason}(미복귀)"; return
  fi

  # (B-1) logcat no-focus 위트니스: 회차 중 포커스 상실이 떴으면 복구됐어도 잡는다(복구 시나리오 한정).
  local nofocus_after nf_delta
  nofocus_after="$(nofocus_count)"; nf_delta=$(( nofocus_after - nofocus_before ))
  if [ "$nf_delta" -gt 0 ]; then
    if [ "${WITNESS_PROBE:-0}" -eq 1 ]; then
      warn "[witness] nofocus 신호 +${nf_delta} (probe 모드: FAIL 처리 안 함)"
    elif [ "${RECOVERY_MODE:-0}" -eq 1 ]; then
      RES_STATUS="FAIL"; RES_REASON="nofocus_during_burst(+${nf_delta}, 복구됨)"; return
    fi
  fi

  if [ "$ENABLE_PIXEL_CHECK" -eq 1 ] && screen_is_blank "$TMP/chk.png"; then
    if [ "${RECOVERY_MODE:-0}" -eq 1 ]; then
      # 복귀 시나리오: HOME 복귀 후 홈이 빈 화면이면 #23025 그 자체 → FAIL 로 격상
      RES_STATUS="FAIL"; RES_REASON="blank_screen(홈 복귀 후 빈 화면)"
    else
      RES_STATUS="WARN"; RES_REASON="blank_pixels(스크린샷 확인요)"
    fi
    return
  fi
  if [ "$early_bad" -eq 1 ]; then
    RES_STATUS="WARN"; RES_REASON="slow_recovery(${early_reason})"; return
  fi
}

record_failure() {
  local name="$1" idx="$2" level="$3" reason="$4"
  local d
  d="$ARTIFACT_DIR/${level}_${name}_$(printf '%04d' "$idx")_$(date +%H%M%S)"
  mkdir -p "$d"
  adbx exec-out screencap -p            > "$d/screen.png"      2>/dev/null
  adbx shell dumpsys window             > "$d/window.txt"      2>/dev/null
  adbx shell dumpsys activity activities> "$d/activities.txt"  2>/dev/null
  adbx logcat -d -v threadtime -t 3000  > "$d/logcat_tail.txt" 2>/dev/null
  # 시나리오/회차 자가식별용 컨텍스트 — 느슨한 파일만 업로드해도 어떤 시나리오인지 확정 가능
  {
    echo "scenario  : $name"
    echo "iteration : #$idx / $COUNT"
    echo "level     : $level"
    echo "reason    : $reason"
    echo "time      : $(date '+%Y-%m-%d %H:%M:%S')"
    echo "serial    : ${SERIAL:-?}"
    echo "model     : $(adbx shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
    echo "build     : $(adbx shell getprop ro.build.display.id 2>/dev/null | tr -d '\r')"
    echo "scenarios : $SCENARIOS"
  } > "$d/context.txt" 2>/dev/null
  # ANR 계열 라인을 logcat_full(전체)에서 추출 — 회차 tail(-t 3000) 밖으로 밀린 ANR도 보존
  grep -aE 'ANR in |Input dispatching timed out|does not have a focused window|Reason: Input dispatching' \
    "$LOGCAT_FILE" 2>/dev/null | sed -E 's/\r$//' | tail -80 > "$d/anr_extract.txt" 2>/dev/null
  echo "$name,$idx,$level,$reason,$d" >> "$RESULT_CSV"
  if [ "$level" = "FAIL" ] && [ "$BUGREPORT_ON_FAIL" -eq 1 ]; then
    info "  → bugreport 수집(수 분 소요)..."
    adbx bugreport "$d/bugreport.zip" >/dev/null 2>&1
  fi
}

############################# [ 시나리오 루프 ] ################################
TOTAL_PASS=0; TOTAL_WARN=0; TOTAL_FAIL=0; TOTAL_COUNT=0
SUMMARY_ROWS=()

declare -A SCN_FUNC=(
  [basic]=scn_basic [hwkeys]=scn_hwkeys [toggle]=scn_toggle
  [reentry]=scn_reentry [screenoff]=scn_screenoff [reboot]=scn_reboot
  [closeall_keymash]=scn_closeall_keymash
  [closeall_switchstorm]=scn_closeall_switchstorm
  [rapid_close_cycle]=scn_rapid_close_cycle
)

run_scenario_loop() {
  local name="$1" func="$2" count="$3"
  info "▶ 시나리오 [$name] x${count}회 시작"
  local pass=0 warn=0 fail=0 i anr_before nofocus_before
  for (( i=1; i<=count; i++ )); do
    ensure_awake
    anr_before="$(anr_count)"; nofocus_before="$(nofocus_count)"
    RES_STATUS="PENDING"; RES_REASON=""; RECOVERY_MODE=0; BURST_BROKEN=""
    "$func" "$i"
    [ "$RES_STATUS" = "PENDING" ] && evaluate_iteration "$anr_before" "$nofocus_before"

    case "$RES_STATUS" in
      PASS)
        pass=$((pass+1))
        printf '\r  진행 %d/%d  (P:%d W:%d F:%d) ' "$i" "$count" "$pass" "$warn" "$fail"
        ;;
      WARN)
        warn=$((warn+1)); echo ""
        warn "[$name #$i] WARN: $RES_REASON"
        record_failure "$name" "$i" "WARN" "$RES_REASON"
        ;;
      FAIL)
        fail=$((fail+1)); echo ""
        err  "[$name #$i] FAIL: $RES_REASON"
        record_failure "$name" "$i" "FAIL" "$RES_REASON"
        ;;
    esac
    adbx shell input keyevent KEYCODE_HOME >/dev/null 2>&1
    sleep "$ITER_GAP"
  done
  echo ""
  info "■ [$name] 결과 → PASS:$pass  WARN:$warn  FAIL:$fail  (총 $count)"
  TOTAL_PASS=$((TOTAL_PASS+pass)); TOTAL_WARN=$((TOTAL_WARN+warn))
  TOTAL_FAIL=$((TOTAL_FAIL+fail)); TOTAL_COUNT=$((TOTAL_COUNT+count))
  SUMMARY_ROWS+=("$name|$count|$pass|$warn|$fail")
}

############################# [ 프리플라이트 ] #################################
HOME_COMPONENT=""; HOME_RE=""
detect_home() {
  if [ -n "$HOME_COMPONENT_OVERRIDE" ]; then
    HOME_COMPONENT="$HOME_COMPONENT_OVERRIDE"
  else
    HOME_COMPONENT="$(adbx shell cmd package resolve-activity --brief \
        -a android.intent.action.MAIN -c android.intent.category.HOME 2>/dev/null \
        | grep -oE '[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+' | head -1 | tr -d '\r')"
  fi
}

DISP_W=0; DISP_H=0
read_display_size() {
  local s; s="$(adbx shell wm size 2>/dev/null | grep -oE '[0-9]+x[0-9]+' | tail -1 | tr -d '\r')"
  [ -n "$s" ] && { DISP_W="${s%x*}"; DISP_H="${s#*x}"; }
}

start_logcat() {
  adbx logcat -c >/dev/null 2>&1
  adbx logcat -v threadtime > "$LOGCAT_FILE" 2>/dev/null &
  LOGCAT_PID=$!
  adbx logcat -v threadtime \
      WindowManager:V ActivityManager:V AnrManager:V RecentsActivity:V \
      SimpleLauncher:V InputDispatcher:V InputReader:V '*:S' \
      > "$LOGCAT_FILTERED" 2>/dev/null &
  LOGCAT_FILT_PID=$!
}

preflight() {
  command -v adb >/dev/null 2>&1 || { err "adb 가 PATH 에 없습니다."; exit 1; }
  local state; state="$(adbx get-state 2>/dev/null | tr -d '\r')"
  if [ "$state" != "device" ]; then
    err "단말이 연결되지 않았습니다 (adb get-state=$state). 'adb devices' 확인."
    exit 1
  fi
  read_display_size
  detect_home
  info "대상 단말 : $(adbx shell getprop ro.product.model 2>/dev/null | tr -d '\r') / Android $(adbx shell getprop ro.build.version.release 2>/dev/null | tr -d '\r') / build $(adbx shell getprop ro.build.display.id 2>/dev/null | tr -d '\r')"
  info "기본 HOME : ${HOME_COMPONENT:-<탐지실패>}"
  info "디스플레이: ${DISP_W}x${DISP_H}"
  info "시나리오  : $SCENARIOS  (각 ${COUNT}회)"
  info "산출물    : $OUTDIR"
  if [ "$HAVE_MAGICK" -eq 1 ]; then
    info "blank 픽셀 자동판정: ON (${MAGICK})"
  else
    warn "ImageMagick 없음 → blank 픽셀 자동판정 생략(WARN/FAIL 스크린샷 수동검토 권장)"
  fi
  [ -z "$HOME_COMPONENT" ] && warn "기본 HOME 탐지 실패 → --home 으로 SimpleLauncher 컴포넌트 지정 권장(판정 정확도 향상)."
}

############################# [ 요약 출력 ] ####################################
print_summary() {
  {
    echo ""
    echo "================= 검증 요약 (BUG #23025) ================="
    printf "%-12s %8s %8s %8s %8s\n" "시나리오" "횟수" "PASS" "WARN" "FAIL"
    echo "---------------------------------------------------------"
    local row n c p w f
    for row in "${SUMMARY_ROWS[@]}"; do
      IFS='|' read -r n c p w f <<<"$row"
      printf "%-12s %8s %8s %8s %8s\n" "$n" "$c" "$p" "$w" "$f"
    done
    echo "---------------------------------------------------------"
    printf "%-12s %8s %8s %8s %8s\n" "합계" "$TOTAL_COUNT" "$TOTAL_PASS" "$TOTAL_WARN" "$TOTAL_FAIL"
    echo ""
    echo "산출물:"
    echo "  - logcat 전체 : $LOGCAT_FILE"
    echo "  - logcat 필터 : $LOGCAT_FILTERED"
    echo "  - 결과 CSV    : $RESULT_CSV"
    echo "  - 실패 스냅샷 : $ARTIFACT_DIR/"
    echo ""
    local anr_hits
    anr_hits="$(grep -aE 'ANR in |Input dispatching timed out|does not have a focused window' "$LOGCAT_FILE" 2>/dev/null | wc -l | tr -d ' ')"
    anr_hits="${anr_hits:-0}"
    if [ "$anr_hits" -gt 0 ]; then
      echo "[ANR 신호] logcat_full 전체에서 ${anr_hits}건 감지 (회차 tail 밖 포함):"
      grep -aE 'ANR in |Input dispatching timed out|does not have a focused window' "$LOGCAT_FILE" 2>/dev/null \
        | sed -E 's/\r$//' | tail -8 | sed 's/^/    /'
      echo ""
    fi
    if [ "$TOTAL_FAIL" -gt 0 ]; then
      echo "[판정] 하드 FAIL ${TOTAL_FAIL}건 → 수정 미완 가능성. 해당 산출물(스크린샷/logcat_tail/anr_extract) 분석 필요."
    elif [ "$anr_hits" -gt 0 ]; then
      echo "[판정] 회차 FAIL 0건이나 logcat 에 ANR 신호 ${anr_hits}건 → 캡처 사이에 ANR 발생 가능. anr_extract/logcat_full 확인 필요."
    elif [ "$TOTAL_WARN" -gt 0 ]; then
      echo "[판정] 하드 FAIL 0건 / WARN ${TOTAL_WARN}건 → WARN 스크린샷 수동검토 후 최종판정."
    else
      echo "[판정] 전 시나리오 PASS. 단, 확률 버그 특성상 2~3개 연속 빌드 재검 권장."
    fi
    echo "========================================================="
  } | tee "$SUMMARY_FILE"
}

############################# [ 대화형 메뉴 ] ##################################
# 연결 단말 자동/수동 선택 (-s 미지정 시에만). 1대면 자동, 여러 대면 번호 선택.
pick_device_interactive() {
  [ -n "$SERIAL" ] && return 0
  local devs=() s
  while IFS= read -r s; do [ -n "$s" ] && devs+=("$s"); done \
    < <(adb devices 2>/dev/null | awk 'NR>1 && $2=="device"{print $1}' | tr -d '\r')
  if [ "${#devs[@]}" -eq 0 ]; then
    err "연결된 단말이 없습니다. 'adb devices' 확인 후 다시 실행하세요."; exit 1
  elif [ "${#devs[@]}" -eq 1 ]; then
    SERIAL="${devs[0]}"; info "단말 자동 선택: $SERIAL"
  else
    echo "연결된 단말:"
    local i=1 d
    for d in "${devs[@]}"; do
      printf "  %d) %s  (%s)\n" "$i" "$d" "$(adb -s "$d" shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
      i=$((i+1))
    done
    local sel; read -r -p "대상 단말 번호 [1]: " sel; sel="${sel:-1}"
    SERIAL="${devs[$((sel-1))]:-${devs[0]}}"
  fi
  ADB=(adb -s "$SERIAL")
}

# 시나리오/횟수 선택
choose_scenarios_interactive() {
  local stress="closeall_keymash,closeall_switchstorm,rapid_close_cycle"
  echo ""
  echo "========= BUG #23025 검증 실행 메뉴 ========="
  echo " 1) 기본 시나리오      ($SCENARIOS_DEFAULT)"
  echo " 2) 스트레스 시나리오  ($stress)"
  echo " 3) 전체 (기본+스트레스)"
  echo " 4) 직접 선택"
  local g; read -r -p "시나리오 선택 [1-4] (기본 1): " g; g="${g:-1}"
  case "$g" in
    1) SCENARIOS="$SCENARIOS_DEFAULT" ;;
    2) SCENARIOS="$stress" ;;
    3) SCENARIOS="$SCENARIOS_DEFAULT,$stress" ;;
    4)
       local all=(basic hwkeys toggle reentry screenoff reboot closeall_keymash closeall_switchstorm rapid_close_cycle)
       local i=1 a; echo "개별 시나리오:"
       for a in "${all[@]}"; do printf "  %d) %s\n" "$i" "$a"; i=$((i+1)); done
       local nums sel out=() n
       read -r -p "번호를 쉼표로 입력 (예: 1,4,7): " nums
       IFS=',' read -r -a sel <<<"$nums"
       for n in "${sel[@]}"; do
         n="$(echo "$n" | tr -d ' ')"
         if [ -n "$n" ] && [ "$n" -ge 1 ] 2>/dev/null && [ "$n" -le "${#all[@]}" ] 2>/dev/null; then
           out+=("${all[$((n-1))]}")
         fi
       done
       if [ "${#out[@]}" -eq 0 ]; then warn "선택 없음 → 기본 시나리오로 진행"; SCENARIOS="$SCENARIOS_DEFAULT"
       else SCENARIOS="$(IFS=,; echo "${out[*]}")"; fi
       ;;
    *) warn "잘못된 입력 → 기본 시나리오로 진행"; SCENARIOS="$SCENARIOS_DEFAULT" ;;
  esac
  local c; read -r -p "시나리오당 반복 횟수 [기본 $COUNT]: " c
  if [ -n "$c" ]; then
    if [ "$c" -gt 0 ] 2>/dev/null; then COUNT="$c"; else warn "숫자 아님 → ${COUNT}회 유지"; fi
  fi
  echo "============================================="
  echo ""
}

# 메뉴 표시 여부: on=항상 / off=생략 / auto=(TTY && -S 미지정). 비대화형(CI/파이프)은 자동 생략.
maybe_interactive() {
  local show=0
  case "$MENU_MODE" in
    on)  show=1 ;;
    off) show=0 ;;
    *)   { [ -t 0 ] && [ "$SCENARIOS_EXPLICIT" -eq 0 ]; } && show=1 ;;
  esac
  [ "$show" -eq 1 ] || return 0
  pick_device_interactive
  choose_scenarios_interactive
}

############################# [ 메인 ] #########################################
maybe_interactive
preflight
start_logcat
info "logcat 캡처 시작 (PID full=$LOGCAT_PID, filtered=$LOGCAT_FILT_PID)"
echo ""

IFS=',' read -r -a WANT <<<"$SCENARIOS"
for s in "${WANT[@]}"; do
  s="$(echo "$s" | tr -d ' ')"
  [ -z "$s" ] && continue
  f="${SCN_FUNC[$s]:-}"
  if [ -z "$f" ]; then warn "알 수 없는 시나리오 무시: $s"; continue; fi
  run_scenario_loop "$s" "$f" "$COUNT"
  echo ""
done

print_summary

# 종료코드: FAIL 있으면 1, WARN만 있으면 2, 전부 PASS 면 0
if   [ "$TOTAL_FAIL" -gt 0 ]; then exit 1
elif [ "$TOTAL_WARN" -gt 0 ]; then exit 2
else exit 0
fi
