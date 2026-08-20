# ALT Basic batch10 — C03/C04 (14.Quick panel) driver slice v1 설계 (2026-08-20)

**입력**: `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`(44행) + `DISCOVERY_C03_QPN_SUMMARY_2026-08-20.md`
(Codex 실행 · Claude 재검증) + C02 자산(`RESULT_RECOVERY_BATCH10_C02_2026-08-19.md` §6~7,
catalog `KEY-011`·`STR-012~014`).
**선례**: C02 driver (`runner/altbasic_c02*.py`) — adb-only·no-guess·fail-closed·hard guard 승계.

## 1. 스코프 — drivable 31 / registry 13

### 1.1 drivable (device 2-run 대상)

| disposition | tc_id | 요지 |
|---|---|---|
| `QPN_STAGE` (4) | 001 · 004 · 116 · 130 | 진입·단계 전환·펼치기 OK. stage 판별자로 검증 |
| `QPN_FOCUS_SPLIT` (4) | 123 · 124 · 125 · 121 | 1단 격자 이동(121은 HOME 격자 — 별도 origin) |
| `QPN_FOCUS_FULL` (7) | 131 · 134 · 135 · 137 · 138 · 140 · 142 | 2단 격자·경계·CANCEL 복귀 |
| `QPN_TILE_LONGOK` (5) | 133 · 146 · 149 · 153 · 155 | 타일 OK 길게 → 설정 화면 (**상태 pre/post 불변 동반 검증**) |
| `QPN_CONTROL_OK` (4) | 010 · 176 · 167 · 168 | 비타일 control navigation (010=tap, 176·167=OK, 168=UP) |
| `QPN_POPUP_EXPOSE` (5) | 011 · 175 · 141 · 043 · 044 | 팝업/제어 **노출·focus 만**. 175만 gated entry OK 1회, 팝업 내부 OK 금지 |
| `QPN_EDIT_VIEW` (2) | 002 · 008 | 편집 화면 노출·복귀 (**타일 구성 exact diff 0 postcondition**) |

합 **31**.

### 1.2 registry (device 무접촉 — 사유 기록)

| bucket | tc_id | 해소 조건 |
|---|---|---|
| `QPN_LONGTAP_PENDING` (5) | 026 · 053 · 056 · 066 · 102 | 터치 롱탭 = mutation-risk. **별도 runsheet + 사용자 승인** 전 미실행 |
| `QPN_CANDIDATE_ONLY` (4) | 157 · 158 · 159 · 165 | active QS 부재, edit candidate 에만 존재 → precondition 불일치. 타일 추가는 mutation |
| `QPN_CAPTURE_BLOCKED` (1) | 145 | 목적지에서 `uiautomator dump` = `could not get idle state`. **capture 전략 선설계 필요** |
| `C02_INPUT_UNAUTOMATABLE` (1) | 122 | 물리 홈 길게 — adb 재현 불가(KEY-011). HDK_019 와 동일 축 |
| `QPN_SAFETY_BLOCKED` (2) | 012 · 163 | 012 = 긴급 전화 발신 위험 / 163 = 안전 제한. **원문 대상 실행 금지** |

합 **13**. 31 + 13 = 44 (chunk 전수, 상호배타).

## 2. ★핵심 설계 원칙 — 조건형 anchor (고정 시퀀스 금지)

discovery 신규 함정: **split 재진입 시 entry focus 가 keyboard nav 이력에 따라 `NONE` 또는 `Wi-Fi`
로 갈린다.** 이미 Wi-Fi 인데 unconditional DOWN 을 보내면 모바일 데이터로 이동해 origin 이 틀어진다.
full entry 는 `NONE → DOWN=brightness → DOWN=Wi-Fi` 순서가 관찰됐다.

→ **`ensure_focus_at(target_desc, stage, budget)`**: ① 현재 focused desc 확인 → ② 이미 target 이면
**키 0회** → ③ 아니면 stage 별 격자 규칙으로 bounded seek(각 스텝 dump 확인) → ④ budget 소진 =
fail-closed(`ANCHOR_FAILED`). **unconditional key 금지**를 pure 단계에서 강제한다.

