#!/usr/bin/env bash
###############################################################################
# reboot_cycle_verify.sh — 반복 재부팅 검증 (P2)
#
# 대상 이슈:
#   - BTS #25762 : 반복 재부팅 후 홈(MIVE Home) "계속 중지됨" 팝업
#   - BTS #25334 / #25278 : 부팅 중 메뉴키 입력 → 블랙/이상 화면
#   - MR DATA-001/002 : DATA OFF/ON 상태로 재부팅 → 상태 유지 + 데이터 동작/비동작
#
# 회차 흐름:
#   [데이터 상태 설정] → reboot → adb 복귀 대기 → (부팅 구간 키 스윕: 취약창 타격)
#   → boot_completed → 홈 전면 대기 → 판정(홈크래시/팝업/무포커스/데이터) → 기록
#
# 판정/아티팩트 규약은 bug23025 하니스와 동일 계열:
#   display-0 스코핑, FAIL/WARN 시 screen.png/window.txt/activities.txt/logcat/context.txt,
#   results.csv, summary.txt, 종료코드 FAIL=1 / WARN-only=2 / PASS=0
#
# 부팅 타이밍 프로브 내장: 회차마다 adb복귀/boot_completed/홈표시 소요를 출력하므로
#   첫 실행(-n 3 권장)으로 이 단말의 타이밍을 확인한 뒤 본 실행을 돌리면 된다.
#
# 사용 예:
#   ./reboot_cycle_verify.sh -s <serial> -n 3            # 타이밍 프로브 겸 스모크
#   ./reboot_cycle_verify.sh -s <serial> -n 200          # 야간 무인(회차당 ~60-90s)
#   ./reboot_cycle_verify.sh --data-mode off -n 50       # DATA OFF 유지 검증만
#   ./reboot_cycle_verify.sh --no-bootkeys -n 100        # 키 스윕 없이 순수 재부팅만
###############################################################################

############################# [ 설정 기본값 ] ##################################
COUNT=20                   # 반복 횟수(회차당 ~60-90초 소요)
SERIAL=""
OUT_ROOT="./reboot_cycle_logs"
MAIN_DISPLAY=0

BOOT_TIMEOUT=180           # reboot 후 boot_completed 까지 최대 대기(초)
ADB_TIMEOUT=120            # reboot 후 adb 복귀 최대 대기(초)
HOME_WAIT=20               # boot_completed 후 홈 전면 표시 최대 대기(초)
SLOW_HOME_SEC=12           # 이보다 늦게 홈이 뜨면 WARN(slow_home)

BOOT_KEY_MODE=1            # 1=부팅 구간 키 스윕 ON (#25334/#25278 재현) / 0=OFF
BOOT_KEYS="KEYCODE_MENU"   # 스윕에 사용할 키(공백 구분 복수 가능)
BOOT_KEY_INTERVAL=2        # 스윕 주기(초) — adb 복귀 시점부터 홈 표시 전까지 반복 주입

DATA_MODE="alternate"      # alternate(홀수 ON/짝수 OFF) | on | off | skip
DATA_CONNECT_TIMEOUT=45    # DATA ON 시 데이터 연결(state=2) 대기(초)

HOME_PKG_OVERRIDE=""       # 홈 패키지 자동탐지 실패 시 --home 로 지정
# 홈 크래시 귀속 패키지(자동탐지 홈 pkg 가 실행 시 추가됨)
CRASH_PKG_RE='com\.hnlens\.launcher3|com\.hnlens\.simplemode|mive'
# 크래시 팝업 문구(uiautomator 덤프 대조)
POPUP_RE='keeps stopping|has stopped|問題が発生|停止しました|繰り返し停止|계속 중지|중지됨|계속 중단|중단됨|중단됩니다'

