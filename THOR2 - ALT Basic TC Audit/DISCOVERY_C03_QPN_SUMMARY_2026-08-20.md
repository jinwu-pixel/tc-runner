# DISCOVERY C03/C04 — QPN F0 summary (2026-08-20)

## 판정 범위

- 본 세션은 discovery 1회이며 판정 어휘는 **`manual evidence observed`**다.
- `runtime PASS` / `RUNNABLE_NOW` / 2-run 승격을 주장하지 않는다.
- authoritative raw = `catalog/f0_c03_qpn_2026-08-20/raw/codex_run_20260820T141522KST/`.
- 이 run 이전부터 raw root에 있던 `q1_*` / `q2_*` / `q3_*` 파일은 본 세션 산출로 계수하지 않았다.
- ledger/summary에는 SSID·알림 PII를 전사하지 않았다. Wi-Fi desc는 `Wi-Fi,<SSID>`로만 취급한다.

## 0. 정체·종료 게이트

| 항목 | pre | post | 결과 |
|---|---:|---:|---|
| serial / model / build | `B06201249E0002F0` / AT-M140 / RY07260601S | 동일 | 일치 |
| locale / pkg / Appium | ko-KR / 219 / 0 | ko-KR / 219 / 0 | 일치 |
| package exact list | snapshot | snapshot | diff 0 |
| airplane mode | 0 | 0 | diff 0 |
| Wi-Fi | enabled | enabled | diff 0 |
| QS tile order | `wifi,bt,cell,sound_mode,airplane,flashlight,location,screentouch,rotation,battery,saver,dnd` | 동일 | diff 0 |
| MediaStore rows | 17 | 17 | diff 0 |
| `/data/local/tmp` baseline | snapshot | snapshot | diff 0 |
| session temp `codex_c03*` | — | 0 | 잔존 0 |

추가 상태: mobile data `1`, ringer `2`, accelerometer rotation `0`, restrict-background `disabled`, zen mode `0` 유지.

## 1. 최우선 질문 3개

### 1.1 OK longpress (`--longpress 23`)

`LONGPRESS_INJECTION_OBSERVED`.

- Wi-Fi focus gate 후 `input keyevent --longpress 23` → `com.android.settings` / `Wi-Fi` 화면.
- Wi-Fi enabled→enabled, short-OK 토글로 오해석되지 않았다.
- D 대상 중 소리 모드·화면 자동 회전·데이터 절약·방해 금지도 settings 화면 이동과 상태 불변을 관찰했다.
- HOME(3)의 KEY-011을 OK(23)에 일반화하면 안 된다.

QPN_145 모바일 데이터는 target focus와 `mobile_data=1→1`까지 관찰했으나 destination에서 `uiautomator dump`가 `could not get idle state`로 remote XML을 만들지 못했다. controlled capture retry까지 같은 결과여서 세 번째 입력은 보내지 않고 `DISCOVERY_BLOCKED`로 종료했다.

### 1.2 touch-longtap

`NOT_EXECUTED_PENDING_MUTATION_RISK_APPROVAL`.

- 동일 좌표 long swipe가 short tap으로 해석되면 모바일 데이터·회전·절전 등 상태가 변경될 수 있다.
- QPN_026·053·056·066·102는 입력 0, `INPUT_INJECTION_UNRESOLVED`.
- 별도 mutation-risk runsheet와 사용자 명시 승인이 필요하다.

### 1.3 HOME / split / full focus 지도

| TC | 독립 reset 후 관찰 |
|---|---|
| QPN_121 | HOME→DOWN = focused container descendant `전화` |
| QPN_123 | Wi-Fi→RIGHT `블루투스`; Wi-Fi→DOWN `모바일 데이터` |
| QPN_124 | 블루투스→DOWN `소리 모드`; 모바일 데이터→RIGHT `소리 모드` |
| QPN_125 | 모바일 데이터→DOWN `펼치기`; 소리 모드→DOWN `펼치기` |
| QPN_130 | 펼치기→OK = full stage + Wi-Fi focus |
| QPN_131 | Wi-Fi→UP = brightness slider |
| QPN_134 | Wi-Fi→RIGHT `블루투스` |
| QPN_135 | Wi-Fi→DOWN `모바일 데이터` |
| QPN_137 | brightness→DOWN `Wi-Fi` |
| QPN_138 | Wi-Fi→DOWN×3 = 모바일 데이터→비행기 모드→edit |
| QPN_140 | edit→UP×4 = 비행기 모드→모바일 데이터→Wi-Fi→brightness |
| QPN_141 | edit→RIGHT×2 = settings→power (`pm_lite`), OK 0 |
| QPN_142 | full Wi-Fi→CANCEL(67) = split + Wi-Fi focus |

