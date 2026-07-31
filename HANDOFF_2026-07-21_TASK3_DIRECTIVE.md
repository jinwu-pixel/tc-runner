# TASK 3 실행 지시서 — loader·Excel/MMI producer canonical mode (Codex 실행용)

역할 분담: **Codex = 실행 / Claude = 계획·검증·freeze 게이트** (사용자 확정 2026-07-21).
본 지시서는 Claude가 작성한 실행 계획이며, Codex는 본 문서 + 설계서 원문만으로 실행한다.

- 설계 SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md` §7.2·§7.3·§10 Task 3
- Baseline: HEAD `742445a` = origin/master (0/0) · pytest tests/ **1212 passed** · matrix digest `95750a5a3220bc77` (CSV `d82e0277…`, SUMMARY `2b8509a9…`)
- Freeze 기록: Task 2 matrix = **FREEZE READY** (Claude 패널 3종 ACCEPT_WITH_NOTES, Critical 0 / Important 1). Important 1건은 아래 Step 0으로 본 Task에 편성.

---

## 0. 불변 규칙 (모든 Step 공통)

- TDD 엄수: RED 작성 → 실패 관찰 → 최소 구현 → GREEN → 다음. 실패 관찰 없는 테스트 금지.
- **commit / push / staging 금지** (사용자 "commit now" 전까지). broad add 영구 금지.
- 단말 불요 — 전 과정 host-only. subprocess/adb 실호출 금지 (fake·tmp_path만).
- legacy 기본값 유지: 모든 canonical mode는 opt-in. legacy 경로 byte/행동 무변경.
- 산출물·수치는 실측만 보고 (§2.2 PASS 4종 어휘, planned를 implemented로 표기 금지).

## Step 0 — semantic-delta 영속화 (freeze Important 해소, 선행)

- `tests/test_execution_contract.py`에 corpus 30파일(golden 3 + exported_tc1 25 + THOR2_J SMOKE 2) 회귀 테스트 1개 추가:
  `test_corpus_normalization_is_identity` — 각 파일에 대해 `normalize_tc(doc).value == doc` AND `blocking == False`.
- 성격 = 검증된 기존 사실의 회귀 잠금(characterization). 즉시 PASS가 정상이며, 구현 변경 금지.
- 근거: 리뷰 Important "FILES=30 SEMANTIC_DELTA=0 산출 도구 부재" (§2.4 evidence accumulation + 설계 Task 6/7 recorded acceptance).

## Step 1 — loader canonical mode (설계 §7.2:457)

파일: `src/tc_loader.py`, `tests/test_tc_loader.py`

- `load_tc`에 `contract_mode: Literal["legacy", "canonical"] = "legacy"` 추가.
- canonical: `src.execution_contract.normalize_tc` + `validate_canonical_tc` 경유,
  `tc_name` 반환(중복 `name` 키 미생성), blocking finding 시 로드 거부(TCValidationError, finding code 포함).
- legacy: 현행 byte/행동 완전 동일 (기존 shim 포함 무변경).
- RED (설계 명명 그대로): `test_canonical_loader_returns_tc_name_without_name_duplicate` ·
  `test_canonical_loader_rejects_alias_conflict` · `test_legacy_loader_behavior_is_unchanged`
- 게이트: `venv/Scripts/python.exe -m pytest tests/test_tc_loader.py -q`

## Step 2 — Excel producer canonical mode (설계 §7.3)

파일: `src/excel_converter.py`, `tests/test_excel_converter.py`

- canonical 변환 모드 추가 (legacy 기본값 유지): `tc_name` + canonical step 필드(`target`/`duration`/`key`/`x·y·x2·y2`) + 명시 supplied metadata emit.
- swipe canonical 입력 인코딩 = `Parameter1="x,y"` + `Parameter2="x2,y2"` (각각 정수 2개).
  scalar legacy 시작좌표만 있고 endpoint 없으면 `SWIPE_ENDPOINT_MISSING` finding + **runnable TC 미기록**.
  `Expected` 컬럼을 endpoint 저장소로 전용(轉用) 금지 (§7.3:469).
- RED: `test_canonical_excel_emits_target_duration_key_and_tc_name` · `test_canonical_excel_requires_explicit_metadata` ·
  `test_canonical_excel_swipe_requires_two_coordinate_pairs` · `test_legacy_excel_output_is_unchanged`
- 게이트: `venv/Scripts/python.exe -m pytest tests/test_excel_converter.py -q`

### ⚠ Step 2 STOP 게이트 — 실 워크북 대조 (§7.3:468, 설계 cycle:800)

canonical producer **promotion 선언 전**, 사용자 승인된 **실 워크북**의 swipe row를 read-only 대조
(path/sheet/row + redacted cell 값을 evidence로 기록). 2026-07-20 사전 감사 결과 적합 실표본 없음
(`tc_samples/TC_1.xlsx` swipe row 없음 · `ODIN T_C 메뉴트리.xlsx`는 자연어 본문뿐).
→ **합성 fixture로 대체했다고 주장하지 말고, canonical 모드 구현+테스트까지만 완료 후
"producer promotion STOP — 실표본 요청" 상태로 보고**할 것.

## Step 3 — MMI compiler/exporter canonical mode (설계 §7.3)

파일: `src/mmi_converter/compiler.py`, `src/mmi_converter/exporter.py`, `tests/test_mmi_compiler.py`, `tests/test_exporter.py`

- compiler canonical mode: `target`·`key`·`duration` emit (legacy `text/keycode/seconds` 경로 무변경).
- exporter canonical mode: top-level `tc_name` + canonical metadata 4필드
  (`runnable`/`tc_class`/`execution_type`/`manual_detail`) — STAGE2 Step 4 규칙으로 classified steps에서 파생 (§4.5:258, §7.3:475).
- unresolved 입력은 `runnable:false` + canonical `runnable_reason` 유지.
- `exported_at`은 evidence 목적 유지하되 결정론 대조에서 제외 (§7.3:476).
- **허용 확장**: Step 4 파생 로직의 공유 helper가 필요하면 `src/execution_contract.py`에
  **신규 함수 추가만** 허용 (기존 함수 시그니처·행동 무변경 + 전용 테스트 동반). 그 외 execution_contract 수정 금지.
- RED: `test_canonical_compiler_emits_target_key_duration` · `test_canonical_exporter_emits_required_metadata` ·
  `test_unresolved_mmi_export_is_not_runnable` · `test_legacy_mmi_output_is_unchanged`
- 게이트: `venv/Scripts/python.exe -m pytest tests/test_mmi_compiler.py tests/test_exporter.py -q`

## Step 4 — ledger 동반 갱신 + 재산출 (설계 cycle:805)

파일: `scripts/contract_drift_ledger.py`, `tests/test_contract_drift_ledger.py` (설계 파일 목록 외 — cycle:805 요건상 계획 승인된 동반 수정)

- canonical producer 경로 probe fixture 추가 (Excel canonical / MMI canonical → 4 consumer pair).
  canonical fixture는 clean(blocking 0), legacy fixture는 **계속 측정** (측정기 원칙 — baseline pin 금지 유지).
- `FIXTURE_VERSION` bump (→ 새 input digest 디렉토리 = 정상. 기존 `95750a5a…`는 Task 2 freeze 증거로 보존).
- 재산출 게이트: `--verify-determinism` exit 0 → 독립 2회 byte 동일(hash 기록) → `--fail-on-blocking` exit 1(legacy 결함 잔존 시 정상).

## Step 5 — 종합 검증 + STOP

1. `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` — 전체 green (baseline 1212 + 신규, 회귀 0)
2. corpus validate 재확인: golden 3 / exported 25 / THOR2_J 2 (legacy 경로 무변경 입증)
3. `venv/Scripts/python.exe tools/untracked_contamination_scan.py` — 오염 0
4. `git status --short` + `git diff --name-only` — 변경 파일이 본 지시서 파일 목록과 정확 일치하는지 대조 (외 파일 발견 시 즉시 중단·보고)
5. **STOP** — commit 금지, Task 4 미착수. 완료 보고 후 Claude 재검증·리뷰 대기.

## 스코프 가드 (건드리지 말 것)

- `src/action_runner.py` / `src/adb.py` — Task 4 영역 (shell 구조화·runner canonical)
- `tc_step_schema.json` / `tc_prompts/*` / `validate_tc.py` — Task 2 완료분, 본 Task 무수정
- 이연 목록 (Task 3 범위 아님·수정 금지): execution_contract 비문자열 step key sorted() TypeError(1줄 픽스 후속),
  WEAK_VERIFY_TEXT legacy 잔재(validate_tc.py:209), STAGE1 tc_class 매핑 갭, STAGE2 내부 action-list 잔재
- `stage2_output/**` 33파일 screenshot name FAIL 전환 = accepted strictness, 조치 금지

## 완료 보고 형식 (Codex → 사용자/Claude)

변경 파일 목록(지시서 대조) / 테스트 수치(모듈별 + 전체) / ledger rows·blocking 분해·신규 digest·CSV/SUMMARY hash /
실 워크북 게이트 상태(STOP — 표본 대기) / git 상태(staged 0·commit 0) / 잔여·이연 목록.

## 커밋 결합 규칙 (사용자 "commit now" 시점용 — 지금 실행 금지)

Task 2+3 slice는 **한 커밋**으로 exact-path 스테이징 (부분 커밋 시 master GATE 2 ImportError):
신규 `src/execution_contract.py`·`tests/test_execution_contract.py`·`scripts/contract_drift_ledger.py`·`tests/test_contract_drift_ledger.py`
+ 수정 `validate_tc.py`·`tc_step_schema.json`·`tc_prompts/STAGE2_COMPILE.md`·`tests/test_execution_type.py`·`tests/test_validate_lint.py`
+ Task 3 수정 8파일. `reports/`는 gitignored — 스테이징 대상 아님.