############################# [ 내부 상태 ] ####################################
RUN_TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR=""; ART_DIR=""; RESULT_CSV=""; SUMMARY=""
PASS=0; WARN=0; FAIL=0
HOME_PKG=""
ART_COUNT=0; MAX_ARTIFACTS=60   # 무거운 캡처(스샷/dumpsys/logcat) 총량 상한 — 야간 반복실패 디스크 폭주 방지

c(){ [ -n "${NO_COLOR:-}" ] && printf '%s' "$2" || printf '\033[%sm%s\033[0m' "$1" "$2"; }
info(){ echo "$(c 36 "[INFO]") $*"; }
warn(){ echo "$(c 33 "[WARN]") $*"; }
fail(){ echo "$(c 31 "[FAIL]") $*"; }
adbx(){ if [ -n "$SERIAL" ]; then adb -s "$SERIAL" "$@"; else adb "$@"; fi; }
HAVE_TIMEOUT=0; command -v timeout >/dev/null 2>&1 && HAVE_TIMEOUT=1
# 타임아웃 adb: 반쯤 죽은 단말에서 screencap/uiautomator dump 무한대기 방지(무인 야간).
# timeout 미존재 환경은 무타임아웃 폴백(기능 동일).
tadb(){ local s="$1"; shift
  if [ "$HAVE_TIMEOUT" -eq 1 ]; then
    if [ -n "$SERIAL" ]; then timeout "$s" adb -s "$SERIAL" "$@"; else timeout "$s" adb "$@"; fi
  else adbx "$@"; fi
}

usage(){ sed -n '3,32p' "$0"; cat <<EOF
옵션:
  -s, --serial <id>     대상 단말
  -n, --count <n>       반복 횟수 (기본 $COUNT)
  -o, --out <dir>       산출물 루트 (기본 $OUT_ROOT)
  --data-mode <m>       alternate|on|off|skip (기본 $DATA_MODE)
  --boot-keys <list>    부팅 스윕 키 (기본 $BOOT_KEYS)
  --no-bootkeys         부팅 구간 키 스윕 비활성
  --home <pkg>          홈 패키지 수동 지정
  -h                    도움말
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--serial) SERIAL="$2"; shift 2;;
    -n|--count)  COUNT="$2"; shift 2;;
    -o|--out)    OUT_ROOT="$2"; shift 2;;
    --data-mode) DATA_MODE="$2"; shift 2;;
    --boot-keys) BOOT_KEYS="$2"; shift 2;;
    --no-bootkeys) BOOT_KEY_MODE=0; shift;;
    --home)      HOME_PKG_OVERRIDE="$2"; shift 2;;
    -h|--help)   usage; exit 0;;
    *) echo "알 수 없는 옵션: $1"; usage; exit 3;;
  esac
done

# 무인 실행 가드: -n 오타(예 '20O')로 0회 실행 후 exit 0 되는 야간 슬롯 낭비 차단
case "$COUNT" in ''|*[!0-9]*) echo "-n/--count 는 양의 정수여야 함: '$COUNT'"; exit 3;; esac
[ "$COUNT" -lt 1 ] && { echo "-n/--count 는 1 이상이어야 함: '$COUNT'"; exit 3; }

############################# [ 헬퍼 ] #########################################
now_s(){ date +%s; }

get_focus(){   # display-0 의 mCurrentFocus 값
  adbx shell dumpsys window 2>/dev/null | tr -d '\r' | awk -v d="$MAIN_DISPLAY" '
    $0 ~ "Display: mDisplayId="d { f=1 }
    f && /mCurrentFocus=/ { print; exit }'
}
get_resumed(){
  adbx shell dumpsys activity activities 2>/dev/null | tr -d '\r' | awk -v d="$MAIN_DISPLAY" '
    $0 ~ "Display #"d { f=1; next }
    /^Display #[0-9]+/ { f=0 }
    f && /(topResumedActivity|ResumedActivity)=/ { print; exit }'
}
focus_is_none(){   # 메인 블록 식별 실패(단일 디스플레이 구형 등) 시: 비-null 포커스가 하나라도 있으면 정상 폴백
  local f; f="$(get_focus)"
  if [ -z "$f" ]; then
    adbx shell dumpsys window 2>/dev/null | grep -E 'mCurrentFocus=' | grep -qv '=null' && return 1
    f="null"
  fi
  printf '%s' "$f" | grep -q '=null'
}
home_foreground(){ [ -n "$HOME_PKG" ] && get_resumed | grep -q "$HOME_PKG"; }

