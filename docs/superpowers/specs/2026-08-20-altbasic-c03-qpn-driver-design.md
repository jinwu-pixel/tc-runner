# ALT Basic batch10 — C03/C04 (14.Quick panel) driver slice v1 설계 (2026-08-20)

**입력**: `DISCOVERY_C03_QPN_LEDGER_2026-08-20.csv`(44행) + `DISCOVERY_C03_QPN_SUMMARY_2026-08-20.md`
(Codex 실행 · Claude 재검증) + C02 자산(`RESULT_RECOVERY_BATCH10_C02_2026-08-19.md` §6~7,
catalog `KEY-011`·`STR-012~014`).
**선례**: C02 driver (`runner/altbasic_c02*.py`) — adb-only·no-guess·fail-closed·hard guard 승계.

## 1. 스코프 — drivable 34 / registry 10

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
| `QPN_TILE_TOUCH_LONGTAP` (3) | 026 · 053 · 056 | 타일 **터치** 롱탭 → 설정 화면. **D1 승인 2026-08-21** (§11.3). 원문 입력 축이 하드키와 다름 (§11.6) |

합 **34**.

### 1.2 registry (device 무접촉 — 사유 기록)

| bucket | tc_id | 해소 조건 |
|---|---|---|
| `QPN_LONGTAP_PENDING` (2) | 066 · 102 | 대상 타일이 active QS 부재 = **D2(타일 추가) 선행**. D1 만으로 해소되지 않는 이중 게이트 (§11.1) |
| `QPN_CANDIDATE_ONLY` (4) | 157 · 158 · 159 · 165 | active QS 부재, edit candidate 에만 존재 → precondition 불일치. 타일 추가는 mutation. **158·159·165 는 타일 short OK 라 §5 전역 금지와도 충돌** (§11) |
| `QPN_CAPTURE_BLOCKED` (1) | 145 | 목적지에서 `uiautomator dump` = `could not get idle state`. adb 전용 계층 채널 **부재 확인** → 채널 결정 필요 (§10) |
| `C02_INPUT_UNAUTOMATABLE` (1) | 122 | 물리 홈 길게 — adb 재현 불가(KEY-011). HDK_019 와 동일 축 |
| `QPN_SAFETY_BLOCKED` (2) | 012 · 163 | 012 = 긴급 전화 발신 위험 / 163 = 안전 제한. **원문 대상 실행 금지** |

합 **10**. 34 + 10 = 44 (chunk 전수, 상호배타).

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
- [x] **registry 13 재구조화 + 145 채널 조사** (§10·§11, 2026-08-21 — 결정 축 3개로 압축)
- [x] **D1 슬라이스 호스트 구현** (`QPN_TILE_TOUCH_LONGTAP` 3건, §11.6 — 5-suite 200 passed · dry-run 34/10)
- [x] **T1 bounded 관찰기 host 구현** (`thor2j` `e225639` — 신규 22; 2026-08-28 T0 재자격
  5-suite+probe **222 passed** · dry-run 34/10 · device 호출 0회)
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

---

## 10. `QPN_145` 계층 캡처 채널 조사 (2026-08-21)

### 10.1 차단의 정확한 범위

§4.1 gate 4단 중 UI 계층을 요구하는 것은 2·4단이다.

| gate | 채널 | 145 에서 |
|---|---|---|
| 1 `state_unchanged(mobile_data)` | `settings get global mobile_data` | 가능 — discovery 에서 `1→1` 관찰 |
| 2 `qs_stage == none` | **UI dump** | 차단 |
| 3 `activity_contains` | `dumpsys window` `mCurrentFocus` | 가능 — 단 §4.1 이 비판별로 규정 |
| 4 `literal_probe` | **UI dump** | 차단 → `LITERAL_PENDING` |

판별력을 가진 두 gate 가 모두 계층에 의존한다. 드라이버는 이미 dump 실패를
`LiteralPendingError` → `LITERAL_PENDING` 으로 매핑하므로
(`tests/test_altbasic_c03.py::test_driver_probe_unobtainable_dump_is_pending_not_fail`),
**채널 없이 145 를 drivable 로 승격하면 scalar guard 와 비판별 activity gate 만 남아 판정이
성립하지 않는다.** "capture 전략 필요" 는 형식 요건이 아니라 실차단이다.