본 원칙은 오늘 세 번째 사례다 — 설정 진입 기하 라우팅 · 메시지 `seek_desc_plan` · 본 anchor.
**"1회 관찰 시퀀스를 driver 상수로 승격 금지"** 를 C03 설계 원칙으로 명문화한다.

## 3. 격자 지도 (discovery 실측 — driver 상수)

**1단(split)**: `Wi-Fi →RIGHT 블루투스` / `Wi-Fi →DOWN 모바일 데이터` / `블루투스 →DOWN 소리 모드` /
`모바일 데이터 →RIGHT 소리 모드` / `모바일 데이터 →DOWN 펼치기` / `소리 모드 →DOWN 펼치기` /
`펼치기 →OK = full stage + Wi-Fi focus`

**2단(full)**: `Wi-Fi →UP brightness` / `brightness →DOWN Wi-Fi` / `Wi-Fi →RIGHT 블루투스` /
`Wi-Fi →DOWN 모바일 데이터` / `Wi-Fi →DOWN×3 = 모바일 데이터→비행기 모드→edit` /
`edit →UP×4 = 비행기 모드→모바일 데이터→Wi-Fi→brightness` / `edit →RIGHT×2 = settings→power(pm_lite)` /
`full Wi-Fi →CANCEL(67) = split + Wi-Fi focus`

**2단 page2 경로(2026-08-20 discovery 실행 명령 이력 복원·복수 target gate 확인)**:
full 무초점에서 `DOWN×4 = brightness→Wi-Fi→모바일 데이터→비행기 모드`, 이어
`RIGHT×2 = 손전등→위치(page2)` / page2 `위치→RIGHT 화면 터치 잠금` /
`위치→DOWN 화면 자동 회전→DOWN 데이터 절약` /
`화면 터치 잠금→DOWN 절전 모드→DOWN 방해 금지 모드`.
driver 는 이 전체 시퀀스를 무조건 재생하지 않고 매 키 뒤 dump를 읽어 `ensure_focus_at()`으로
재계산한다. 현재 target이면 키 0회, 미등록 focus/edge면 fail-closed한다.

**HOME**: `HOME →DOWN = focused container descendant '전화'` (QPN_121 전용 origin)

**active QS 12**: Wi-Fi/블루투스/모바일 데이터/소리 모드/비행기 모드/손전등/위치/화면 터치 잠금/
화면 자동 회전/절전 모드/데이터 절약/방해 금지 모드

## 4. verify 계약

- 기존 재사용: `qs_stage`(full/split/none) · `desc_focus` · `desc_focus_prefix`(Wi-Fi 는 SSID 포함) ·
  `literal` · `desc_present`
- **신규 `state_unchanged`**: `QPN_TILE_LONGOK` 전용. `--longpress 23` 이 short-OK 로 오해석되면
  토글이 발생하므로 **대상 설정값 pre/post exact 비교**를 verify 스텝으로 편입한다.
  대상 키: `wifi`(dumpsys) · `mobile_data` · `accelerometer_rotation` · `restrict_background` ·
  `zen_mode` · `ringer`. TC 별로 해당 축만 지정.
  driver 는 longpress 직전 scalar snapshot 을 baseline 으로 잡고 목적지 노출 직후 같은 extractor 로
  post 값을 읽어 pure evaluator 에 `(axis, before, after)`를 전달한다. Wi-Fi 는 동적 전체 dumpsys 가
  아니라 `Wi-Fi is ...` 단일 상태행만 정규화해 exact 비교한다.
- **신규 `qs_tiles_unchanged`**: `QPN_EDIT_VIEW`/`QPN_CONTROL_OK`(167/168) 전용.
  `settings get secure sysui_qs_tiles` pre/post **exact** 비교(편집 화면에서의 배치 변경 감지).