detect_home(){
  if [ -n "$HOME_PKG_OVERRIDE" ]; then HOME_PKG="$HOME_PKG_OVERRIDE"; return; fi
  HOME_PKG="$(adbx shell cmd package resolve-activity --brief \
      -a android.intent.action.MAIN -c android.intent.category.HOME 2>/dev/null \
      | grep -oE '^[A-Za-z0-9_.]+/' | head -1 | tr -d '/\r')"
}

wait_adb(){  # reboot 후 adb 복귀. 성공 0
  local t0; t0=$(now_s)
  while :; do
    [ "$(adbx get-state 2>/dev/null | tr -d '\r')" = "device" ] && return 0
    [ $(( $(now_s) - t0 )) -ge "$ADB_TIMEOUT" ] && return 1
    sleep 1
  done
}
boot_completed(){ [ "$(adbx shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; }

data_set(){  # $1 = on|off
  case "$1" in
    on)  adbx shell svc data enable  >/dev/null 2>&1;;
    off) adbx shell svc data disable >/dev/null 2>&1;;
  esac
  sleep 1
}
data_setting(){ adbx shell settings get global mobile_data 2>/dev/null | tr -d '\r'; }
# 듀얼SIM 폴드 대응: head -1(=Phone0, DDS 아닐 수 있음) 대신 '어느 모뎀이든 연결(state=2)' 판정.
# on=하나라도 연결이면 OK / off=하나라도 연결이면 위반 — 로 의미 명확화.
data_any_connected(){
  adbx shell dumpsys telephony.registry 2>/dev/null | tr -d '\r' \
    | grep -oE 'mDataConnectionState=[0-9-]+' | grep -q '=2'
}

crash_scan(){  # 이번 부팅 이후(버퍼=부팅 후 전체) 홈 계열 crash/ANR. 발견 시 사유 echo
  local crash events
  crash="$(adbx logcat -d -b crash 2>/dev/null | tr -d '\r')"
  if printf '%s' "$crash" | grep -E "Process: ($CRASH_PKG_RE)" >/dev/null 2>&1; then
    echo "home_crash(FATAL, $(printf '%s' "$crash" | grep -oE "Process: [a-z0-9._]+" | head -1))"; return 0
  fi
  events="$(adbx logcat -d -b events 2>/dev/null | tr -d '\r' | grep am_crash | grep -E "$CRASH_PKG_RE")"
  [ -n "$events" ] && { echo "home_crash(am_crash)"; return 0; }
  adbx logcat -d 2>/dev/null | tr -d '\r' | grep -E "ANR in ($CRASH_PKG_RE)" >/dev/null 2>&1 \
    && { echo "home_anr"; return 0; }
  return 1
}
popup_scan(){  # 크래시 팝업 문구 화면 노출 여부 (uiautomator dump 는 wedge 시 무한대기 가능 → 타임아웃)
  tadb 20 shell 'rm -f /sdcard/uidump.xml 2>/dev/null; uiautomator dump /sdcard/uidump.xml >/dev/null 2>&1; cat /sdcard/uidump.xml 2>/dev/null' \
    2>/dev/null | grep -qE "$POPUP_RE"
}

