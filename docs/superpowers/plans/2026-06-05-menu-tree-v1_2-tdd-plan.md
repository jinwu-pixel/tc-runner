# Menu-Tree v1.2 — TDD 구현 Plan

> Status: **무단말 Task 1·2·3·5·6 구현 完 + Task 4 선결(I1·I2) DONE** (2026-06-05; 2026-06-08 I1 access probe `d9a3809`). Task 4 잔여 = APN read-only 단말 probe (device-gated).
> source spec = [../specs/2026-06-05-menu-tree-v1_2-tc-anchor-design.md](../specs/2026-06-05-menu-tree-v1_2-tc-anchor-design.md).
> §2.3 source-of-truth 준수(정의→코드→테스트 동일 PR). 본 plan 은 spec 을 실행 task 로 분해만 한다.

## 계획 원칙 (전 task 공통 불변)
1. **near-term consumer = issue-probe** (BUG/BTS/phone-settings 재현 좌표). 코퍼스 70 대량 자동화 아님.
2. `src/menu_tree.py`(schema_version=1 `MenuTreeBaseline`) **무변경**, **sidecar-first**. 레이어링: `menu_tree` → `scripts.menu_mapper` import 금지.
3. **Task 1·2 = 단말 불요 순수 TDD** (RED→GREEN, pytest). Task 3·5·6(설계)도 단말 불요.
4. DebugScreen/APN **실기 확인은 Task 4 단일 승인 게이트**로 뒤에 배치 — 앞단이 외부 조건에 묶이지 않게.
5. **DebugScreen 접근 실패 = plan 실패 아님** → Tier 재분류(A/B/C 또는 IssueProbePoint)로 흡수.
6. APN = **read-only 관찰(Tier A/B)** 와 **편집/저장(Tier C)** 분리.
7. SeniorShield = **reference-only**, package baseline 착수 안 함(O4).