- **transient 대응**: 화면 터치 잠금 타일은 page2 에서 **즉시 dump 미포함**(3초 settle 후
  `화면 터치 잠금, 꺼짐` 으로 gate) — `settle_gate` 는 최대 3.0초, 0.5초 간격 재-dump 로 구현한다.
  조건 충족 즉시 종료하며 선행 고정 sleep 은 금지한다.
  transient 는 043/044 한정이 아니라 **page2 일반 속성**이므로 page2 inventory 를 읽는
  QPN_001 도 동일 gate 를 선행한다.

### 4.1 TILE_LONGOK verify 재설계 (초판 결함 정정)

초판은 롱탭 직후 `verify literal` 하나로 목적지를 판정했다. 실측 결과 두 결함이 겹쳤다.

| tc | 목적지 dump | 원문 literal 이 진입 **전** QS 패널에도 존재 | 결함 |
|---|---|---|---|
| 133 | 있음 | `Wi-Fi` 존재 | 비판별 |
| 146 | **없음** | 아니오 | 근거 부재 |
| 149 | **없음** | **예** | 비판별 + 근거 부재 |
| 153 | **없음** | 아니오 | 근거 부재 |
| 155 | **없음** | **예** | 비판별 + 근거 부재 |

149/155 는 롱탭이 no-op 이어서 QS 패널에 그대로 있어도 verify 가 통과한다(위양성).
146/149/153/155 는 목적지 XML 이 없고 증거가 `_00_target.xml`(진입 **전**) + `.png` 뿐이다.

→ gate 체인을 판별력 순서로 재구성한다:

1. `state_unchanged(axis)` — scalar mutation guard (롱탭 오해석 포착, 최우선)
2. `qs_stage == none` — 퀵패널 이탈 (구조적 판별자, 전 TC 공통)
3. `activity_contains(<per-TC activity>)` — discovery 실측 목적지 activity
   (`SoundSettings`/`SmartAutoRotateSettings`/`DataSaverSummary`/`ZenModeSettings`;
   133 은 activity 미캡처라 목적지 dump 의 package 실측값 사용)
4. `literal_probe(<canonical 원문 literal>)` — bounded 재-dump

**`literal_probe` 는 미확보 시 FAIL 이 아니라 `LITERAL_PENDING`** 이며, 실패 경로에서도 목적지
dump 를 evidence 로 남긴다(backfill 판단의 유일한 근거). **activity 만으로 literal 을 대신
증명하지 않는다.** 원문 literal 을 실측값으로 미리 완화(backfill)하지 않는다 — 목적지 dump 확보
후 사용자 승인 영역.

### 4.2 QPN_002 inventory — 합집합 + BUG-GAP 종료 어휘

edit candidate 는 스크롤에 분산돼 단일 dump 로는 행이 잘린다(초판이 핫스팟을 놓친 원인).
→ `scroll_inventory` bounded DOWN 합집합(합집합이 2회 연속 정체하면 budget 을 남기고 정지).

원문 후보 11 = **관찰 10 + 부재 1(`취침 모드`)**. 부재는 미검증이 아니라 **결론**이므로 plan
완주 판정을 `runtime PASS` 로 두면 안 된다 → `expected_verdict()` 가 QPN_002 에 대해
**`BUG-GAP observed`** 를 반환한다. 2-run 이 모두 성공해도 RUNNABLE_NOW 승격 대상이 아니다.
`evaluate_inventory` 는 `missing`(관찰돼야 할 것의 부재 = 캡처 실패)과 `unexpected`(부재 판정
literal 의 출현 = divergence)를 분리해 FAIL 사유를 구분한다.

## 5. 안전 (코드 강제)

- `FORBIDDEN_KEYCODES = {134}` 전 plan 유지(SOS).
- **`QPN_POPUP_EXPOSE`**: 011/141/043/044 는 plan 에 OK(23) 부재를 pure 단계에서
  assert(`_assert_no_ok` 재사용). 175는 `pm_lite` focus verifier 뒤 짧은 OK 정확히 1회만 허용하고,
  팝업 literal verifier 이후에는 BACK만 허용한다. 팝업 내부 OK는 전 TC 금지한다.