record_failure(){  # $1=회차 $2=level $3=reason
  local d="$ART_DIR/${2}_reboot_$(printf '%04d' "$1")_$(date +%H%M%S)"
  mkdir -p "$d"
  local reason_csv="${3//,/;}"   # reason 내 쉼표가 5컬럼 CSV 를 밀어내지 않도록 치환
  ART_COUNT=$((ART_COUNT+1))
  if [ "$ART_COUNT" -le "$MAX_ARTIFACTS" ]; then
    tadb 30 exec-out screencap -p        > "$d/screen.png"      2>/dev/null
    adbx shell dumpsys window            > "$d/window.txt"      2>/dev/null
    adbx shell dumpsys activity activities > "$d/activities.txt" 2>/dev/null
    adbx logcat -d -v threadtime -t 5000 > "$d/logcat_main.txt" 2>/dev/null
    adbx logcat -d -b crash              > "$d/logcat_crash.txt" 2>/dev/null
  else
    echo "(무거운 캡처 생략: 아티팩트 상한 ${MAX_ARTIFACTS} 초과 — context/CSV 만 기록)" > "$d/NOTE.txt"
  fi
  {
    echo "scenario  : reboot_cycle"
    echo "iteration : #$1 / $COUNT"
    echo "level     : $2"
    echo "reason    : $3"
    echo "data_mode : $DATA_MODE (this iter: ${CUR_DATA:-skip})"
    echo "boot_keys : $([ "$BOOT_KEY_MODE" -eq 1 ] && echo "$BOOT_KEYS @${BOOT_KEY_INTERVAL}s" || echo off)"
    echo "time      : $(date '+%Y-%m-%d %H:%M:%S')"
    echo "serial    : ${SERIAL:-auto}"
    echo "model     : $(adbx shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
    echo "build     : $(adbx shell getprop ro.build.display.id 2>/dev/null | tr -d '\r')"
  } > "$d/context.txt" 2>/dev/null
  echo "reboot_cycle,$1,$2,$reason_csv,$d" >> "$RESULT_CSV"
  echo "$d"
}

############################# [ 준비 ] #########################################
mkdir -p "$OUT_ROOT" || { echo "산출물 폴더 생성 실패: $OUT_ROOT"; exit 3; }
RUN_DIR="$OUT_ROOT/run_$RUN_TS"; ART_DIR="$RUN_DIR/artifacts"
mkdir -p "$ART_DIR"
RESULT_CSV="$RUN_DIR/results.csv"; SUMMARY="$RUN_DIR/summary.txt"
echo "scenario,index,level,reason,artifact_dir" > "$RESULT_CSV"
# 콘솔 전체(회차 타이밍 프로파일 포함)를 파일에도 남긴다 — 무인 야간 창닫힘/호스트 재부팅 대비(참조 하니스 규약)
# -i: Ctrl-C 시 tee 가 SIGINT 로 죽어 trap summary 가 broken pipe 로 유실되는 것 방지
exec > >(tee -ai "$RUN_DIR/console.log") 2>&1

if ! adbx get-state >/dev/null 2>&1; then echo "adb 단말 연결 확인 실패"; exit 3; fi
detect_home
# 홈 자동탐지 실패 시 전 회차 false-FAIL(home_not_foreground) 되므로 무인 진입 전 하드스톱
[ -z "$HOME_PKG" ] && { fail "홈 패키지 자동탐지 실패 — --home <pkg> 지정 후 재실행(무인 야간 전 회차 오탐 방지)"; exit 3; }
[ -n "$HOME_PKG" ] && ! printf '%s' "$CRASH_PKG_RE" | grep -q "$HOME_PKG" \
  && CRASH_PKG_RE="$CRASH_PKG_RE|$(printf '%s' "$HOME_PKG" | sed 's/\./\\./g')"

info "홈 패키지: ${HOME_PKG:-?} / 데이터 모드: $DATA_MODE / 부팅 키 스윕: $([ "$BOOT_KEY_MODE" -eq 1 ] && echo "$BOOT_KEYS" || echo OFF)"
info "산출물: $RUN_DIR (회차당 약 60~90초)"
[ "$BOOT_KEY_MODE" -eq 1 ] && warn "부팅 키='$BOOT_KEYS'. 물리 메뉴키가 표준 KEYCODE_MENU 가 아닐 수 있음 — 'adb shell getevent -lt' 로 실제 keycode 확인 후 --boot-keys 지정 권장(#25334/#25278)."

