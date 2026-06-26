# ALT Basic batch10 — C01 narrow fail-closed pilot driver (design)

- 날짜: 2026-06-26
- 트랙: THOR2 ALT Basic TC Audit — Part B (device validation)
- 대상 단말: F0 `B06201249E0002F0` (AT-M140 THOR2, build RY07260601S, ko-KR). B27/ODIN2 미접촉.
- 실행 repo: **thor2j-tc-appium** (§2.5 cross-commit 금지 — 실행코드는 thor2j side)
- 입력 계약: tc-runner `THOR2 - ALT Basic TC Audit/handoff_device_validation/THOR2J_HANDOFF_BATCH10_2026-06-25.md` + manifest CSV (read-only)
- 상태: **설계 (코드 0). host-TDD 구현 + 단말 2-run 은 본 spec/plan 승인 후.**

---

## 1. 배경 — pre-scan 요약과 "full generic driver" 포기 근거

batch10 236행 entry_detail/verifier 전수 read-only pre-scan(`scratch/_batch10_entry_scan_report.md`, 2026-06-26) 결과:

| bucket (구조 분류) | n | % | 비고 |
|---|---|---|---|
| auto-generic | 44 | 18.6% | **UPPER BOUND / OVERCOUNT** (아래) |
| needs-domain-helper | 9 | 3.8% | focus_state 6 + app-nav 3 |
| ambiguous (fail-closed) | 166 | 70.3% | bare-prose step 141 + navigate 조합 25 |
| manual (elevated §6) | 17 | 7.2% | handoff §6 = 18; `CAL_355` 236 부재 → 17 정합 |

**full generic driver 비viable 근거:**

1. entry_detail 자유서술 비중 압도적 — `press_key` 본문이 distinct **134** 파편. 같은 키가 제각각 표기(`UP 방향키`/`UP방향키`/`Press Up`/`Navi 키( ↑)`/`위 하드키`).
2. `press_key`로 라벨됐지만 **실제 키가 아닌** 항목 다수 — focus-prose(`wifi focus`·`새 연락처 만들기 focus` 등 30+), 화면상태(`간편 설정 페이지`), 모호(`아무 방향키`·`해당 버튼을 짧게 누른다`).
3. navigate 타겟에 소스 TODO 플레이스홀더(`[앱 서랍 진입 설명 추가 필요]`)까지 존재.
4. 따라서 `auto-generic 44`는 **상한선**이며 실제 자동화 가능 수치는 더 작다. 이 수치를 자동화 달성치로 오해/과장 금지.

→ 전수 한글 사전을 코드에 굳히면 **검증 안 된 해석이 고착**된다. 대신 **검증된 실제 키/동작만 허용하는 narrow 드라이버 + 미커버 전부 fail-closed**로 전환한다. 병목은 드라이버가 아니라 manifest entry_detail 품질 → entry_detail 정규화는 §8 후속 트랙.

---

## 2. 목표 / 비목표

**목표:** C01(1.Basic principle, 13행) 중 **clean 실행가능분을 host-TDD로 준비**하고, 단말 2-run **직전 STOP**. narrow 드라이버가 fail-closed 구조로 C01을 통과시킬 수 있는지 검증(레버 확인).

**비목표(금지):**
- 236 전수 사전 구현
- 자유서술을 실행 step으로 추측 변환 / focus-target prose를 키 입력으로 해석
- BSC_025/BSC_124 억지 실행
- 단말 접촉 (본 spec/plan 단계)
- commit / push
- entry_detail 정규화 (별도 트랙 §8 — C01 pilot 선결조건으로 삼지 않음)

---

## 3. C01 분류 (spec 고정) — 실측 entry_detail 직독 기반

> directive 초안은 "auto/literal 9"로 두었으나, entry_detail 직독 결과 그 9 중 4건(BSC_031/071/072/073)이 vague-nav/미지정이라 **추측 금지 원칙상 clean 실행가능에서 제외**. 정직 정정 — STOP에서 사용자 결정 항목.