- **타일 위 short OK 전역 금지**: `QPN_TILE_LONGOK` 은 `--longpress` 만, `QPN_CONTROL_OK` 는
  **비타일 control 에 한정**(실행 직전 focused desc/resource-id gate).
- **tap step**: canonical/ledger 가 tap 을 요구하는 002·004·008·010·011·043·044는 pure plan 에
  `tap_target(selector_kind, selector_value)`를 명시한다. driver 는 현재 dump 에서 clickable target이
  정확히 1개일 때만 bounds 중심을 tap한다. 0개/2개 이상/좌표 파싱 실패는 fail-closed이며 naked
  hard-coded tap 좌표는 금지한다. 043·044의 `취소`도 같은 exact-one gate를 적용한다.
- swipe 는 `QPN_*` 계열에서만 허용 — 기존 `_assert_swipe_scope` 의 허용 disposition 을 QPN 군으로 확장
  (C02 의 `HDK_QP_NAV` 와 동일 근거: QPN_004 원문이 스와이프를 명시).
- registry 13 은 **build_key_plan 자체가 fail-closed 예외**(무접촉 보장).

## 6. host-TDD 필수 커버

classify 44/44 + 미등록 fail-closed / disposition 별 plan 생성 / **011·141·043·044 OK 부재 +
175 gated OK 정확히 1회 assert** / 타일 short-OK 부재 assert / tap target exact-one·bounds 실패
fail-closed / `ensure_focus_at`: 이미 target(키 0회)·seek 도달·page1→page2 복원 경로·budget 초과
fail / page1/page2 격자 규칙 테이블 정합 / `state_unchanged`·`qs_tiles_unchanged` 평가 / `settle_gate` 조건형
wait(고정 sleep 아님) / swipe scope 확장 후에도 비-QPN 에서 거부. 전부 synthetic fixture(device 0).

## 7. 실행 프로토콜

run1/run2 독립 → `TWO_RUN_GREEN` 만 RUNNABLE_NOW 후보. evidence
`evidence/altbasic_batch10_c03_v1_<date>/run{n}/{tc_id}/`(thor2j local-only, gitignore).
**세션 종료 시 `/data/local/tmp` 자기 산출물 정리 필수**(C03 discovery 에서 35개 잔존 사례).

**정정 2026-08-20 (v1.1, Claude 재검증)**: 157 은 `TARGET_ABSENT` 가 아니라 `CANDIDATE_ONLY` — 핫스팟 `tile_label` 이 `QPN_002_108~113_scan_down` 에 실재한다. registry 총계 13 불변.
추가 정정: QPN_001 page2 inventory 에 `settle_gate` 결박(transient 는 page2 일반 속성), QPN_001 literal 은 canonical 15(tile 12 + 수정/설정/전원)로 정렬.

## 8. 상태

- [x] 설계 lock (본 문서)
- [x] host-TDD 구현 (thor2j — Codex, 5-suite 172 passed)
- [x] Claude 독립 재검증 (dry-run 44/44 · disposition mismatch 0 · 계약 8/8 코드 확인)
- [x] **B1/B2 해소** (§4.1·§4.2, 5-suite **184 passed** · dry-run 매핑 무변화 44/44)
- [ ] device 2-run (별도 승인)

### 8.1 device 2-run blocker (2026-08-20 재검증에서 발견)

| # | 대상 | 내용 | 필요 조치 |
|---|---|---|---|
| B1 | QPN_002 | edit candidate 는 **스크롤 분산 13종**인데 driver 는 단일 dump 로 9종만 검증 — 원문 11종 대비 미달인 채 GREEN 가능 | inventory 를 bounded scroll 합집합으로 재설계 (`ensure_focus_at` 와 같은 조건형) |
| B2 | QPN_146 | 목적지 증거가 `Settings$SoundSettingsActivity` **activity 뿐** — literal `소리 및 진동` 의 dump 근거 0 | 목적지 dump 확보 후 backfill, 또는 verifier 를 `activity_contains` 로 전환 |