# Ctrl-C 시에도 데이터 ON 복원(다음 테스트에 데이터 OFF 방치 방지). data_set/DATA_MODE 는 위에서 정의됨
trap 'echo; [ "$DATA_MODE" != "skip" ] && data_set on; print_summary; exit $EXITC' INT

print_summary(){
  EXITC=0; [ "$WARN" -gt 0 ] && EXITC=2; [ "$FAIL" -gt 0 ] && EXITC=1
  {
    echo "=== reboot_cycle 결과 ($(date '+%Y-%m-%d %H:%M:%S')) ==="
    echo "PASS=$PASS WARN=$WARN FAIL=$FAIL / 총 $((PASS+WARN+FAIL))회 (요청 $COUNT)"
    echo "results: $RESULT_CSV"
    echo "artifacts: $ART_DIR/"
    if [ "$FAIL" -gt 0 ]; then echo "[판정] 하드 FAIL 존재 — artifacts 분석 필요"
    elif [ "$WARN" -gt 0 ]; then echo "[판정] WARN 수동검토 필요(slow_home/데이터 연결 지연 등)"
    else echo "[판정] 전 회차 PASS"
    fi
  } | tee "$SUMMARY"
}

############################# [ 메인 루프 ] ####################################
for (( i=1; i<=COUNT; i++ )); do
  # 회차 데이터 목표 상태
  case "$DATA_MODE" in
    alternate) [ $(( i % 2 )) -eq 1 ] && CUR_DATA="on" || CUR_DATA="off";;
    on)  CUR_DATA="on";;
    off) CUR_DATA="off";;
    *)   CUR_DATA="";;
  esac
  [ -n "$CUR_DATA" ] && data_set "$CUR_DATA"

  t0=$(now_s)
  adbx reboot >/dev/null 2>&1
  # 실제 다운을 먼저 확정한다: adbd 트랜스포트가 빠질 때까지 대기.
  # 이 단계가 없으면 셧다운 지연 시 이전 부팅의 sys.boot_completed=1 을 읽어
  # '헛부팅'을 PASS 로 채점하고 #25334/#25278 키 스윕도 통째 skip 된다.
  down=0; dw0=$(now_s)
  while [ $(( $(now_s) - dw0 )) -lt "$ADB_TIMEOUT" ]; do
    [ "$(adbx get-state 2>/dev/null | tr -d '\r')" != "device" ] && { down=1; break; }
    sleep 0.3
  done
  if [ "$down" -eq 0 ]; then
    d=$(record_failure "$i" FAIL "reboot_not_detected(${ADB_TIMEOUT}s adbd 미분리)"); fail "[#$i] 재부팅 미감지 → $d"
    FAIL=$((FAIL+1)); continue
  fi

  if ! wait_adb; then
    d=$(record_failure "$i" FAIL "adb_timeout(${ADB_TIMEOUT}s)"); fail "[#$i] adb 미복귀 → $d"
    FAIL=$((FAIL+1)); continue
  fi
  t_adb=$(( $(now_s) - t0 ))

  # 부팅 구간 키 스윕(#25334/#25278): boot_completed 까지 + 홈 표시 직전까지 주기 주입
  injected=0
  while ! boot_completed; do
    if [ $(( $(now_s) - t0 )) -ge "$BOOT_TIMEOUT" ]; then
      d=$(record_failure "$i" FAIL "boot_timeout(${BOOT_TIMEOUT}s)"); fail "[#$i] 부팅 미완료 → $d"
      FAIL=$((FAIL+1)); continue 2
    fi
    if [ "$BOOT_KEY_MODE" -eq 1 ]; then
      for k in $BOOT_KEYS; do adbx shell input keyevent "$k" >/dev/null 2>&1; done
      injected=$((injected+1))
    fi
    sleep "$BOOT_KEY_INTERVAL"
  done
  t_boot=$(( $(now_s) - t0 ))

  # 홈 전면 대기(+ 초기 구간 추가 키 주입: 홈 뜨는 순간이 취약창)
  # t_home     = reboot 발령→홈(누적, 프로파일 출력용)
  # t_home_rel = boot_completed→홈(홈 지연, slow_home 판정용). 누적을 임계 비교하면
  #              부팅시간(60~90s) 때문에 정상 회차가 전부 slow_home 오탐된다.
  t_home=-1; t_home_rel=-1
  hw0=$(now_s)
  while [ $(( $(now_s) - hw0 )) -lt "$HOME_WAIT" ]; do
    if [ "$BOOT_KEY_MODE" -eq 1 ] && [ $(( ($(now_s) - hw0) % 3 )) -eq 0 ]; then
      for k in $BOOT_KEYS; do adbx shell input keyevent "$k" >/dev/null 2>&1; done
    fi
    if home_foreground; then t_home=$(( $(now_s) - t0 )); t_home_rel=$(( $(now_s) - hw0 )); break; fi
    sleep 1
  done
  info "[#$i/$COUNT 프로파일] adb복귀 ${t_adb}s / boot ${t_boot}s / 홈 $( [ $t_home -ge 0 ] && echo ${t_home}s || echo 미표시) / 키주입 ${injected}회 / data=${CUR_DATA:-skip}"

  reason=""; level="PASS"
  if r=$(crash_scan); then level="FAIL"; reason="$r"
  elif popup_scan; then level="FAIL"; reason="crash_popup(화면 노출)"
  elif [ $t_home -lt 0 ]; then level="FAIL"; reason="home_not_foreground(${HOME_WAIT}s)"
  elif focus_is_none; then sleep 0.5; focus_is_none && { level="FAIL"; reason="no_focus(지속)"; }
  fi

  # 데이터 유지/동작 판정 (crash 계열 FAIL 이 이미 있으면 그쪽 우선)
  if [ "$level" = "PASS" ] && [ -n "$CUR_DATA" ]; then
    st="$(data_setting)"
    want=$([ "$CUR_DATA" = "on" ] && echo 1 || echo 0)
    if [ "$st" != "$want" ]; then
      level="FAIL"; reason="data_state_mismatch(설정=$st, 기대=$want)"
    elif [ "$CUR_DATA" = "on" ]; then
      dc0=$(now_s); ok=0
      while [ $(( $(now_s) - dc0 )) -lt "$DATA_CONNECT_TIMEOUT" ]; do
        data_any_connected && { ok=1; break; }; sleep 2
      done
      [ "$ok" -eq 0 ] && { level="WARN"; reason="data_no_connect(${DATA_CONNECT_TIMEOUT}s, 현장 망 요인 가능)"; }
    else
      data_any_connected && { level="FAIL"; reason="data_connected_while_off"; }
    fi
  fi
  # slow_home 은 '부팅 완료 후 홈까지'(t_home_rel)로 판정 — 누적(t_home)은 항상 임계 초과라 오탐
  if [ "$level" = "PASS" ] && [ "$t_home_rel" -ge 0 ] && [ "$t_home_rel" -ge "$SLOW_HOME_SEC" ]; then
    level="WARN"; reason="slow_home(부팅완료후 ${t_home_rel}s)"
  fi

  case "$level" in
    PASS) PASS=$((PASS+1));;
    WARN) d=$(record_failure "$i" WARN "$reason"); warn "[#$i] $reason → $d"; WARN=$((WARN+1));;
    FAIL) d=$(record_failure "$i" FAIL "$reason"); fail "[#$i] $reason → $d"; FAIL=$((FAIL+1));;
  esac
done

# 종료 시 데이터 ON 복원(다음 테스트 대비)
[ "$DATA_MODE" != "skip" ] && data_set on
print_summary
exit $EXITC