### 10.2 adb 전용 대안 — 전수 제거 (측정)

[측정: AT-M150 `alt_odin2-userdebug 14 UKQ1.240227.001` — **도구 표면 확인 용도**.
F0 상태 근거로 쓰지 않는다. 양 단말 모두 Android 14 이므로 플랫폼 도구 표면은 이전된다고 본다.]

| 후보 | 실측 | 판정 |
|---|---|---|
| `uiautomator dump` idle 우회 플래그 | 옵션 = `--verbose` / `--compressed` / `[file]` **뿐**. idle 대기 knob 없음 | 불가 |
| `dumpsys activity top` View Hierarchy | 섹션 존재 — 클래스·플래그·bounds·resource-id 출력. **text / content-desc 미출력** | literal 대체 불가 |
| `dumpsys window` `mCurrentFocus` | activity 명만 | §4.1 이 명시 거부 (진입 경로만 증명) |

→ **adb 전용 계층 채널은 존재하지 않는다.**

### 10.3 미확정 — 판별이 선행한다

`could not get idle state` 가 **영구**(주기 갱신 뷰가 접근성 이벤트를 계속 발생)인지
**일시**(로딩 스피너)인지 discovery 2 회 시도로는 구분되지 않는다. 갈래에 따라 해법이 정반대다.

**판별 수단**: `uiautomator events` (비파괴·adb 전용, `uiautomator help` 에 존재) 를 목적지에서
bounded 시간 동안 읽어 이벤트 소스의 주기성을 관찰한다.

관찰기 산출물은 총 이벤트 수·inter-event interval·마지막 이벤트 이후 경과의 **raw digest 로
한정**한다. 영구/일시 후보 분류와 후속 채널 결정은 출력하지 않으며, 사용자·Claude 가 digest 를
근거로 아래 표를 판정한다.

| 관찰 | 결론 | 후속 |
|---|---|---|
| 이벤트가 주기적으로 계속 발생 | 영구 | retry 무의미 — §10.4 채널 결정 |
| 수 초 내 정지 | 일시 | `settle_gate` budget 확대로 해소, 아키텍처 변경 불필요 |

**판별 전에 채널을 고르지 않는다** — §2 "1회 관찰 시퀀스를 driver 상수로 승격 금지" 와 같은 근거.

### 10.4 영구 확정 시 — 사용자 결정 항목

adb 전용 대안이 §10.2 에서 전수 제거됐으므로 남는 것은 하나뿐이다.

- **Appium UiAutomator2 `waitForIdleTimeout=0`** — idle 대기를 실제로 우회하고 text 포함 계층을
  반환한다. 단 C03 의 **adb-only 승계를 깨는 아키텍처 변경**이며, Appium 세션 생성 자체가
  상태를 건드릴 수 있다(포그라운드 앱 전환·키 입력). 채택 여부는 **사용자 결정 영역**.
- 미채택 시 145 는 `QPN_CAPTURE_BLOCKED` 유지가 정상 종결이다 — 회피 채널을 만들어
  판별력 없는 gate 로 승격시키지 않는다.

### 10.5 상태

- [x] adb 전용 대안 전수 제거 (§10.2)
- [x] `uiautomator events` bounded 관찰기 **host 구현** (`runner/altbasic_c03_idle_probe.py`,
  `thor2j` `e225639`; raw digest 만 출력, 영구/일시 판정 미출력, device 호출 0회)
- [ ] `uiautomator events` 판별 — **F0 device 관찰 필요**, 2-run 동반 1건으로 등록
- [ ] 영구 확정 시 채널 결정 — 사용자

---

## 11. registry 13 재구조화 — 결정 축 3개 (2026-08-21)

§1.2 는 registry 를 5 bucket 으로 나눴다. ledger `divergence` 열 재확인 결과 **bucket 경계와
실제 차단 요인이 일치하지 않는다.** 차단 요인 기준으로 다시 묶으면 결정은 3개다.

### 11.1 측정 — 이중 게이트

