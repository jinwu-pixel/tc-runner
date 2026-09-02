# BUG27084 Session B immutable handoff — fixed build 검증

## Session A bootstrap-only seal

- 기준 branch: `codex/bug27084-harness-provenance`
- source_digest_sha256: `850C00E08136D9AD1526EB769AB63AFA39FAC2CB28F0AC6720EB35C797935238`
- 실행 호환성 key: `harness_commit + source_digest_sha256`
- candidate commit OID는 commit 후 Session A 통합 보고에서 발행한다. OID를 이 commit 안에 자기참조로 넣지 않는다.
- Session A device work: 없음. ADB 호출·fixed build 설치·단말 mutation을 수행하지 않았다.
- known-bad evidence: 45개 legacy bundle, `EVIDENCE_LEDGER.json`에 manifest/tree digest 결박

위 source digest는 설계 문서 §17.1의 runtime 11개 exact-set에 대한 canonical Git blob bytes만 입력으로 사용한다. 테스트·문서·repository HEAD·절대경로·시간·환경값과 checkout EOL은 입력이 아니다. 이 Session A pair는 Session B 시작 checkout을 검증하는 bootstrap-only 기준이며 device campaign의 권위 pair가 아니다.

## Session B preparation commit과 campaign authority pair

아래 준비를 순서대로 마치기 전에는 ADB를 포함한 device phase를 시작하지 않는다.

1. Session A가 보고한 exact commit OID를 checkout하고 runtime harness scope가 clean이어야 한다. 현재 pair를 다시 계산해 이 문서의 Session A digest/OID와 비교하고 host test를 실행한다. 이 단계의 device 호출은 0이어야 한다.
2. fixed identity/profile을 `scripts/appwidget_stale_provider_profiles.py`에 추가하고 필요한 tests/docs를 정렬하는 단일 pre-device **Session B preparation commit**을 만든다. profile은 runtime exact-set에 포함되므로 이 commit이 pair를 바꾸는 것은 의도된 전환이다. 이 commit 전에는 known-bad/fixed evidence를 capture하지 않는다.
3. preparation commit 후 runtime scope가 clean한 상태에서 새 `harness_commit + source_digest_sha256`를 계산하고 Session B 보고에 OID와 digest를 발행한다. 이 pair B가 campaign authority pair 후보이다.
4. pair B에서 fresh known-bad root bundle을 먼저 capture해 **campaign authority pair**를 확정한다. fixed root bundle도 같은 pair B에서 fresh capture한다. 두 bundle의 `harness_provenance.json` pair가 같아야 하며 ledger entry의 pair와도 일치해야 한다.
5. Session A pair로 만든 bundle이나 과거 45개 legacy bundle은 pair B campaign의 일반 phase, child lineage, reset source 또는 비교 root로 사용하지 않는다. pair B 확정 후 harness-scope commit/dirty 변경이 생기면 기존 campaign은 restore-only로 종료하고 새 pair의 campaign을 시작한다.
6. 대상은 serial `B06201249E00030C`, model `AT-M140`이다. known-bad identity는 fingerprint `ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys`, incremental `RY07260901S`다.
7. fixed build `AT-M140Z0827U_DAILY_DEV_GMS_849`는 label만으로 신뢰하지 않는다. 실제 artifact SHA-256, fingerprint, incremental, Launcher version/code와 APK SHA-256을 read-only로 확보한다. 값은 추정하지 않는다.
8. ADB read-only 확인과 각 device mutation은 Session B에서 별도 사용자 승인을 받은 뒤 실행한다.

## 실행 경계

- 기존 45개 legacy bundle은 일반 phase, child capture, `reset-fixture`의 source로 사용하지 않는다. 단말 안전 restore만 가능하다.
- 새 known-bad/fixed bundle은 pair B의 동일한 provenance-enabled harness로 fresh capture한다. resume과 lineage는 repository HEAD가 아니라 source pair의 동일성을 검사한다.
- provider, lifecycle, 30초 관찰 창, 반복 수, target widget ID 규칙, Launcher-host binding count/hostId/provider drift를 known-bad와 fixed에서 맞춘다.
- stale precondition이 직접 확인되지 않은 fixed 미재현은 `runtime PASS`가 아니라 `runtime precondition FAIL`이다.
- fixed 판정은 HOME 렌더링, Launcher process 안정, line185→88 NPE 0건, 안전 placeholder 또는 stale record 정리, 정상 Weather·SimpleClock·Google Go 회귀를 함께 요구한다.
- mismatch/legacy/invalid-provenance restore는 먼저 evidence manifest를 검증하고 `restore_provenance_<attempt>.json`을 첫 device mutation 전에 기록한다. 이 상태들에서 `preserve_armed_state`를 사용하지 않는다.