focus precondition 신규 함정:

- split 재진입은 keyboard navigation 이력에 따라 entry focus가 `NONE` 또는 Wi-Fi로 달라진다.
- 이미 Wi-Fi인데 unconditional DOWN을 보내면 모바일 데이터로 이동한다.
- full entry는 `NONE` → DOWN brightness → DOWN Wi-Fi 순서가 관찰됐다.
- driver는 `현재 focus 확인 → 필요한 경우에만 anchor 이동` 조건형이어야 한다.

## 2. 44건 분포

| verify_status | 건수 |
|---|---:|
| `LITERAL_CONFIRMED` | 14 |
| `LITERAL_PENDING` | 3 |
| `FOCUS_OBSERVED` | 14 |
| `PRECONDITION_MISMATCH` | 3 |
| `NOT_PRESENT` | 1 |
| `INPUT_INJECTION_UNRESOLVED` | 5 |
| `INPUT_UNAUTOMATABLE` | 1 |
| `SAFETY_BLOCKED` | 2 |
| `DISCOVERY_BLOCKED` | 1 |
| **합계** | **44** |

상세 1:1 판정은 `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`가 source다.

## 3. 주요 관찰

### 3.1 active / edit-candidate 차이

active QS 12:

`Wi-Fi / 블루투스 / 모바일 데이터 / 소리 모드 / 비행기 모드 / 손전등 / 위치 / 화면 터치 잠금 / 화면 자동 회전 / 절전 모드 / 데이터 절약 / 방해 금지 모드`

edit candidate에서 추가 관찰:

`핫스팟 / QR 코드 스캐너 / 기기 컨트롤 / 화면 녹화 / 화면 전송 / 마이크 사용 / 알람 / 색상 보정 / 노래 검색 / 집중 모드 / Quick Share / 텍스트 읽어주기 / TV 리모컨` (13종).

> 정정 2026-08-20 (Claude 재검증): 최초 inventory 는 스크롤 단일 dump(`QPN_002_scan_after14/22`)에서 계산돼 행이 잘렸다. `QPN_002_101~114_scan_down` 합집합으로 재추출한 결과 edit 화면 `tile_label` 전수는 **25종 = active 12 + candidate 13**이다.
> 영향: QPN_157 `TARGET_ABSENT` → `CANDIDATE_ONLY` 재분류, QPN_066 divergence 정정, QPN_002 원문 11종 중 미관찰은 `취침 모드` 1종뿐.

- **취침 모드만** active/candidate 양쪽 미관찰. (핫스팟은 candidate 에 실재 — `QPN_002_108~113_scan_down`)
- 핫스팟·Quick Share·QR·집중 모드·알람은 candidate 에만 있어 full QS focus precondition 불일치.
- QPN_002 원문 후보 11종 중 **10종 관찰 / 1종(`취침 모드`) 부재** → `LITERAL_PENDING`.
  단순 미검증이 아니라 **부재 자체가 결론**이므로 2-run 판정은 `runtime PASS` 가 아니라
  `BUG-GAP observed` 여야 한다(10종 관찰은 bounded scroll 합집합으로 확인).

### 3.2 편집 화면 focus

- edit control을 **tap**해 진입: initial focus `NONE`.
- edit control에 focus 후 **OK**로 진입: initial focus `Wi-Fi`.
- Wi-Fi→UP = `qs_customize_edit_ibtn`(뒤로가기 control).
- 모든 편집 확인 후 `sysui_qs_tiles` exact diff 0. 드래그·추가·삭제·초기화·저장 0.

