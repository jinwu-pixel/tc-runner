# RUNSHEET — C03/C04 (14.Quick panel) F0 v1 discovery run (Codex 실행용, 2026-08-20)

**역할**: Codex = 단말 실행·채록 / Claude = 계획·검증 / 사용자 = 승인 게이트.

**본 세션 = discovery run. 2-run 아님 — `runtime PASS`·`RUNNABLE_NOW` 승격 주장 금지.**
목적 = QPN 44건의 ① 진입/focus 경로 확정 ② **입력 주입 가능 여부의 선행 게이트 판별**(§3 = 최우선) ③ 실측 literal/desc 채록 ④ driver-pattern 분류 입력 확보.
§3 결과는 공통 입력 primitive의 가능성만 가른다. 개별 TC의 focus 도달·목적지·literal 검증 전에는 44건 전체 자동화 가능을 주장하지 않는다.

- 상위 계약: `handoff_device_validation/THOR2J_HANDOFF_BATCH10_2026-06-25.md` (§6 elevated-caution·§7 denylist 유효)
- manifest (read-only): `VALIDATION_MANIFEST_BATCH10_2026-06-25.csv` — `source_sheet=14.Quick panel` **44행**
- canonical yaml (read-only): `stage1_review_mapping_batch10/ALTBASIC_QPN_*.yaml` — **편집 금지**(backfill 은 Claude 검증 후 별도)
- **선행 자산 필독**: `RESULT_RECOVERY_BATCH10_C02_2026-08-19.md` §6~7 · `catalog/f0_literal_catalog.csv` `KEY-011`·`STR-012~014`

## 0. 단말 정체 게이트 (하나라도 불일치 = 즉시 STOP)

```bash
adb devices -l                                                   # F0 단독
adb -s B06201249E0002F0 shell getprop ro.product.model            # AT-M140
adb -s B06201249E0002F0 shell getprop ro.build.version.incremental # RY07260601S
adb -s B06201249E0002F0 shell getprop persist.sys.locale          # ko-KR
adb -s B06201249E0002F0 shell "pm list packages | wc -l"          # 219
adb -s B06201249E0002F0 shell pm list packages io.appium          # 출력 없음
```
이후 모든 adb 호출에 `-s B06201249E0002F0` 명시. USB 재연결 시 게이트 전체 재실행.

### 0.1 세션 pre-snapshot (종료 게이트의 비교 기준)

정체 게이트 직후, 어떤 QPN 입력보다 먼저 아래 값을 host scratch에 보존한다. **사후값만 읽고 불변을 주장하지 않는다.**

```bash
adb -s B06201249E0002F0 shell "pm list packages | sort" > <scratch>/F0_pkgs_pre.txt
adb -s B06201249E0002F0 shell "settings get global airplane_mode_on" > <scratch>/F0_airplane_pre.txt
adb -s B06201249E0002F0 shell "dumpsys wifi | grep -m1 'Wi-Fi is'" > <scratch>/F0_wifi_pre.txt
adb -s B06201249E0002F0 shell "settings get secure sysui_qs_tiles" > <scratch>/F0_qs_tiles_pre.txt
adb -s B06201249E0002F0 shell "content query --uri content://media/external/images/media --projection _id | wc -l" > <scratch>/F0_media_pre.txt
```

- `sysui_qs_tiles` 가 `null`/빈값이면 1단·2단 dump에서 타일의 정규화된 identity 순서(`content-desc`의 상태·SSID suffix 제거)를 별도 pre-snapshot으로 만든다.
- `airplane_mode_on` pre 값은 `0`이어야 한다. 다른 값이면 비교만 믿고 진행하지 말고 `PRECONDITION_MISMATCH`로 STOP한다.
- pre-snapshot 실패 또는 값 불명확 = `PRECONDITION_MISMATCH`, 본 세션 STOP. 추정값으로 진행 금지.

## 1. 오늘(2026-08-19~20) 확립된 사실 — 재발견 금지, 그대로 사용

| 항목 | 확정값 |
|---|---|
| 퀵패널 진입 | **`input swipe 240 5 240 600 300`** = 1단(분할). 물리 홈 길게와 도달 상태 등가(STR-013) |
| 전체화면 확장 | **`input swipe 240 300 240 780 300`** = 2단(전체 QS) ≡ `cmd statusbar expand-settings` |
| 단계 판별자 | 2단 = `brightness_slider` 존재 / 1단 = `expandableNotificationRow` 존재 (STR-012) |
| 진입 직후 focus | **부재**. `DPAD DOWN` 1회에 **Wi-Fi 타일** focus(desc `Wi-Fi,<SSID>`) — RIGHT=블루투스 / LEFT=Wi-Fi / UP=`alternate_expand_target` (STR-014) |
| 타일 verifier | 타일은 **text 속성 부재 → content-desc 기반**. Wi-Fi 는 SSID 포함이라 **prefix 매칭**만 |
| **adb `--longpress` ≠ 물리 홀드** | 물리 홈 길게는 퀵패널을 열지만 `--longpress 3` 은 못 연다. `sendevent` 는 권한 거부 (KEY-011) |
| 하드키 | 홈 3 / 뒤로 4 / **취소·지움 67(DEL)** / 연락처 131 / 메시지 132 / 즐겨찾기 133 / 최근앱 187 / 카메라 27 |
| **SOS = 134 (추론)** | **절대 발신 금지** |

