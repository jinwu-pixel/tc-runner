# TASK 6 + TASK 7(host) 실행 지시서 — 회귀·cutover 증거 + THOR2_J host differential (Codex 실행용)

역할: **Codex = 실행 / Claude = 계획·검증**. 사용자 착수 승인 2026-07-21 ("다음 작업 1,2").
설계 SSOT: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md` §9.1-9.2·§10 Task 6 (883-895)·Task 7 host (897-918)·§11 G2.
Baseline: HEAD `742445a` = origin/master · pytest tests/ **1287 passed** · matrix `16ee5ae8ca8f55c4` FROZEN (Task 5 재검증 2026-07-21).

불변 규칙: commit·push·staging 금지 / **device·adb 실호출 0** (§9.3 device 부분은 본 dispatch 범위 밖 — B27 가용 확인·serial-pinned 별도 사용자 승인 전 금지, 미실행은 `NOTE`) / TC 파일 편집·authoring 0 (§9.2:603) / kernel·구현 파일 무수정 (Task 6 원칙: "no new implementation file unless a failing test demonstrates a scoped defect" — 결함 발견 시 즉시 STOP·보고, 임의 수정 금지).

## 파일 경계

- Create 허용: `tests/test_thor2j_smoke_differential.py` (Task 7 host 테스트 전용 — 비교 helper도 이 모듈 내부에만)
- 그 외 일체 무수정. 종료 게이트: ledger digest **`16ee5ae8ca8f55c4` 불변** + 기존 파일 sha256 무변화.

## Part A — Task 6: 회귀·cutover 증거 취합

1. **Focused 모듈 전체 실행** (Task 1~5 산물 12개 모듈 한 번에):
   `venv/Scripts/python.exe -m pytest tests/test_contract_drift_ledger.py tests/test_execution_contract.py tests/test_validate_lint.py tests/test_execution_type.py tests/test_tc_loader.py tests/test_excel_converter.py tests/test_mmi_compiler.py tests/test_exporter.py tests/test_adb.py tests/test_action_runner.py tests/test_cli.py tests/test_reporter.py -q` — 모듈별 수치 기록.
2. **전체 회귀**: `pytest tests/ -q -p no:cacheprovider` — failures 0.
3. **원본 1120 nodeid 보존 증명** (설계 891): scratchpad에 `git worktree add --detach <scratchpad>/head_worktree 742445a` → 그 트리에서 `venv/Scripts/python.exe -m pytest tests/ --collect-only -q` nodeid 목록 수집 → 현 작업트리 collect-only 목록과 대조 → **HEAD nodeid 전부 현재 목록에 포함** + 신규만 추가임을 증명 → `git worktree remove` 정리. (worktree는 read-only 사본 — 그 안에서 어떤 편집·실행 산출물도 남기지 말 것. venv는 repo 루트 것 재사용.)
   HEAD collect가 선존 수집 오류 등으로 불가하면 우회하지 말고 실패 양상 그대로 보고.
4. **ledger 통합 실행**: `scripts/contract_drift_ledger.py --out-dir reports/contract_drift --verify-determinism --fail-on-blocking` — 기대: determinism self-check 통과 + 산출물 기록 + legacy blocking 12로 **exit 1** (정상). digest `16ee5ae8` 불변 확인.
5. **semantic delta 0 재확인**: `test_corpus_normalization_is_identity` + `test_primary_corpus_execution_type_matches_shared_derivation` green (2번에 포함되나 명시 기록).
6. **redaction 게이트**: commit-candidate 집합(코드 25파일 + 신규 테스트 1 + 최종 CSV/SUMMARY 2)에 대해 민감 토큰 스캔 — 최소 패턴: `01[016789]\d{7,8}` (전화번호), 실단말 serial (`B06201249E0002F0` 등 `[A-F0-9]{16}` 류 실측 serial), IMEI(15자리 연속 숫자). 스캔 방법·hit 0/목록 보고. (reports/는 gitignored — CSV/SUMMARY는 local-only 유지, 스캔은 유출 예방 기록 목적.)
7. Slice 1a/1b 증거 목록화: matrix 3세대 digest + 각 freeze 보고 참조를 표로 정리 (default flip 금지 — 증거 제출까지만).

## Part B — Task 7 host: THOR2_J SMOKE legacy↔canonical differential

대상 (read-only): `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml` · `SETTINGS_SMOKE_02_scroll_more_menu.yaml`

1. **역사 증거 확인** (신규 run 아님): `THOR2_J - Settings/RESUME.md`·`BUG_LOG.md`의 `runtime PASS 11/11`·`13/13` 기록 위치를 인용으로 채록 — 새 runtime 주장 금지.
2. **테스트 4종** (설계 명명 그대로, `tests/test_thor2j_smoke_differential.py`):
   - `test_contract_ledger_counts_existing_thor2j_smoke_two` — `scan_corpora()` thor2j 그룹 file_count 2
   - `test_thor2j_smoke_top_level_is_already_tc_name` — 두 파일 top-level `tc_name` (name 아님)
   - `test_thor2j_smoke_legacy_and_canonical_semantics_match` — legacy `load_tc` vs canonical `load_tc(contract_mode="canonical")` projection 비교: step 수·action 순서·command·selector(target)·unit 값·metadata projection 동일 (표시용 top-level key 차이는 canonical projection 후 비교, §9.2:600). 비교 helper는 테스트 모듈 내부 구현 — RED 관찰 가능 지점(헬퍼 부재/의도적 미구현)에서 TDD 사이클 준수, 순수 characterization 항목은 그 성격을 보고에 명시
   - `test_thor2j_smoke_source_hashes_unchanged` — 비교 수행 전후 두 파일 sha256+mtime_ns 불변
3. **canonical preflight 음성·양성**: `host_preflight` — J 2파일 canonical → gate PASS + `src.cli.ADB` monkeypatch로 **ADB 생성 0** 단언; 결함 주입 사본(임시 tmp_path 사본 — 원본 무접촉)으로 gate 거부 음성 케이스 1건.
4. **reporter v2 fixture**: J 파일명 기반 fixture로 `contract_mode`·`COMPLETED`/`ABORTED_FAIL_CLOSED` 직렬화 확인 (기존 Task 5 테스트 참조로 충분하면 중복 작성 금지 — 참조 명시).

## Part C — 종합 게이트 + STOP

1. 신규 테스트 포함 전체 `pytest tests/ -q -p no:cacheprovider` green (1287 + 신규)
2. ledger digest `16ee5ae8` 불변 + J 2파일 원본 hash/mtime 불변
3. `tools/untracked_contamination_scan.py` 0 · `git diff --name-only` 변화 = **0개** (본 Task는 tracked 수정 없음 — 신규 untracked 테스트 1개만)
4. **STOP** — 보고: Part A 증거표(모듈별 수치·nodeid 보존·redaction)·Part B differential 결과·git 상태. §9.3 device 부분은 `미실행(NOTE)` 처리. Task 7 device·THOR2_K·promotion·default flip·commit 전부 미착수.

## 보고 어휘 주의

host differential green ≠ `runtime PASS` (§9.2:605 — 주장 금지). 역사 기록은 "과거 근거 인용"으로만. 단말 미가용 = `NOTE`/`미실행`.

## 커밋 결합 규칙 갱신 (사용자 "commit now" 시)

contract slice = 25파일 + `tests/test_thor2j_smoke_differential.py` = **26파일** 한 커밋 exact-path.
사용자 트랙(`THOR2_J_missed_call_issue/` 3+1)·`AGENTS.md`·`HANDOFF_*` 초안 별도 처리 유지.
