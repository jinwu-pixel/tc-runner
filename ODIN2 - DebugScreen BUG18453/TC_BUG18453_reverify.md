# TC — BUG-18453 DebugScreen internet/tethering/DUN IP 재검증 (정식 빌드용)

> 본 TC는 모뎀/DebugScreen 검증으로 tc-runner YAML compile 파이프라인(validate_tc.py/gen_excel.py) 대상이 아님.
> BUG-17126 선례와 동일하게 절차 문서 + 증거 누적 방식으로 운용.
> Test 빌드(Z0518U)에서 발견된 갭이 정식 빌드에 반영되면 본 TC로 재검증한다.

## 대상 / 트리거

- BUG-18453, 출처 bug-view-18453, 원본 PDF `doc/[ODIN2][LTE][DEBUG] internet IPTethering IPOTAEmergency IP.pdf`
- 재검증 트리거: T3 fix(또는 스펙 확정)가 **정식 빌드**에 반영되었을 때
- 단말: AT-M150 (ZEM 포켓몬3, ODIN2) / SIM: **LGU+ 필수**(tethering.lguplus.co.kr DUN APN 필요. SKT/KT는 별도 DUN PDN 없어 재현 불가)

## 선행 조건 (반드시)

1. 빌드/SIM 확인: `getprop ro.build.display_build_number_internal`, `getprop gsm.operator.alpha`(=LG U+)
2. **mobile data ON** — 콜드부팅 직후 `settings get global mobile_data`=0 가능. 0이면 `svc data enable` 후 internet PDN(10.x) 올라올 때까지 대기(최대 ~2분). 데이터 OFF 상태 IP 미표시는 정상이므로 판정 금지
3. 화면 잠금해제: `input keyevent KEYCODE_WAKEUP` + `wm dismiss-keyguard`
4. **2단말 동시 연결 주의**: AT-M150(odin2)+AT-M140(thor2) 동시 시 bare adb 실패 → 항상 `adb -s <serial>`(예 <device_serial>)
5. DebugScreen 진입: `adb -s S shell am start -n com.android.phone/.settings.DebugScreen`
   - 값 갱신 위해 재확인 시 **재진입**(force-stop com.android.phone 후 재실행 권장). 화면 자동 새로고침 없음
6. Windows: `/sdcard/...` 경로가 Git Bash에서 변환 깨짐 → **PowerShell 도구로 adb 실행** 또는 MSYS_NO_PATHCONV=1

## Ground-truth 모니터 (재사용, grep -P 금지)

```
S=<device_serial>; prev=""; reach="init"; echo "$(date +%H:%M:%S) MON ARMED"; while true; do td=$(adb -s $S shell dumpsys tethering 2>/dev/null); if [ -z "$td" ]; then if [ "$reach" != "down" ]; then echo "$(date +%H:%M:%S) OFFLINE"; reach="down"; fi; sleep 5; continue; fi; if [ "$reach" != "up" ]; then echo "$(date +%H:%M:%S) ONLINE"; reach="up"; prev=""; fi; up=$(echo "$td" | grep -m1 'Current upstream:' | tr -d '\r' | sed 's/.*Current upstream:[[:space:]]*//'); [ -z "$up" ] && up="null"; ti=$(echo "$td" | grep -oE '(rndis[0-9]|wlan[0-9]|usb[0-9]|softap[0-9]) - TetheredState' | sed 's/ - TetheredState//' | tr '\n' ','); [ -z "$ti" ] && ti="none"; dun="none"; case "$up" in rmnet_data[0-9]*) ip=$(adb -s $S shell ifconfig "$up" 2>/dev/null | grep -oE 'inet addr:[0-9.]+' | head -1 | sed 's/inet addr://'); [ -n "$ip" ] && dun="CONNECTED ip=$ip ($up)" || dun="up=$up";; esac; sig="DUN=[$dun]|up=[$up]|teth=[$ti]"; if [ "$sig" != "$prev" ]; then echo "$(date +%H:%M:%S) | $sig"; prev="$sig"; fi; sleep 5; done
```

- DUN 판정 = tethering `Current upstream` 의 rmnet iface + 그 iface ifconfig IP. `grep -P` 사용 금지(로케일 오류로 오탐).

## 테스트 항목 / PASS·FAIL 기준

