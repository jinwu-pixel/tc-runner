# TASK 5 실행 지시서 — CLI pre-device gate + fail-closed abort + reporter v2 (Codex 실행용)

역할: **Codex = 실행 / Claude = 계획·검증**. 사용자 착수 승인 2026-07-21.
설계 SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md` §8.1·§8.2·§8.4·§10 Task 5.
Baseline: HEAD `742445a` = origin/master · pytest tests/ **1261 passed** · **matrix `16ee5ae8ca8f55c4` FROZEN** (Claude 재검증 2026-07-21).

불변 규칙: TDD 엄수(RED 실패 관찰) / commit·push·staging 금지 / **본 Task 전 과정 device 명령 0** (설계 cycle:881) / legacy 행동 무변경 / 실측만 보고.

## 파일 경계 (설계 §10 Task 5 — 이 4개 + 지정 예외 외 수정 금지)

- Modify: `src/cli.py` · `tests/test_cli.py` · `src/reporter.py` · `tests/test_reporter.py`
- **kernel 불변 잠금**: action_runner/adb/tc_loader/execution_contract/producers/ledger/schema 무수정.
  검증 게이트: Task 종료 시 ledger 1회 실행 → **digest가 여전히 `16ee5ae8ca8f55c4`** 이어야 함
  (cli/reporter는 ledger actor가 아니므로 digest 불변 = kernel 무접촉의 기계 증명. 재산출·FIXTURE_VERSION bump 금지).

## Step 1 — CLI flag (§8.1)

- `cli run`에 `--contract-mode {legacy,canonical}` 추가, default `legacy`, argparse `choices` 거부 (unknown mode = argparse 에러).
- RED: `test_run_contract_mode_defaults_to_legacy` · `test_run_accepts_canonical_contract_mode`

## Step 2 — cmd_run 위상 분리 + pre-device host gate (§8.2)

현재 `cmd_run`은 진입 즉시 `adb = ADB()` 생성(`src/cli.py:141`). 이를 **host preflight 위상 / device 실행 위상**으로 분리한다.

- host preflight를 **importable 함수**로 구현 (예: `host_preflight(tc_files, contract_mode) -> PreflightReport`) — Step 5의 corpus 측정과 테스트가 직접 호출할 수 있어야 함 (subprocess·ADB 불요).
- canonical mode: 모든 TC 파일을 resolve → `load_tc(..., contract_mode="canonical")` → canonical 검증을 **ADB 생성·device 호출 이전에** 완료. 다음 중 하나라도 있으면 전체 invocation 비정상 종료(§8.2 — 8조건):
  canonical/schema 오류 · `metadata.runnable is not True` · 비어있지 않은 `runnable_reason` · `has_unresolved_params: true` · `compile_status == UNRESOLVED_PARAMS` · 비어있지 않은 `_unresolved_params` · 미해결 shell placeholder · alias conflict/invalid unit.
- **부분 실행 금지**: 한 파일이라도 blocking이면 유효한 나머지도 실행하지 않는다 (부분 device mutation 방지).
- legacy mode: 현행 경로 그대로 (gate 미적용).
- RED: `test_canonical_preflight_rejects_runnable_false_before_adb_constructed` · `test_canonical_preflight_rejects_unresolved_before_adb_constructed` · `test_one_invalid_file_prevents_all_valid_files_from_running`
  — "ADB 미생성" 검증 기법: `src.cli.ADB`를 monkeypatch로 기록/raise 하여 gate 실패 시 생성 호출 0 단언.

## Step 3 — canonical fail-closed abort (§8.4)

canonical mode 실행 위상의 단일 규칙:
1. **모든 action에서** 첫 실패 step → 현재 TC 즉시 중단 (verify 계열 한정 아님)
2. 잔여 TC 미시작
3. 추측성 자동 cleanup step 주입 금지
4. reporter가 partial 결과를 `ABORTED_FAIL_CLOSED` 컨텍스트로 기록
5. process 비정상 종료 (non-zero)

legacy mode: 현행 verifier-only break(`src/cli.py:193-194` — verify 실패 시 해당 TC만 중단, 다음 TC 계속) **원문 보존**.

- RED: `test_canonical_nonverifier_failure_stops_remaining_steps_and_tcs` · `test_canonical_failed_run_returns_nonzero_and_writes_partial_summary` · `test_legacy_verifier_only_break_policy_is_unchanged`

## Step 4 — reporter summary v2 (§8.4 후단)

- `src/reporter.py:13` `SUMMARY_SCHEMA_VERSION = 1 → 2`.
- 모든 bundle의 `summary.json` top-level에 `contract_mode`(`legacy`|`canonical`)와 `run_status`(`COMPLETED`|`ABORTED_FAIL_CLOSED`) **항상** 기록 — legacy run도 포함 (조건부 fallback 금지 = 설계 §8.1 "required reporter contract change").
- canonical abort 시 partial TC/step 결과만 있어도 `run_status: ABORTED_FAIL_CLOSED`로 **반드시 persist**.
- v1을 단언하는 기존 reader/테스트는 **같은 slice에서** 갱신. version bump 없는 silent 필드 추가 금지.
- RED: `test_summary_schema_version_two_records_contract_mode` · `test_aborted_fail_closed_is_serialized_in_partial_summary` · `test_report_records_contract_mode_and_abort_context`
- **cross-repo note (조치 금지·보고만)**: 형제 repo `qa-suite/contracts/run-bundle/summary_schema_v1.json`은 자체 reporter의 v1 계약(`"schema_version": {"const": 1}`)을 고정 — tc-runner v2 전환의 qa-suite 측 계약 갱신은 별도 트랙·별도 승인 (cross-commit 금지). 완료 보고에 영향 범위 1줄 명시.

## Step 5 — host canonical corpus 측정 (device 0)

Step 2의 importable preflight 함수로 golden 3 + exported_tc1 25 + THOR2_J 2를 직접 측정 (CLI full-run 금지 — gate 통과 파일이 device 위상으로 진입하면 안 됨):

- 파일별 gate verdict 표 보고 (PASS / 거부 사유).
- 수용 기준: canonical/schema 오류 **0** · 거부는 **선언된** `runnable:false`/unresolved 사유에 한함 (해당 파일 수 실측 보고 — 전 파일 gate-PASS를 요구하지 않음).
- 이 측정을 테스트로 영속화 (§2.4): corpus 대상 gate verdict가 선언 metadata와 일치함을 단언.

## Step 6 — 종합 게이트 + STOP

1. `pytest tests/test_cli.py tests/test_reporter.py -q` → 전체 `pytest tests/ -q -p no:cacheprovider` green (baseline 1261 + 신규)
2. ledger 1회 실행 → digest `16ee5ae8ca8f55c4` 불변 확인 (변했으면 kernel 오염 = 즉시 STOP·보고)
3. `tools/untracked_contamination_scan.py` 0 · `git diff --name-only` = 본 지시서 4파일 + 기존 contract set (THOR2_J 사용자 트랙 3+1·`AGENTS.md` 접촉·포함 금지)
4. **STOP** — Task 6/7·producer promotion(실 워크북 대기)·commit 미착수. 완료 보고: 변경 파일 sha256 / 테스트 수치 / corpus gate 측정표 / digest 불변 확인 / git 상태.

## Deferred (변동 없음 — 건드리지 말 것)

'수신자' 류 합성어 마커 잔여 · canonical `_shell` timeout 필드 미지원(schema 정합) · loader mode guard I/O 후 실행 · loader schema 재로드 · `SWIPE_ENDPOINT_MISSING` 네이밍 · 비문자열 step key sorted() crash · WEAK_VERIFY_TEXT 잔재 · STAGE1 tc_class 매핑 갭 · STAGE2 내부 action-list 잔재 · top-level additionalProperties validator 미집행 · Excel all-or-nothing granularity.

## 커밋 결합 규칙 (사용자 "commit now" 시 — 지금 실행 금지)

contract slice = Task 2+3+R1+4 21파일 + 본 Task 4파일(cli/reporter+테스트) 한 커밋 exact-path.
사용자 트랙(`THOR2_J_missed_call_issue/` 3+1)·`AGENTS.md`·`HANDOFF_*` 초안은 별도 처리(사용자 결정).