| tc_id | manifest entry_detail | verifier | disposition | 근거 |
|---|---|---|---|---|
| BSC_014 | `press_key:Recent App 버튼` | literal `최근앱 리스트 화면` | **pilot-literal** | 단일 하드키 (cand APP_SWITCH 187) |
| BSC_015 | `press_key:Home 버튼` | literal `홈스크린` | **pilot-literal** | 단일 하드키 (cand HOME 3) |
| BSC_017 | `press_key:Contact 버튼` | literal `연락처 앱 실행 초기 화면` | **pilot-literal** | 단일 하드키 (cand CONTACTS 207) |
| BSC_018 | `press_key:Message 버튼` | literal `메시지 앱 실행 초기 화면` | **fail-closed (device key-discovery)** | **표준 Android keycode 부재**(KEYCODE_MESSAGE 없음) → 후보 추측 금지; 키 발견 후 편입 |
| BSC_019 | `press_key:Camera 버튼` | literal `카메라 앱 실행 초기 화면` | **pilot-literal** | 단일 하드키 (cand CAMERA 27) |
| BSC_120 | `tap:더보기 > press_key:하드키 돌아가기` | `[focus_retained]` ; literal `더보기` | **pilot-focus** | tap+BACK(4)+fsnap 2축 (§5) |
| BSC_121 | `tap:더보기 > press_key:하드키 지우기/취소` | `[focus_retained]` ; literal `더보기` | **fail-closed (device key-discovery)** | `지우기/취소` 하드키 표준 keycode 불확정 → 추측 금지; 키 발견 후 §5 2축으로 편입 |
| BSC_031 | `press_key:숫자버튼 길게` | literal `Quick Dialer…팝업창` | **fail-closed (needs-decision)** | "숫자버튼" 어느 digit 미지정 — 추측 금지 |
| BSC_071 | `press_key:홈화면에서 Navi U/D/L/R/OK 키 입력` | literal `전화` | **fail-closed (needs-decision)** | 키/순서 불명; literal '전화'는 홈에서 자명(약한 verifier) |
| BSC_072 | `…U/D/L/R/OK > press_key:Navi Up키` | literal `갤러리` | **fail-closed (needs-decision)** | step1 vague-nav |
| BSC_073 | `…U/D/L/R/OK > press_key:Navi Down키` | literal `앱서랍` | **fail-closed (needs-decision)** | step1 vague-nav |
| BSC_025 | `press_key:종료 버튼 길게` | literal `전원 종료 팝업/긴급전화/…` | **observe-only (manual)** | elevated §6 — 전원 모달 confirm 금지, Back 이탈 |
| BSC_124 | `press_key:Select box Dropdown 활성화 > 돌아가기 하드키` | `[focus_absent]` | **UNSUPPORTED (fail-closed)** | bare 연속 step + focus_absent 미검증 assert |

**요약 (정직 카운트, no-guess):** clean host-pilot **5** = pilot-literal 4 (BSC_014/015/017/019) + pilot-focus 1 (BSC_120) · device key-discovery **2** (BSC_018 Message · BSC_121 지우기/취소 — 표준 keycode 부재, 현재 fail-closed) · fail-closed needs-decision **4** (BSC_031/071/072/073) · observe-only **1** (BSC_025) · unsupported **1** (BSC_124). 합 **13**.

> directive 초안 "실행가능 11(9 literal + 2 focus)" → 실측·no-guess 적용 후 **host-pilot 5**. 축소 사유: literal 9 중 4(BSC_031/071/072/073) vague-nav/미지정, 추가로 2(BSC_018/121) 키 표준 keycode 부재. **이게 STOP의 최우선 검토 항목** — entry_detail 품질이 throughput 병목임을 C01 13건 안에서 재확인.

---

## 4. 아키텍처

기존 인프라 재사용(무수정): `runner/altbasic_validation_batch1.py`(b1: `Dev`/`run_one`/`adb`/`UDID`/`SERVER`/`REPO`) + `runner/focus_snapshot.py`(fsnap). batch11 패턴(EV_BASE in-memory override) 동일.