**QPN_004 원문이 "상단 스와이프"를 명시**하므로 본 시트에서 swipe 는 계약 위반이 아니라 **원문 지정 입력**이다.

## 2. 대상 44 (전건 `[R1]`, NAVIGATION_ONLY 38 + READ_ONLY 6)

| 클러스터 | tc_id | 성격 |
|---|---|---|
| A 진입·구조 | 001·004·116·122 | 패널 노출/페이지/커튼. **홈 하드키 길게 항목은 C02 HDK_019 와 동일 축** |
| B0 홈 focus | 121 | 홈 화면 방향키/OK 입력 — 퀵패널 격자와 별도 |
| B1 1단 focus nav | 123·124·125·130 | 방향키 focus 이동(Wi-Fi→블루투스→모바일데이터→소리모드→펼치기) |
| C 2단 focus nav | 131·134·135·137·138·140·141·142 | 확장 패널 focus 이동·경계 |
| D **OK 길게**(§3-①) | 133·145·146·149·153·155·157 | 타일 OK 길게 → 설정 페이지 이동 |
| E **Long 탭**(§3-②) | 026·053·056·066·102 | 타일 터치 롱탭 → 설정 이동 |
| F OK 단문 진입 | 158·159·163·165·176 | Quick Share/QR/집중모드/알람/설정 |
| G **편집 모드**(§5 위험) | 002·008·167·168 | 퀵패널 편집 화면 — **타일 배치 변경 = mutation** |
| H 전원 패널 | 011·012·175 | 전원 팝업 / **긴급 전화** / 전원 버튼 OK |
| I 터치 잠금(§5) | 043·044 | 켜기 팝업 노출·취소 |
| J 기타 | 010 | 설정 버튼 → 설정 전환 |

위 표는 **44건 상호배타 partition**이다. 별도 safety overlay = `011·012·141·175`; QPN_141은 C에만 계수하고 H에 중복 계수하지 않는다.

## 3. ★최우선 discovery 질문 3개 (공통 입력 primitive의 후보 범위를 가른다)

먼저 이 3개를 판별하고 결과를 보고할 것. 나머지 채록은 그 다음.

**① `--longpress 23`(OK 길게)이 타일에서 작동하는가** — 클러스터 D 7건의 입력 primitive 선행 게이트.
절차: 1단 진입 → `DPAD DOWN`(Wi-Fi focus) → `input keyevent --longpress 23` → 목적지 activity 확인.
- 작동 = Wi-Fi 설정 페이지 이동 → `LONGPRESS_INJECTION_OBSERVED`. D 7건은 **후보 유지**이며, 각 타일의 focus 도달·목적지·literal은 별도 검증한다.
- 미작동(패널 잔류) = `LONGPRESS_INJECTION_UNRESOLVED`. HOME(3)의 KEY-011을 OK(23)에 일반화하지 않는다.
- adb 실패 + 동일 상태의 **물리 OK 길게 positive control 성공**까지 확인된 경우에만 `INPUT_UNAUTOMATABLE` 제안 가능. 물리 control은 사용자 별도 승인·실기 영역이며 Codex가 대신 판정하지 않는다.
- 실패 시 **연타·대체 발명 금지**. 실패 dump/activity를 보존하고 다음 질문으로 진행한다.
- 확인 후 즉시 BACK 으로 원복

QPN_122는 이미 C02 HDK_019와 동일한 HOME(3) 물리 길게 입력이고 KEY-011의 positive control이 존재하므로, 본 세션에서 재주입하지 않고 `INPUT_UNAUTOMATABLE` 후보로 carry-forward한다.