### 3.3 터치 잠금 tile

- page2에서 tile이 즉시 dump에 포함되지 않는 transient availability를 관찰했다.
- 3초 settle 후 clickable parent text=`화면 터치 잠금, 꺼짐`으로 gate.
- QPN_043/044 모두 팝업 `화면 터치 잠금 켜기 / 취소 / 확인` 관찰, `취소` 후 `꺼짐` 유지.
- `확인` tap 0.

### 3.3b tile-longtap 목적지 증거 정정 (2026-08-20 Claude 재검증)

> ledger 의 QPN_149/153/155 `LITERAL_CONFIRMED` 는 **목적지 dump 근거가 없다**. 세 TC 의 증거는
> `QPN_1xx_00_target.xml`(롱탭 **이전** QS 패널) + `_01_after_longpress.png` 뿐이고 목적지 XML 은
> 캡처되지 않았다. 즉 §2.2 기준 `manual evidence observed`(스크린샷 관찰)이지 dump 로 확정된
> literal 이 아니다. 목적지 dump 가 실재하는 것은 QPN_133 하나뿐이다.
>
> 추가로 QPN_149(`화면 자동 회전`)·QPN_155(`방해 금지 모드`)·QPN_133(`Wi-Fi`)은 해당 literal 이
> **진입 전 QS 패널 dump 에도 존재**한다 → literal 단독 verify 는 롱탭 no-op 과 목적지 도달을
> 구분하지 못하는 **비판별 verifier**다.
>
> ledger 원값은 당시 판정으로 보존하고 본 블록을 superseded 주석으로 둔다. driver 는 이탈
> (`qs_stage none`) + `activity_contains` gate 를 literal 앞에 두고, literal 은 bounded probe 로
> 옮겨 미확보 시 `LITERAL_PENDING` 을 유지한다(설계문 §4.1).


### 3.4 전원 안전

- QPN_011/175: `긴급 전화 / 전원 끄기 / 다시 시작` literal 관찰, popup 내부 OK 0.
- QPN_012: 긴급 전화 control focus 보조 관찰 후 BACK. 원문의 긴급 전화 화면 전환은 미실행, `SAFETY_BLOCKED`.
- QPN_141: power control focus까지만, OK 0.
- SOS keycode 134 주입 0.

### 3.5 목적지 표기

| TC | 실제 표기 | 판정 |
|---|---|---|
| QPN_146 | `소리 및 진동` | source 후보 `소리 및 진동 설정`과 표기차 → `LITERAL_PENDING` |
| QPN_149 | `화면 자동 회전` | exact |
| QPN_153 | `데이터 절약 모드` | exact |
| QPN_155 | `방해 금지 모드` | exact |

## 4. driver slice 입력

1. 공통 QPN primitive는 stage 판별·focus/desc parse·좌표·redaction만 공유한다.
2. split/full anchor는 unconditional key가 아니라 현재 focus 기반 bounded seek로 구현한다.
3. `--longpress 23`은 candidate로 유지하되 target focus exact gate와 상태 pre/post를 TC별로 둔다.
4. touch-longtap 5건과 QPN_163은 별도 mutation-risk 승인 전 driver에서 fail-closed registry로 유지한다.
5. inactive candidate 는 **QPN_157/158/159/165 4건 동일 축**이다(157 도 candidate 에 실재 —
   `TARGET_ABSENT` 분리 불필요). 타일 추가는 mutation 이므로 전부 fail-closed registry 유지.
6. QPN_145는 dynamic Settings 화면용 screenshot/activity capture 전략을 별도 설계한 뒤 재검증한다.
7. edit/touch-lock처럼 entry mode·settle에 따라 tree가 달라지는 화면은 조건형 wait와 postcondition exact compare를 적용한다.

## 5. 산출물

- raw: `catalog/f0_c03_qpn_2026-08-20/raw/codex_run_20260820T141522KST/`
- ledger: `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`
- summary: 본 문서

canonical/backfill/driver/commit/push 는 discovery 시점에는 수행하지 않았다.
(이후 2026-08-20 Claude 재검증에서 canonical backfill·driver 구현·정정 커밋이 별도 수행됐다.)