## 신규 코드 배치 (제안)
- `src/menu_anchor.py` (신규, 순수): `ActionSafety` enum + `TCAnchorMapping`/`IssueProbePoint` dataclass + emitter/parser.
  - import 방향 = **src→src 만**. `menu_tree`(읽기) 가능.
  - **`mmi_converter.models` 직접 import 금지(수정 #1)** — `ActionSafety ↔ AutomationClass` 매핑은 **문자열/adapter 기반**. 실제 `AutomationClass` enum 은 **정합 test 에서만 import**.
  - `scripts.*` 역의존 금지(레이어링 회귀 test 1건).
- sidecar 산출: `THOR2_K - Settings/catalog/{anchors,probes}/` (Task 에서 생성).

---

## Task 1 — `ActionSafety` derive (순수)
- **목적**: step/element(`kind`·`risk`·**shell command**)에서 물리 안전성 enum 파생(spec §4.2). 위험 1급 대상 = shell.
- **변경 파일 후보**: `src/menu_anchor.py`(신규 `ActionSafety` + `derive_action_safety()`), `tests/test_menu_anchor_safety.py`(신규).
- **ActionSafety enum (수정 #2 — 명확 분리)**:

  | 값 | 트리거 | 비고 |
  |---|---|---|
  | `READ_ONLY` | dump/verify(read)/getprop 류 비-shell 관찰 | |
  | `READ_ONLY_SHELL` | **`getprop` / `dumpsys` / `logcat -d` / `uiautomator dump` / `cat /sdcard`** | read-only shell — 아래 위험 shell 과 **분리** |
  | `NAVIGATION_ONLY` | DPAD/HOME/BACK/swipe, `am start`(진입) | read-only 아님 |
  | `SELECTION_GATED` | ENTER/CENTER/tap | screen-scoped allowlist 있을 때만 |
  | `INPUT_REQUIRED` | EditText(`_INPUT_CLASSES`)/`input_text` | |
  | `DESTRUCTIVE` | **`settings put` / `svc` / `reboot` / `content delete`** | 상태 변경·되돌림 위험 |
  | `PRIVILEGED_SHELL` | **`pm grant/revoke` / 권한·시스템 shell** | 권한 상승 계열 |
  | `UNKNOWN_UNSAFE` | **분류 불가 shell/action** | **보수적 = unsafe 취급**(자동 실행 금지) |

  - read-only shell(`getprop/dumpsys/logcat`)과 위험 shell(`settings put/svc/reboot/pm grant`)을 **같은 enum 으로 묶지 않는다**.
  - **unknown shell = `UNKNOWN_UNSAFE`** (보수적). default 는 항상 더 위험한 쪽.
- **테스트 방식**: 위 표를 케이스 테이블로. **RED 먼저** — 8개 값 각 1+행, 특히 read-only shell vs 위험 shell 분기·unknown→`UNKNOWN_UNSAFE` 검증.
- **승인 게이트**: 코드 신규 → **구현 착수 승인 필요**(§2.1). 단말 없음.
- **성공 기준**: spec §4.2 + 수정 #2 트리거가 결정적 매핑, 모호 입력은 명시 default(보수). pytest GREEN.
- **non-goals**: AutomationClass 매핑(§4.3 은 별도 adapter), 자동 실행, mmi `_AUTO_ACTIONS`(`src/mmi_converter/step_classifier.py`) 수정.

## Task 2 — `TCAnchorMapping` sidecar (순수, **2단계 분리**)
- **목적**: TC yaml 의 `am start -a <action>`/`-n <pkg/comp>` 를 1차 key 로 anchor 산출(spec §4.1). expected↔observed 분리·`source` 보존.
- **처리 2단계 (수정 #3 — expected/observed 혼용 금지)**:
  - `extract_anchor_candidate(tc_yaml)` → **`source_expected_texts` 까지만**. 산출: `tc_file`, `entry_action`(원문), `domain`, `match_method∈{deeplink,component,text}`, `source_expected_texts={source∈{mmi,figma,tc_yaml}, texts:[]}`. (`screen_id`/`confidence`/observed 는 **아직 비움**)
  - `join_anchor_to_baseline(candidate, baseline)` → baseline join 후 **`device_observed_texts`·`screen_id`(null 허용)·`match_confidence`(deeplink=high/text=low) 보강**.
  - emitter 가 observed 를 **직접 만들지 않음**(baseline join 이후 값).
- **변경 파일 후보**: `src/menu_anchor.py`(`TCAnchorMapping` dataclass + `extract_anchor_candidate()`/`join_anchor_to_baseline()`/`load_anchor()`), `tests/test_menu_anchor_mapping.py`, fixture `tests/fixtures/anchor/*.yaml` + golden `*.json`.
- **ActionSafety ↔ AutomationClass adapter (수정 #1)**: `menu_anchor` 내 **문자열 매핑 함수**로 노출(아래), `AutomationClass` enum 은 import 안 함.

  | ActionSafety | AutomationClass(문자열) |
  |---|---|
  | `READ_ONLY` / `READ_ONLY_SHELL` | `FULL_AUTO` |
  | `NAVIGATION_ONLY` | `SEMI_AUTO` 후보 |
  | `SELECTION_GATED` | `SEMI_AUTO`(allowlist) / else `MANUAL_REQUIRED` |
  | `INPUT_REQUIRED` | `MANUAL_REQUIRED` |
  | `DESTRUCTIVE` / `PRIVILEGED_SHELL` | `MANUAL_REQUIRED` / guided |
  | `UNKNOWN_UNSAFE` | `MANUAL_REQUIRED`(보수) |

  - **정합 test 에서만** `from src.mmi_converter.models import AutomationClass` 하여 문자열 ↔ enum 이름 일치 단언(legacy `_AUTO_ACTIONS` 와 별개 명시).
- **테스트 방식**: fixture TC(deeplink/component/text 각 1) → `extract` → candidate roundtrip → `join` → 보강 필드 검증. `screen_id` null 허용·text 매핑 low-confidence+ambiguous flag.
- **승인 게이트**: 구현 착수 승인. 단말 없음.
- **성공 기준**: 정의(sidecar json schema)→코드→test 동일 PR(§2.3). expected/observed 2단계 분리 불변.
- **non-goals**: schema_version=2 bump(O3), `MenuTreeBaseline` 변경, 실기 observed 신규 수집(기존 baseline 재사용).

## Task 3 — 코퍼스 anchor 추출 audit fixture화 (read-only)
- **목적**: Task 2 emitter 를 실제 코퍼스에 돌려 P1 anchor 후보·매핑 현실을 **재현 가능한 golden** 으로 고정(2026-06-05 audit 재현).
- **코퍼스 수치 (수정 #4 — 분해+합산 둘 다 기록)**:
  - `exported_tc1` **44 = top-level 25 + `_autoconverted` 19**.
  - `exported_ss_call` 16, `golden_tc_set` 3.
  - audit golden 에 **분해 수치(25/19)와 합산(44) 모두** 기록 → 추후 회귀 golden 안정.
- **변경 파일 후보**: `scripts/anchor_corpus_audit.py`(신규, read-only CLI), `tests/test_anchor_corpus_audit.py`, golden `tests/fixtures/anchor/corpus_audit_baseline.json`.
- **테스트 방식**: 위 코퍼스 대상 emitter 집계 → (deeplink/component/text 분포, 현 17-screen baseline 매핑 수, domain 분포, 25/19/44 분해) golden 대조. drift 시 fail(원칙 1·2 회귀 가드).
- **승인 게이트**: 스크립트 신규 = 구현 승인. **단말 없음**(파일 read 만).
- **성공 기준**: audit 수치가 spec §0/§2 가정(SeniorShield 39 / Settings deep-link 4 / 현 baseline 매핑 2~3)과 정합, 이탈 시 명시 노출. 코퍼스 분해 수치 golden 고정.
- **non-goals**: TC 수정, 자동 실행, 커버리지 확대.

## Task 4 — APN/DebugScreen 접근성 probe + 단말 승인 게이트
- **목적**: P1 1차 anchor(APN+DebugScreen) **deep-link 가능 여부·권한 게이트를 read-only 로 확인**하고 Tier 판정(spec §2 NOTE, I1).
- **PRECONDITION (수정 #5 — sub-gate 아님, 선결):**
  - 단말 probe **이전에** redaction 후보 필드·raw carry 정책을 **먼저 확정**.
  - redaction 후보 = **IMSI / IMSI-like, MSISDN, ICCID, operator numeric(MCC/MNC), APN credential 후보(user/password/auth)**.
  - **raw XML = local carry 유지(미커밋)**, **digest/ledger 만 commit 후보**.
  - precondition 미확정 시 Task 4 단말 진입 금지.
- **변경 파일 후보**: `scripts/anchor_access_probe.py`(신규, `GuardedADB` 확장 read-only: `am start` dry-run / `cmd package resolve-activity` / `dumpsys`), ledger `THOR2_K - Settings/catalog/MENU_TREE_RUNS.md`(append), digest `catalog/anchors/access_probe_<run_id>.{json,md}`.
- **테스트 방식**: `GuardedADB` allowlist 단위테스트(승인 전, 단말 없이) → 실기 probe 는 **`-s B06201249E0002F0` 고정, B27(`B2700125BW000083`) 미접촉**. raw=local carry / digest+ledger=commit 후보.
- **승인 게이트**: **YES — 단말 호출 + 코드. 명시 승인 필요**(plan 의 첫 단말 게이트). redaction precondition 확정이 선결.
- **성공 기준 (재정의):**
  - APN + `device_info`(비교 기준)로 **sidecar 흐름(anchor emit→Tier 판정→ledger) 닫힘 검증**.
  - **DebugScreen 은 접근 결과에 따라 Tier A/B/C 또는 IssueProbePoint 로 재분류** — 접근 불가도 정상 산출물(실패 아님, 원칙 5).
  - ("APN+DebugScreen 둘 다 Tier A" 는 성공 기준 **아님**.)
- **non-goals**: APN 편집/저장(Tier C, 자동 실행 금지·원칙 6), DebugScreen 강제 진입, 2차 후보(WWAN/USB/SIM/Network).

## Task 5 — `IssueProbePoint` sidecar + ledger linkage
- **목적**: 이슈 재현 좌표(screen_id+상태+관찰항목) 정형화(spec §4.5). **1호 = 2026-06-05 privacy settle-probe(20 trial)** 백필.
- **변경 파일 후보**: `src/menu_anchor.py`(`IssueProbePoint` + emit/load), `catalog/probes/<issue_id>_<run_id>.json`, `THOR2_K - Settings/catalog/MENU_TREE_RUNS.md`(probe linkage 행), `tests/test_issue_probe_point.py`.
- **테스트 방식**: privacy 기존 데이터로 fixture → probe json roundtrip + ledger 링크 파싱 test. **단말 불요**(기존 evidence 재사용).
- **승인 게이트**: 코드 신규 = 구현 승인. 단말 없음.
- **성공 기준**: privacy probe 가 sidecar 로 표현되고 ledger run_id 와 양방향 링크. schema v1 무변경.
- **non-goals**: 신규 probe 단말 수집, FocusGraph 전수(§4.4 조건부).

## Task 6 — `failure_reason` attachment 설계
- **목적**: TC 실패를 좌표로 분류 부착(spec §7): `failed_screen_id·expected_nav_path·observed_focus·closest_menu_node·failure_reason`.
- **변경 파일 후보(설계 대상)**: `src/reporter.py`/`summary.json results[].steps[]` 확장 후보, `menu_tree` reach 결과 연동 후보, `src/menu_anchor.py`(`failure_reason` enum). **이번 task 는 설계+test 스캐폴딩, runner 통합은 별도 게이트.**
- **테스트 방식**: `failure_reason∈{unreachable,focus_mismatch,text_missing,risky_action,input_required,document_drift}` 매핑 단위테스트. `text_missing` = `source_expected_texts` vs `device_observed_texts` 비교 함수 test(2단계 분리 산출물 사용). `closest_menu_node`(I3) = 알고리즘 미확정 → **인터페이스 stub + xfail test**.
- **승인 게이트**: 설계 무게 낮음, **runner 통합 착수는 별도 승인**.
- **성공 기준**: 6개 reason 결정적, I3 미해결 명시(stub), reporter schema↔코드↔test 정합 경로 제시.
- **non-goals**: I3 알고리즘 확정, 자동 실행, summary 스키마 bump 강행.

## Task 7 — docs / self-review / batch commit gate
- **목적**: spec status 갱신 + 산출물 digest 정리 + GREEN baseline 보존 후 batch commit/push.
- **변경 파일 후보**: spec(status 줄), 신규 `docs/...` self-review 노트(선택), `catalog/anchors|probes/*.{json,md}` digest, `MENU_TREE_RUNS.md`. raw XML = 미커밋 carry.
- **테스트 방식**: full pytest GREEN + `validate_tc.py`(해당 시) + `tools/git_safe_push_audit.py`(forbidden-path/ff).
- **승인 게이트**: **YES — commit/push 항상 명시 승인(§7), 명시 path stage 만, broad add 금지.**
- **성공 기준**: 정의→코드→test 동일 PR drift 0, push audit PASS(ff-only).
- **non-goals**: 임의 checkpoint commit, raw XML 커밋, force push.

---

## 의존·순서
`1 → 2 → 3`(3은 2 emitter 사용) → **4(단말 게이트, redaction precondition 선결)** / `5`는 2 이후 독립 병행 / `6`은 2·5 이후 / `7` 최종.
단말 없이 진행 = **Task 1·2·3·5·6(설계)**. 단말 게이트 = **Task 4**(+ Task 6 runner 통합 시).

## open issue 연동
- **I1**(DebugScreen 접근성) → Task 4 read-only 판정, 실패는 재분류로 흡수(원칙 5).
- **I2**(APN 민감정보 redaction) → **Task 4 precondition 으로 승격(수정 #5)**. IMSI/IMSI-like·MSISDN·ICCID·operator numeric·APN credential 후보 마스킹 + raw carry 선결.
- **I3**(`closest_menu_node` 알고리즘) → Task 6 stub+xfail, 별도 확정.
- **I4**(SeniorShield package-track 트리거) → 전 task non-goal 유지(O4).

## 리스크
- Task 4 가 유일한 단말 의존점 → I1/I2 선결 없이 진입 금지(원칙 4 실현).
- `src/menu_anchor.py` 레이어링 = `mmi_converter.models` **직접 import 금지**, 문자열 adapter + test-only import(수정 #1). 회귀 test 1건으로 import 방향 가드.
- shell safety enum 분리(수정 #2): read-only shell ↔ 위험 shell 혼입 방지가 이후 분류 정확도의 핵심.

---

## 실행 로그 (execution log, 2026-06-05)
| Task | 상태 | 커밋 / 비고 |
|---|---|---|
| 1 ActionSafety derive (+ manual_pause) | **done** | `78279a4` (manual_pause → `SELECTION_GATED`) |
| 2 TCAnchorMapping extract/join + adapter | **done** | `78279a4` (expected/observed 분리, deeplink 0.9 / settings-comp 0.8 / 미매칭 0.3) |
| 3 corpus anchor audit + golden | **done** | `78279a4` (SeniorShield 39 / baseline 직접매핑 2 / APN gap / DEVICE_INFO method-mismatch gap) |
| 4 APN/DebugScreen accessibility probe | **partial** | I1 DebugScreen 접근성 = **DONE** (`d9a3809` Tier A access probe, F0 REACHED·87 dump nodes) · I2 APN redaction 필드 lock = **DONE** (redaction_gate.py). **잔여 = APN read-only 단말 probe (device-gated)** |
| 5 IssueProbePoint + privacy 1호 | **done** | `cffa61c` (ledger 요약값만, raw bundle 미의존) |
| 6 failure_reason 분류 | **done** | `cffa61c` (`no_device_observation` ↔ `text_missing` 분리, closest_menu_node=stub) |
| 7 docs/self-review/commit gate | **done** | 본 커밋 |

- 테스트: full suite **617 passed**. menu_anchor 무단말 신규 테스트 = safety 68 + mapping 24 + audit 8 + probe 8 + failure 24.
- non-goals 준수: 단말 호출 0 · schema_version=2 bump 0 · runner/reporter 통합 0 · catalog/{anchors,probes} 실파일 생성 0(test fixture/tmp_path만).

## self-review (Task 7)
- **near-term consumer = issue-probe** 유지 — corpus audit가 Settings 직접 매핑 LOW(2)를 정량 증거화.
- **SeniorShield = reference-only** 유지 — `app:<pkg>` 도메인 39건, baseline/anchor 우선순위 미승격.
- **expected(source) ↔ observed(device) 분리** 유지 — extract는 `source_expected_texts`까지만, join에서 `device_observed_texts` 보강.
- **`no_device_observation` ↔ `text_missing` 분리** — "baseline 부재"와 "텍스트 누락"을 issue-probe 판정에서 가름.
- raw/probe/catalog 실 sidecar는 **아직 미생성**(`--out`/`write_*` 준비만) — repo sidecar 쓰기는 후반 승인 게이트.
- **다음 게이트**: I2 APN redaction 필드 lock = **DONE**(redaction_gate.py) · I1 DebugScreen 접근성 read-only 확인 = **DONE**(2026-06-08 `d9a3809` Tier A access probe). **잔여 = APN read-only 단말 probe (device-gated)** — 단말 승인 후 별도 트랙.