**② 터치 롱탭 주입을 mutation 없이 판별할 수 있는가** — 클러스터 E 5건의 별도 risk gate.
- 동일 좌표 장시간 swipe가 짧은 탭으로 해석되면 Wi-Fi 등 타일 상태를 변경할 수 있다. **Wi-Fi는 저위험 probe가 아니다.**
- 본 read-only discovery 승인만으로는 `input swipe <cx> <cy> <cx> <cy> 1000` probe를 실행하지 않는다. 기본 판정 = `LONGTAP_INJECTION_UNRESOLVED`, E 5건 미실행.
- 실행하려면 비영속·비토글 probe target, 대상 상태별 pre/post 명령, 오입력 시 STOP 기준을 적은 **별도 mutation-risk runsheet와 사용자 명시 승인**이 필요하다.
- 추후 승인된 probe 실패만으로 `LONGTAP_UNSUPPORTED`를 확정하지 않는다. 좌표/target handler/물리 positive control을 분리해 `LONGTAP_INJECTION_UNRESOLVED`로 보고한다.

**③ HOME 1건 + 1단/2단 focus 지도 12건 전수 채록** — B0·B1·C의 입력.
- QPN_121: HOME precondition에서 canonical 원문대로 별도 채록한다. QS 격자 결과에 합치지 않는다.
- 1단(B1): 각 TC/각 방향마다 `collapse → HOME → 1단 → DOWN(Wi-Fi anchor)`로 reset한 뒤 canonical의 정확한 origin·방향을 실행한다. RIGHT→DOWN→LEFT→UP 연속 경로를 각 방향의 독립 이웃처럼 해석하지 않는다.
- 2단(C): 각 TC마다 `collapse → HOME → swipe×2 → DOWN(Wi-Fi anchor)`로 reset하고 canonical 절차대로 origin을 확립한 뒤 입력한다.
- `keep press` 원문(138·140·141)은 longpress로 바꾸지 않는다. 같은 방향의 **짧은 keyevent를 최대 8회**, 매회 dump하며 최초 목표/경계 도달에서 중단하고 실제 최소 횟수를 기록한다.
- QPN_130만 `alternate_expand_target` focus를 dump로 확인한 뒤 **짧은 OK 1회**를 허용한다. 타일 위 OK는 금지한다.

## 4. per-TC 절차 (discovery 표준)

1. 시작 정규화: `cmd statusbar collapse` → `HOME` (이전 TC 상태 이월 차단)
2. manifest `entry_detail` 대로 진입(§1 확정 좌표 사용)
3. pre dump → 입력 → post dump (`/data/local/tmp` 만 사용, `/sdcard` 금지)
4. 채록: literal 은 text·**content-desc 양쪽** 확인. Wi-Fi 계열은 **prefix 로만** 기록(SSID 는 `<SSID>` 마스킹)
5. 판정 어휘: `LITERAL_CONFIRMED` / `LITERAL_PENDING`(표기차·실측 채록) / `NOT_PRESENT` / `ENTRY_FAILED` / `FOCUS_OBSERVED` / `INPUT_INJECTION_UNRESOLVED` / `INPUT_UNAUTOMATABLE` / `SAFETY_BLOCKED` / `PRECONDITION_MISMATCH` / `DISCOVERY_BLOCKED`
6. cleanup: `cmd statusbar collapse` → HOME
7. TC가 canonical 입력을 안전 규칙 때문에 끝까지 실행하지 못하면 `SAFETY_BLOCKED` 또는 `INPUT_INJECTION_UNRESOLVED`로 기록한다. 보조 노출 evidence를 해당 TC 성공으로 승격하지 않는다.

## 5. 안전 (hard denylist — 위반 시 즉시 중단·보고)

- **QPN_012 긴급 전화**: 원문의 긴급 전화 화면 전환은 실행하지 않는다. 전원 팝업의 `긴급 전화` 항목은 **노출·focus 확인까지만**, **OK/탭 절대 금지**(발신 위험), 이탈은 BACK. TC 판정은 `SAFETY_BLOCKED`; 보조 literal evidence와 분리한다.
- **QPN_011·175 전원 버튼**: 전원 버튼 자체의 tap/OK로 팝업을 여는 것까지만 허용. 팝업 내부 `긴급 전화`/`전원 끄기`/`다시 시작` 위에서 **OK 금지**. 이탈은 BACK.
- **QPN_141 전원 버튼 focus**: focus 확인까지만. OK 금지.
- **QPN_043/044 터치 잠금**: `켜기` 팝업 **노출만**. `확인` 금지, `취소`로만 이탈.
- **클러스터 G 편집 모드(002·008·167·168)**: 편집 화면 **진입·노출·focus 까지만**. 타일 드래그·추가·삭제·저장 **전부 금지**. 이탈은 BACK, 이탈 후 1단 타일 구성이 진입 전과 동일한지 dump 로 확인해 보고.
- **토글 금지 전역**: Wi-Fi/블루투스/모바일데이터/핫스팟/절전/방해금지/자동회전 타일에 **짧은 OK·탭 금지**(토글 발생).
- 비토글 control/명시 navigation target의 짧은 OK/tap 허용은 canonical이 요구하는 `QPN_002·004·008·010·011·012·043·044·130·158·159·165·167·168·175·176`에 한정한다. 실행 직전 focused desc/resource-id가 해당 control인지 dump로 gate한다. QPN_012는 전원 버튼까지만 허용하고 팝업 내부 OK는 금지한다.
- **QPN_163 집중 모드**: 짧은 OK가 page 이동이 아니라 상태 토글로 해석될 가능성을 본 read-only 세션에서 배제할 수 없으므로 `SAFETY_BLOCKED`. 상태별 pre/post와 오입력 대응이 있는 별도 mutation-risk 승인 전 실행 금지.
- 타일 OK 길게는 §3-① Wi-Fi probe 성공 후, D 7건의 canonical target에만 각 1회 허용한다. 매회 focused desc를 먼저 gate하고 예상 목적지 미도달 시 D 잔여를 즉시 중단한다. touch-longtap은 §3-② 별도 승인 전 0회.
- **SOS(134) 발신 절대 금지**. `am start` 직접 기동 금지. 설정값 변경·저장·삭제·발신 0.