두 모듈로 분리(테스트 격리):

- **`runner/altbasic_narrow.py` (pure, Appium import 0 — host-TDD 대상)**
  - `parse_entry_detail(s) -> [Step]` : `>` 분할, `action:body` 추출, step number 제거. bare/unknown prefix는 `Step(action=UNSUPPORTED, raw=…)`로 보존(추측 0).
  - `KEY_DICT` : **표준 keycode 후보가 존재하는 키만**(run1 device-verify 대상). C01 = {`Recent App 버튼`→187, `Home 버튼`→3, `Camera 버튼`→27, `Contact 버튼`→207, `하드키 돌아가기 버튼`→4}. **표준 keycode 부재 키(`Message 버튼`·`지우기/취소`)는 사전 미등록 → resolve=UNSUPPORTED**(추측 0; device key-discovery 후속 트랙). 사전에 없는 키名 = 전부 UNSUPPORTED.
  - `resolve_step(step) -> Action | UNSUPPORTED` : 키名→keycode / tap target 해석. 모호·미사전 → UNSUPPORTED(fail-closed).
  - `literal_decision(expected_literals, dump_text) -> PASS|LITERAL_PENDING|ABSENT` : 전 literal substring present=PASS / 일부만·표기차=LITERAL_PENDING(실측 literal 채록) / 전무+화면도달실패신호=호출부에서 ENTRY_FAILED.
  - `focus_retained_decision(baseline_snap, post_snap, dropdown_absent: bool) -> PASS|VERIFIER_FAILED` : 2축(§5).
- **`runner/altbasic_c01_driver.py` (device executor + CLI)**
  - manifest CSV(read-only)에서 C01 행 로드 → disposition 분기.
  - pilot-literal/focus만 실행. fail-closed/unsupported/observe-only는 실행하지 않고 해당 result code 기록.
  - b1.Dev 프리미티브(`home`/`tap_text`/`src`/`has`/`evidence`/`d.press_keycode`)로 step 실행, `altbasic_narrow` 결정 함수로 판정.
  - b1.run_one 재사용(결과코드 매핑·evidence·results CSV). EV_BASE = `evidence/altbasic_batch10_c01_20260626`.
  - CLI: `--tc ALTBASIC_BSC_014` / `--seq` / `--run {1,2}` (b1 패턴).

---

## 5. BSC_120/121 — 2축 focus_retained 검증 계약

> 본 계약은 2건 공통이나, **host-pilot 대상은 BSC_120(키=BACK 4)만**. BSC_121(`지우기/취소` 키 표준 keycode 부재)은 device key-discovery 후 동일 계약으로 편입(현재 fail-closed).

의도 outcome은 **2축**이다. 둘 다 충족해야 PASS, 하나만이면 승격 금지.

- **precond**: `더보기 포커스 상태` (더보기 아이콘 focused + dropdown 메뉴 목록 열림).
- **baseline 캡처**: tap("더보기") 후 dump → ① 더보기 focused 요소(fsnap.parse_focused_attrs: resource-id/bounds/class) ② dropdown 메뉴 항목 노드(목록) 시그니처.
- **action**: `하드키 돌아가기`(BSC_120, BACK 4) / `하드키 지우기/취소`(BSC_121, CLEAR/CANCEL cand) 입력.
- **post 캡처 + 2축 assert**:
  - **axis1 (dropdown 닫힘)**: post dump에 dropdown 메뉴 목록 노드 **부재**.
  - **axis2 (focus 유지)**: post의 focused 요소가 baseline 더보기와 동일(fsnap.is_baseline_equivalent — resource-id/class 일치).
- **판정**: axis1 ∧ axis2 → PASS. axis2만(focus 유지하나 dropdown 잔존) → **VERIFIER_FAILED / verifier-gap NOTE** (false-PASS 구멍 차단, 단독 승격 금지). axis1만 → VERIFIER_FAILED.
- dropdown 노드 시그니처·CLEAR/CANCEL keycode는 **run1 device-verify**로 확정(발명 0). 미확정 시 ENTRY_FAILED.