| tc | bucket | ledger `desc_observed` | ledger `divergence` |
|---|---|---|---|
| 066 | `QPN_LONGTAP_PENDING` | 핫스팟은 edit candidate 에만 존재 | 입력 미확정 + **active precondition 불일치** |
| 102 | `QPN_LONGTAP_PENDING` | 집중 모드는 edit candidate 에만 존재 | 입력 미확정 + **active precondition 불일치** |
| 157 | `QPN_CANDIDATE_ONLY` | 핫스팟은 edit candidate 에만 존재 | full QS active tile 아님 |

066 과 157 은 **같은 타일(Wi-Fi 핫스팟)** 이며 입력 방식만 다르다(066 = touch long-tap,
157 = OK longpress). 102 도 같은 타일 부재 축을 갖는다. 즉 `QPN_LONGTAP_PENDING` 5 건 중
**2 건은 롱탭 승인만으로 해소되지 않는다.**

### 11.2 측정 — 타일 short OK 충돌

| tc | ledger `input_used` | 대상 | §5 "타일 위 short OK 전역 금지" |
|---|---|---|---|
| 157 | `OK longpress 0` | 핫스팟 타일 | 저촉 없음 — `--longpress` 는 승인된 기전 |
| 158 | `OK 0` | Quick Share 타일 | **저촉** |
| 159 | `OK 0` | QR 코드 스캐너 타일 | **저촉** |
| 165 | `OK 0` | 알람 타일 | **저촉** |

158·159·165 는 타일을 추가해도 **여전히 실행 불가**다 — 원문이 요구하는 입력이 §5 가 전역
금지한 타일 short OK 이기 때문이다. 해소하려면 타일 추가 승인 **외에** 해당 타일이 toggle 형이
아니라 launch 형임을 근거로 한 **개별 예외 승인**이 추가로 필요하다.
원문 기대값이 각각 `Quick Share 설정 창` / `QR 코드 스캔` / `알람앱` 이라 launch 형으로
보이나 실측 근거가 없다 — [추론·미측정], 예외 승인 전 확인 대상.

### 11.3 결정 축 3개

| # | 결정 | 해소 대상 | 비고 |
|---|---|---|---|
| D1 | **터치 롱탭 입력 승인** — **승인됨 2026-08-21 (026·053·056 한정)** | 026 · 053 · 056 완전 / 066 · 102 부분 | 호스트 구현 완료 (§11.6). device 2-run 미실행 |
| D2 | **타일 추가 mutation 승인** (`sysui_qs_tiles` 변경 + 복원) | 066 · 102 · 157 완전 / 158 · 159 · 165 부분 | 6 건 공통 |
| D3 | **145 계층 채널** | 145 | §10.4 — 판별 후 결정 |
| — | (D2 후속) 타일 short OK 개별 예외 | 158 · 159 · 165 | launch 형 실측 근거 선행 |
| — | 종결 (결정 대상 아님) | 122 (adb 재현 불가) · 012 · 163 (실행 금지) | — |

### 11.4 D1 신규 state 축 — 2 확보 / 1 부재

`state_unchanged` 는 `read_state(dev, axis)` 가 exact 비교 문자열을 반환하는 계약이다
(`runner/altbasic_c03_driver.py`). LONGTAP 5 건 중 기존 축으로 덮이는 것은 2 건뿐이다.

| tc | 목적지 | axis | 채널 | 상태 |
|---|---|---|---|---|
| 026 | 모바일 데이터 설정 | `mobile_data` | `settings get global mobile_data` | 기존 축 |
| 053 | 자동 회전 설정 | `accelerometer_rotation` | `settings get system accelerometer_rotation` | 기존 축 |
| 056 | 절전 모드 메뉴 | `low_power` | `settings get global low_power` | **신규 — 확보** (scalar) |
| 066 | Wi-Fi 핫스팟 설정 | `hotspot` | `dumpsys tethering` → `Tether state:` 블록 정규화 | **신규 — 확보** (안정 상태행) |
| 102 | 집중 모드 설정 | — | global/secure 에 focus-mode scalar **부재** | **부재 — guard 미구성** |