> **정정 2026-08-20 (사용자 검토 반영)**
> - B1 은 "13종을 찾는 문제"가 아니다. 원문 11종 중 핫스팟 포함 **10종은 관찰, `취침 모드`는
>   실제 부재**다. 따라서 합집합으로 10종을 확인하고 부재는 `BUG-GAP observed` 로 판정한다.
>   QPN_002 를 `runtime PASS` 로 만들면 안 된다. → §4.2
> - B2 의 "verifier 를 `activity_contains` 로 전환"은 **채택하지 않는다**. activity 는 진입
>   경로만 증명하므로 literal 검증을 대체할 수 없다. 미확보 시 `LITERAL_PENDING` 을 유지한다.
> - B2 는 QPN_146 단독이 아니라 **TILE_LONGOK 5건 전부의 구조 결함**이었다. → §4.1
> - 두 건 모두 해소됐으므로 drivable 31 → 29 축소 운영은 **불필요**하다.
- 커밋: batch 대기

## 9. `취침 모드` 부재 판별 계획 (2-run 동반, 비파괴)

QPN_002 의 `BUG-GAP observed` 는 **판정 어휘**이지 root cause 가 아니다. 현재 근거로는 세 갈래를
구분할 수 없다 — 단말 결함 / 원문 스펙 불일치 / precondition 미비. §4.2 가 `SPEC_GAP` 결론에
"단말 결함 아님 입증"을 요구하므로 어느 쪽이든 판별이 선행돼야 한다. **판별 전 BUG_LOG 등록 안 함.**

### 9.1 이미 확보된 사실

- `취침 모드` 를 언급하는 canonical 은 batch10 전체에서 QPN_002 **한 건뿐**(교차 근거 없음).
- 원문 11 과 단말 13 은 포함관계가 아니라 **양방향 어긋남**:
  원문에만 `취침 모드`(1) / 단말에만 `노래 검색`·`텍스트 읽어주기`·`TV 리모컨`(3).
  → 원문 리스트가 이 빌드 기준이 아닐 가능성을 시사한다.
- [추론·미측정] `집중 모드` 와 `취침 모드` 는 통상 같은 Digital Wellbeing 계열인데
  **집중 모드는 단말에 실재**한다 → "provider 자체 부재" 가설은 약해져 있다.
  판별 전 결론으로 쓰지 않는다.

### 9.2 2-run 동반 관찰 (판정 불변·기록 전용)

`_capture_diagnostics()` 가 run 당 1회 비파괴 수집한다. 실패해도 run 을 막지 않되 실패 사실을 남긴다.

| 축 | 명령 | 판별 용도 |
|---|---|---|
| `packages` | `pm list packages` | provider 존재 여부 (1차 판별) |
| `qs_tiles` | `settings get secure sysui_qs_tiles` | active tile spec 실측 |

추가로 QPN_002 inventory 단계가 `registry_probe` 를 남긴다 — `취침 모드` + CANDIDATE_ONLY 4건의
대상(`핫스팟`/`Quick Share`/`QR 코드 스캐너`/`알람`) present/absent 지도.
**네 건은 판별 대상이 아니라 사유가 이미 확정된 상태**(candidate 실재·active QS 부재 → 추가 =
mutation)이므로, 이 기록은 그 사유가 매 run 여전히 유효한지(stale 가정 아님)를 확인하는 용도다.

### 9.3 결과 매핑

| 관찰 | 결론 | 후속 |
|---|---|---|
| provider 부재 | `SPEC_GAP` | TC 를 모델 비적용 표기. BUG_LOG 등록 안 함 |
| provider·기능 존재 + 타일만 부재 | `OBSERVED` | BUG_LOG `OPEN` 등록 |
| 기능 미설정이 원인 | 결함 아님 | TC 원문 precondition 정정 |

어느 쪽이든 QPN_002 는 **RUNNABLE_NOW 승격 대상이 아니다**(§4.2).