## 6. 종료 게이트

```bash
adb -s B06201249E0002F0 shell "pm list packages | sort" > <scratch>/F0_pkgs_post.txt
adb -s B06201249E0002F0 shell "settings get global airplane_mode_on" > <scratch>/F0_airplane_post.txt
adb -s B06201249E0002F0 shell "dumpsys wifi | grep -m1 'Wi-Fi is'" > <scratch>/F0_wifi_post.txt
adb -s B06201249E0002F0 shell "settings get secure sysui_qs_tiles" > <scratch>/F0_qs_tiles_post.txt
adb -s B06201249E0002F0 shell "content query --uri content://media/external/images/media --projection _id | wc -l" > <scratch>/F0_media_post.txt
adb -s B06201249E0002F0 shell "ls /data/local/tmp"          # 본 세션 임시파일 0 (직접 정리)
# HOME 복귀 상태로 종료
```

host에서 `*_pre.txt`와 대응 `*_post.txt`를 exact compare한다. package/Wi-Fi/비행기모드/QS 타일 구성/MediaStore 중 하나라도 diff = `POSTCONDITION_MISMATCH`; 원인 추정·자동 복구·추가 TC 진행 금지, diff를 그대로 보고한다. `sysui_qs_tiles` fallback을 썼으면 동일 정규화 규칙의 pre/post identity 순서를 비교한다.

## 7. 산출물 (신규 3종, 그 외 repo 무편집)

| 산출물 | 경로 |
|---|---|
| raw dump/png (**gitignore 대상**) | `THOR2 - ALT Basic TC Audit/catalog/f0_c03_qpn_2026-08-20/raw/` |
| per-TC ledger CSV | `THOR2 - ALT Basic TC Audit/DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv` — 열: `tc_id, entry_status, entry_route, input_used, input_injection_status, safety_status, literal_expected, literal_observed, desc_observed, verify_status, focus_observed, state_diff, divergence, evidence_files, note` |
| summary MD | `THOR2 - ALT Basic TC Audit/DISCOVERY_C03_QPN_SUMMARY_2026-08-20.md` — §3 3대 질문 답 · focus 격자 지도 · 클러스터별 분류 제안 · 신규 함정 |

- **raw 는 반드시 `raw/` 하위**(`.gitignore: **/catalog/**/raw/`). ledger/summary 에 **SSID·PII 미전사**(`<SSID>` 마스킹).
- git stage/commit/push **0**.

## 8. 보고 (STOP 후 Claude 검증)

- **§3 3대 질문 답을 맨 앞에** — primitive gate 결과이며 개별 44건 자동화 가능과 동일시하지 않는다. §3-②는 별도 승인 없으면 `NOT_EXECUTED_PENDING_MUTATION_RISK_APPROVAL`로 명시한다.
- 분포: 상호배타 44 = `LITERAL_CONFIRMED / LITERAL_PENDING / NOT_PRESENT / ENTRY_FAILED / FOCUS_OBSERVED / INPUT_INJECTION_UNRESOLVED / INPUT_UNAUTOMATABLE / SAFETY_BLOCKED / PRECONDITION_MISMATCH / DISCOVERY_BLOCKED` 상태별 건수. QPN_141 safety overlay 중복 계수 금지. 어휘 = `manual evidence observed` 만.
- 필수 첨부: 정체 게이트 값 · package/Wi-Fi/비행기모드/QS 타일 구성/MediaStore **pre==post exact diff** · 세션 temp 0 · 편집모드 이탈 후 타일 구성 동일 · 산출 3종 경로 · 미실행 TC 와 사유.
- 보고 후 **STOP** — driver 설계·backfill·commit 은 Claude/사용자 영역.