[측정: AT-M150, 채널 표면 확인 용도] `low_power` = scalar 응답 확인.
`dumpsys tethering` 의 `Tether state:` 블록은 iface 당 1 행
(`wlan0 - AvailableState - lastError = 0`)으로 exact 비교 가능. **F0 에서 동일 포맷인지는
실행 시 확인 대상**이며, USB tethering 등으로 iface 집합이 변하면 위양성이 되므로
`wifi` 축과 동일하게 "정확히 예상 행수" 를 강제한다.

102 는 집중 모드 상태가 Digital Wellbeing 앱 내부에 있어 adb scalar 로 읽히지 않는다.
**scalar guard 를 만들 수 없으므로 D1·D2 가 모두 승인돼도 102 는 registry 유지가 기본값**이며,
비-scalar guard 를 별도 설계하지 않는 한 승격 대상이 아니다. 대체 guard 를 추측으로 만들지 않는다.

### 11.5 산출물

- 실행 절차·승인 요청: `THOR2 - ALT Basic TC Audit/RUNSHEET_C03_QPN_LONGTAP_2026-08-21.md`
- 본 절은 구조 기록이며, **승인은 runsheet 에서 받는다**. 본 절 자체는 어떤 실행도 허가하지 않는다.

### 11.6 D1 슬라이스 구현 (2026-08-21, 사용자 승인 후)

`QPN_TILE_TOUCH_LONGTAP` 신설 — 026 · 053 · 056. registry 13 → 10, drivable 31 → 34.

**입력 축이 원문에서 갈린다** (측정):
`TILE_LONGOK` 5건 원문 = `<타일> focus > Press OK 길게 입력` (하드키) /
본 3건 = `퀵 패널 > <아이콘> Long 탭` (터치, focus 언급 없음).
053 목적지는 149 와 같으므로 하드키로 대체하면 **053 은 149 의 중복**이 된다.
→ `build_qpn_plan` 이 본 disposition 에서 **하드키 OK 존재 자체를 assert 거부**한다.

| 항목 | 결정 | 근거 |
|---|---|---|
| 주입 기전 | `input swipe x y x y 1200` (동일좌표) | 단일 호출 원자적·self-terminating. `motionevent` DOWN/UP 은 UP 실패 시 **터치 고착** |
| 최소 지속 | **1000ms 강제** (`_touch_longpress` 가 미만을 `ValueError`) | `ViewConfiguration` 롱프레스 임계 기본 500ms 대비 여유 |
| 좌표 | 실행 시 `find_clickable_bounds` **exact-one** → bounds 중심 | §5 하드코딩 좌표 금지 승계 |
| selector | 신규 `desc_prefix` | 타일 content-desc 는 상태/SSID suffix 포함 (STR-014) — `desc_exact` 불가 |
| `tap` 사용 | **전 경로 금지** | short tap = 타일 토글 |
| 신규 state 축 | `low_power` (`settings get global low_power`) | 056 |
| **목적지 activity gate** | **두지 않음** | discovery 가 3건 모두 `NOT_EXECUTED` — 실측 activity 가 없다. 추측 금지(§4.1). 149 실측값을 053 에 전용하지도 않는다. 첫 run evidence 확보 후 backfill = 사용자 승인 영역 |

gate 순서 = `snapshot → touch_longpress → state_unchanged → qs_stage none → literal_probe → BACK`.
activity gate 부재로 판별은 **이탈 gate + 각 TC 자신의 canonical literal** 이 담당한다
(026 `모바일 데이터 설정` / 053 `화면 자동 회전 메뉴` / 056 `절전 모드 메뉴`).
literal 미확보 시 `LITERAL_PENDING` — FAIL 아님.

disposition 사유 문자열도 정정했다 — 3건은 discovery 실측이 아니라 **승인**이 근거이므로
`D1 touch long-tap approval 2026-08-21 (discovery NOT_EXECUTED)` 를 쓴다.

**검증**: host-TDD 5-suite **200 passed** (기존 188 → 신규 12) · dry-run `drivable=34 registry=10`.
**device 실행 0회** — F0 2-run 은 여전히 별도 게이트다.
