# R1(reconcile) + TASK 4 실행 지시서 — Codex 실행용

역할: **Codex = 실행 / Claude = 계획·검증** (2026-07-21 확정 체제).
설계 SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md` §8.3·§10 Task 4.
Baseline: HEAD `742445a` = origin/master · pytest tests/ **1240 passed** · **matrix `bb695f1728561ba7` FROZEN** (Claude 재검증 2026-07-21) · Task 2+3 commit-set 17파일 sha256 고정 기록 있음 (Claude freeze 보고 참조).

불변 규칙: TDD 엄수(RED 실패 관찰 필수) / commit·push·staging 금지 / host-only (단말·실 subprocess 금지) / legacy 경로 byte·행동 무변경 / 실측만 보고.

---

## Part A — R1: derive/validate execution_type reconcile (freeze Important 해소)

### A-0. 배경 (측정 확정 사실 — 재도출 불요)

- STAGE2 Step 4 SSOT(`tc_prompts/STAGE2_COMPILE.md:186-188`): EXTERNAL_EVENT 승격 조건 = execution_mode 또는 "description에 보조폰/수신/발신/상대 단말/외부 이벤트 **의존이 명시됨**".
- 현 `derive_execution_metadata`(`src/execution_contract.py:364-395`)는 **전체 step description에 bare-substring** 매칭 → 과대 발화 실측:
  `exported_tc1/BUG_5426_airplane_reboot_apn.yaml`의 **SHELL_AUTO** step "긴급호 118 **자동 발신**"(line 415, `am start -a ...CALL_EMERGENCY`)이 EXTERNAL로 오승격 (declared=MANUAL_LOCAL이 정답 — 자동화 step은 외부 '의존'이 아님).
- `validate_canonical_tc`의 일관성 검사(`:554-572`)는 execution_mode/manual_pause만 봄 → canonical MMI exporter에서 derive와 충돌 시 정상 TC export 거부 (fail-closed지만 기능 갭).
- 측정 현황: corpus30 mismatch 1(BUG_5426) / exported_ss_call 16 mismatch 0 / wide 134 중 1(untracked `stage2_output/.../SS-15`).

### A-1. derive 제한 (RED→GREEN)

description-marker 스캔을 **manual-routed step**(action `manual_pause` 또는 execution_mode `MANUAL_REQUIRED`/`EXTERNAL_EVENT`)의 description으로 한정하고, 비의존 합성어 오발화를 제거한다.

RED fixtures (최소):
1. SHELL_AUTO step, description "비행기 모드 중 긴급호 118 자동 발신" → **비승격** (BUG_5426 실사례)
2. manual_pause(MANUAL_REQUIRED), description "보조폰에서 전화 수신" → **EXTERNAL_EVENT**
3. manual_pause(MANUAL_REQUIRED), description "문자 수신함을 확인하세요" → **비승격** (MANUAL_LOCAL — '수신함'은 의존 아님)
4. execution_mode EXTERNAL_EVENT step → EXTERNAL_EVENT (기존 유지)
5. 기존 derive 테스트 6종은 규칙 변경에 맞게 조정 허용 (의미 약화 금지)

### A-2. validator 정렬 — 단일 규칙 공유 (RED→GREEN)

- `validate_canonical_tc`의 expected_exec_type 계산이 A-1과 **동일한 공유 helper**를 사용하도록 정렬 (규칙 구현 2개 금지 — §2.3).
- 완료 후 재측정 의무: **corpus30 mismatch 0 · ss_call16 mismatch 0** (하나라도 위반 시 즉시 STOP·보고).
  측정 스크립트 사양: 각 yaml에 대해 공유 helper 파생 execution_type vs metadata 선언값 비교 — Claude 스크래치패드 `derive_vs_metadata_scan.py`와 동일 로직을 **테스트로 영속화**할 것 (corpus30 대상, §2.4).
- untracked `stage2_output/` 전환은 accepted-strictness로 기록만 (조치 금지).

### A-3. 합성(composition) 테스트

exporter 경유 derive→validate 왕복 2건:
- marker manual TC (fixture 2 유형) → canonical export **성공**, metadata.execution_type=EXTERNAL_EVENT, validator 오류 0
- benign manual TC (fixture 3 유형) → canonical export **성공**, MANUAL_LOCAL 일관

### A-4. freeze minor 동반 해소 (3건)

1. non-runnable canonical export 시 억제되는 `validate_canonical_tc` 오류를 `metadata.warnings`에 기록 (무기록 폐기 금지, §2.4)
2. empty compiled_steps → `runnable:false` + `runnable_reason: ["MANUAL_FALLBACK"]` 부여 (reason 없는 runnable:false 금지)
3. canonical compiler `compile()` 전문서 경로 + `_canonicalize_steps` blocking-raise 경로 테스트 추가

### A-5. R1 게이트

`pytest tests/test_execution_contract.py tests/test_exporter.py tests/test_mmi_compiler.py -q` → 전체 `pytest tests/ -q` green (30파일 identity 테스트 포함) → ledger 재산출 (§Part C).

---

## Part B — Task 4: Structured shell result + runner canonical branch (설계 §8.3·§10 Task 4)

파일: `src/adb.py`·`tests/test_adb.py`·`src/action_runner.py`·`tests/test_action_runner.py` (이 4개 + ledger 2개 외 금지)

### B-1. ADB (RED→GREEN)

- `ShellResult` frozen dataclass: `command/stdout/stderr/returncode` + `ok` property (설계 §8.3 원문 그대로).
- `ADB.shell_result(command: str, *, timeout_s: float = 10.0) -> ShellResult` 신설. **기존 `shell() -> str` 시그니처·행동 무변경**.
- RED: `test_shell_result_preserves_returncode_and_stderr` (subprocess mock rc=1/stdout/stderr 보존) + `test_legacy_shell_still_returns_stdout`.
- 게이트: `pytest tests/test_adb.py -q`

### B-2. ActionRunner canonical branch (RED→GREEN)

- `ActionRunner(..., contract_mode: Literal["legacy","canonical"]="legacy")`.
- canonical에서만: `_shell`/`_verify_shell`이 `shell_result` 사용, **rc≠0 = step FAIL** (stdout에 expected 매칭돼도 FAIL — `test_canonical_verify_shell_does_not_pass_on_nonzero_stdout_match`); verify_shell `timeout` ms→s 변환 후 `timeout_s` 전달 (`test_verify_shell_converts_5000ms_to_5_seconds`); tap_id는 `target` 소비 (`test_canonical_runner_consumes_target_for_tap_id`); message에 bounded stdout/stderr+rc 포함.
- legacy 분기 byte·행동 무변경 (`test_legacy_shell_still_returns_stdout`·`test_legacy_runner_alias_tests_are_unchanged` — 기존 alias sentinel 테스트 무수정 green).
- 게이트: `pytest tests/test_action_runner.py -q`

### B-3. 스코프 금지

`src/cli.py`·`src/reporter.py`·pre-device gate·abort 정책 = **Task 5** (착수 금지). runner의 non-verifier 계속 진행 정책 변경도 Task 5.

---

## Part C — ledger 동반 갱신 + 재산출 (R1·T4 공통, 1회)

- runner **canonical mode consumer probe** 추가 (shell rc / verify_shell timeout / tap_id target fixtures를 contract_mode=canonical로도 probe).
- 기대 관찰 (측정 원칙 유지 — enforcement 금지, baseline 테스트만 갱신):
  legacy: `SHELL_RC_DISCARDED` observed 유지 / canonical: rc≠0 → FAIL 관찰 = **defect not observed (fixed candidate, canonical path)** · `TIMEOUT_MS_AS_SECONDS` canonical에서 해소 관찰 · `CANONICAL_REJECTED_BY_RUNNER`(tap_id) canonical에서 해소 관찰.
- `FIXTURE_VERSION` bump → 새 digest (기존 `bb695f17…`·`95750a5a…` 보존). R1의 execution_contract 변경으로 consumer 일부 행 변동 가능 — **Task3 대비 행 diff 요약** 보고 의무.
- 게이트: `--verify-determinism` exit 0 → 독립 2회 byte 동일(hash 기록) → `--fail-on-blocking` (legacy 결함 잔존 시 exit 1 = 정상).

## Part D — 종합 게이트 + STOP

1. 전체 `pytest tests/ -q -p no:cacheprovider` green (baseline 1240 + 신규)
2. corpus validate 30/30 + A-2 재측정 0/0
3. `tools/untracked_contamination_scan.py` 0
4. `git diff --name-only` = 본 지시서 파일 목록 정확 일치 (예외로 인정된 사용자 트랙: `THOR2_J_missed_call_issue/` 3+1 파일 — 접촉 금지·커밋 분리 유지. `AGENTS.md` 커밋 제외 유지)
5. **STOP** — Task 5·producer promotion(실 워크북 대기)·commit 전부 미착수. 완료 보고는 **R1 증거 블록 / T4 증거 블록 분리** + 변경 파일 sha256 목록 갱신.

## Deferred (건드리지 말 것 — 변동 없음)

loader mode guard I/O 후 실행 · loader schema 재로드 · `SWIPE_ENDPOINT_MISSING` 네이밍 · 비문자열 step key sorted() crash · WEAK_VERIFY_TEXT 잔재 · STAGE1 tc_class 매핑 갭 · STAGE2 내부 action-list 잔재 · top-level additionalProperties validator 미집행 · Excel all-or-nothing 배치 granularity.