---

## 6. result code (fail-closed 포함)

| code | 의미 | 승격 |
|---|---|---|
| `SINGLE_RUN_PASS` / `RUN2_PASS` → `TWO_RUN_GREEN` | run1∧run2 PASS | **RUNNABLE_NOW** |
| `LITERAL_PENDING` | 화면 도달, 기대 literal과 표기차/부분노출 → 실측 literal 채록(발명 0) | 미승격 (run1 backfill) |
| `VERIFIER_FAILED` | literal 전무(도달 후) / focus assert 실패 / BSC 단축 1축만 | 미승격 |
| `ENTRY_FAILED` | nav 기계 실패 — 키 사전 부재·keycode 무동작·tap target 미발견·앱 미실행 | 미승격 |
| `UNSUPPORTED_ENTRY_DETAIL` | **fail-closed** — bare/unknown/미사전-키/vague 토큰 → 실행 거부, 추측 0 | 미승격 |
| `OBSERVE_ONLY` | elevated §6 — 노출 확인 + Back 이탈, confirm 금지 | 미승격(자동) |
| `DEVICE_FIT_SKIP` | precond 미충족 (FAIL 아님) | — |
| `CLEANUP_FAILED` | 종료 verify 실패 (즉시 보고) | — |
| `INFRA_FAILURE` | appium/예외 | — |

**unsupported 처리 정책**: parser가 bare-step/unknown-prefix/미사전-키/vague 토큰을 만나면 즉시 `UNSUPPORTED_ENTRY_DETAIL`(offending 토큰 기록), **실행 시도 0·추측 매핑 0**. BSC_124 및 fail-closed 4건이 기본 대상.

**elevated observe-only(BSC_025)**: 전원 모달 도달 → 노출 라벨 dump 채록 → **Back으로 모달 닫고 HOME 복귀**. 위험 버튼(전원끄기/다시시작/긴급전화) tap/OK/confirm **절대 금지**. 자동 승격 대상 아님.

---

## 7. 단말 2-run 전 STOP 지점

```
[host, 단말 0]  spec 승인 → plan 승인 → host-TDD 구현(parser/dict/checker/focus 테스트 GREEN)
                → C01 dry-run selection 리포트(어느 tc가 pilot/fail-closed/observe/unsupported로 가는지)
   ┌─────────────────────────  ★ STOP  ─────────────────────────┐
   │ 여기서 멈춘다. helper APK 설치·F0 실행 0. 사용자 device-go 대기 │
   └─────────────────────────────────────────────────────────────┘
[device]        사용자 승인 → Appium /status → helper 설치 → C01 run1 → run2 → TWO_RUN_GREEN 회수
```

- host-TDD까지는 단말 무접촉. 모든 결정 함수는 fake Dev / synthetic fsnap fixture로 검증.
- STOP 후 device-go 받으면 run1에서 키사전(Message/CLEAR keycode)·dropdown 시그니처 device-verify → run2.

---

## 8. 후속 트랙 (별도 device-free, C01 선결조건 아님)

- **(c) entry_detail 정규화**: 자유서술 → 실행가능 step. 236 throughput 확대의 실제 병목 후보. 별도 트랙으로 분리하되 C01 pilot을 막지 않는다.
- fail-closed needs-decision 4건(BSC_031/071/072/073): 해석을 명시 결정하면 narrow 사전에 편입 가능(예: BSC_031 digit 지정, BSC_071~073 nav 시퀀스 정의). 추측으로 자동 편입 금지.

---

## 9. §2.5 / 안전 경계

- spec/plan/manifest/STAGE1 yaml = tc-runner side. 실행코드(`altbasic_c01_driver.py`/`altbasic_narrow.py`) = thor2j side. cross-commit 금지.
- mutation 0 (NAVIGATION/READ_ONLY + Back/HOME). 위험 tap denylist(handoff §7) 준수. helper pre/post diff 0 + uninstall.
- evidence local-only(commit 금지). 회수 리포트 = tc-runner `RESULT_RECOVERY_BATCH10_C01_*.md`.