DebugScreen 필드: `IP:` `IMS IP:` `DUN IP:`. 화면값을 매 단계 ground-truth와 대조.

### T1 — bootup internet/IMS IP
- 절차: 재부팅 → boot_completed → (mobile data ON 보장) → 데이터 등록 대기 → DebugScreen
- PASS: `IP:`=internet PDN IPv4, `IMS IP:`=IMS PDN IP 표시, ground-truth(dumpsys precise data states) 일치
- FAIL: 데이터 정상인데 IP/IMS IP 누락

### T2 — tethering IP 표시 (WIFI + USB 각각)
- 절차: 모바일 핫스팟 ON / USB 테더링 ON (각각) → DebugScreen
- ground-truth: 모니터에 `DUN=CONNECTED ip=X (rmnet_dataN)` 표시될 때의 X
- PASS: 화면 tethering IP == ground-truth X
- FAIL: tethering 활성·DUN PDN CONNECTED인데 화면 미표시 (원본 버그 증상)

### T3 — "DUN" 문구 ★스펙 확인 선행★
- ※ 지시 #2(tethering IP 표시)와 #3("DUN" 문구 미표시)는 양립하려면 "tethering IP를 일반 `IP:` 필드 표시 + `DUN IP:` 라벨 제거" 설계여야 함. **최종 설계 의도를 보고자(Sh hwang)/개발(YanLijie)에게 먼저 확인**하고 아래 기준 택1:
  - (A) 최종 스펙 = DUN 라벨 제거: **PASS = DebugScreen 어디에도 "DUN" 문자열 없음**(uiautomator dump 전체에서 `DUN` 0건), tethering IP는 `IP:` 필드에 표시
  - (B) 최종 스펙 = DUN IP 필드 유지: T3 비적용, T2 기준으로만 판정
- Test 빌드 Z0518U 현황(참고): "DUN IP:" 라벨 상시 노출(dump 내 DUN 1건) = (A) 기준이면 FAIL

### T4 — tethering 해제 시 tethering IP 미표시 ★시간축 측정 필수★
- 절차: tethering OFF 시각 t0 기록 → DebugScreen **재진입**하며 t0 기준 **0s / 30s / 60s / 90s / 120s** 시점 `DUN IP:` 값 캡처 (WIFI·USB 각각)
- 단일 시점만 보지 말 것 — clear 가 지연될 수 있음(Test 빌드에서 WIFI는 ~<45s 잔존 후 ~2분내 clear, USB는 ~18s 즉시 clear 관측)
- PASS: 스펙상 허용 지연 이내(미정 시 기본 ≤60s 권장, 보고자 합의)에 `DUN IP:` 빈 값. ground-truth(upstream=null)와 최종 일치
- FAIL: 허용 지연 초과 잔존, 또는 영구 stale
- 기록: `T4-[WIFI|USB] t0=__ : 0s=__ 30s=__ 60s=__ 90s=__ 120s=__ / 판정`

## 교차 검증 규칙 (Test 빌드 교훈)

- tethering ON/OFF 는 **WIFI(핫스팟) + USB(테더링) 양쪽**, 가능하면 단말 UI 토글로 수행(root `cmd wifi`는 shell 권한 차단 → `su 0` 우회 가능하나 UI 경로 우선)
- "미표시/clear" 항목은 **한 시점 단정 금지**, 시간축으로 측정
- 한 경로(WIFI만/USB만) 결과로 BUG/PASS 단정 금지 — Test 빌드에서 WIFI/USB clear 동작 비대칭 발견됨

## 알려진 함정

- grep -P 로케일 오류 → ground-truth 오탐(모니터는 위 -P-free 버전 사용)
- Git Bash `/sdcard` 경로 변환 → PowerShell로 adb 실행
- 2단말 동시 → `adb -s` 필수
- USB 테더링 토글 시 adb-over-USB 일시 단절(정상). 필요시 `adb tcpip 5555` 백업(단 RNDIS 서브넷 가변 192.168.4x.x — PC 어댑터 IP 확인)
- 콜드부팅 직후 mobile_data=0 가능 → T1 전 데이터 ON 보장

## 증거 누적 위치

`ODIN2 - DebugScreen BUG18453/evidence/` — `<seq>_<항목>_<상태>.{xml,png}` + RESULT_<date>.md 갱신