## evidence ledger 절차

`EVIDENCE_LEDGER.json` schema v2는 `legacy_baseline.entries`와 `provenance_entries`를 분리한다. legacy baseline 45개는 manifest SHA와 `bundle_tree_sha256`까지 고정하며 수정하지 않는다. 새 bundle은 `provenance_entries`에 run ID, manifest SHA, tree SHA, harness commit, source digest를 추가한다. ledger 갱신 전에는 actual run ID union 불일치로 unledgered evidence가 실패해야 한다.

future provenance entry는 bundle의 sealed `harness_provenance.json` pair와 ledger pair를 교차검증한다. tree digest는 root `.run.lock`을 제외한 모든 regular file(`evidence_sha256.txt` 포함)을 POSIX 상대경로순으로 열거해 path/byte size/대문자 SHA-256 canonical JSON을 만들고, `ensure_ascii=false`, 정렬 key, 고정 separators, 마지막 LF를 적용한 UTF-8 bytes의 SHA-256을 기록한다. pending/tmp/symlink는 허용하지 않는다.

evidence root가 아예 없는 clean clone은 명시적 NOTE다. root가 존재하면 run 누락·추가·중복과 manifest SHA 불일치를 모두 실패로 처리한다.

## Session A host-only 검증 기록

- focused 명령: `python -m pytest tests\test_appwidget_stale_provider_repro.py tests\test_bug27084_evidence_contract.py -q`
- correction 후 focused 결과: `209 passed in 270.09s`, exit `0`
- correction RED 명령: `python -m pytest tests\test_bug27084_evidence_contract.py::test_bug27084_evidence_ledger_is_exact_and_locally_verified_when_present tests\test_bug27084_evidence_contract.py::test_appwidget_repro_test_has_no_same_block_unreachable_statements tests\test_bug27084_evidence_contract.py::test_bug27084_status_docs_pin_current_safe_state_and_session_b_gate tests\test_appwidget_stale_provider_repro.py::test_restore_current_inspection_failure_preserves_recorded_provenance tests\test_appwidget_stale_provider_repro.py::test_restore_records_legacy_and_current_unavailable_before_preflight -q`
- correction RED 결과: `5 failed, 1 passed`, exit `1`; failure node ID:
  - `tests/test_bug27084_evidence_contract.py::test_bug27084_evidence_ledger_is_exact_and_locally_verified_when_present`
  - `tests/test_bug27084_evidence_contract.py::test_appwidget_repro_test_has_no_same_block_unreachable_statements`
  - `tests/test_bug27084_evidence_contract.py::test_bug27084_status_docs_pin_current_safe_state_and_session_b_gate`
  - `tests/test_appwidget_stale_provider_repro.py::test_restore_current_inspection_failure_preserves_recorded_provenance[True]`
  - `tests/test_appwidget_stale_provider_repro.py::test_restore_records_legacy_and_current_unavailable_before_preflight`
- future manifest RED 명령: `python -m pytest tests\test_bug27084_evidence_contract.py::test_future_provenance_entry_rejects_manifest_that_does_not_seal_payload -q`; 결과 `1 failed`, exit `1`; failure node ID는 명령에 적힌 node와 같다.
- 전체 명령: `python -m pytest tests -q`
- 최신 격리 worktree 전체 결과: `1843 passed, 1 skipped, 3 failed in 924.54s`, exit `1`; 환경 failure node ID:
  - `tests/test_anchor_corpus_audit.py::test_corpus_file_counts_decomposed`
  - `tests/test_anchor_corpus_audit.py::test_audit_matches_golden_snapshot`
  - `tests/test_canonical_shell_rc_remediation.py::test_live_worktree_is_fully_remediated`
- 위 3건은 ignored `_autoconverted` 19개와 frozen inventory CSV가 격리 worktree에 없어서 발생했다. 코드 failure와 혼동하지 않으며, primary 통합 후 같은 전체 명령을 다시 실행하기 전에는 최종 전체 GREEN을 주장하지 않는다.

## 중단·복구 조건

- fixed artifact/fingerprint 불명, harness dirty/mismatch, manifest 불일치, lineage provenance 불일치, target identity 불일치 시 일반 실험을 중단한다.
- HOME role 또는 resumed activity/UI package가 불명확하면 `RESTORED_SAFE`를 선언하지 않는다.
- 실험 중단 시 새 mutation보다 안전 restore를 우선하고, restore provenance artifact와 잔존 mutation을 결과에 남긴다.
- 완료 후 `BUG_LOG.md`, `RESUME.md`, 새 RESULT, `EVIDENCE_LEDGER.json`을 같은 변경에서 정렬한다.
