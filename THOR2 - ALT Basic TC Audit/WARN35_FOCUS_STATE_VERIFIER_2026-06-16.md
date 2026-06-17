# batch10 WARN 35 — focus_state verifier 강화 (2026-06-16)

batch10 합성 gate가 WARN 35로 플래그한 "positive verifier 부재" draft 정합 정정. 무단말 prep 트랙 Stream 1.

## 진단

WARN 35건은 **전부 focus-state TC** (포커스 이동/미이동/생성/정지·"무반응 확인"). 텍스트 literal이 본질적으로 없는 종류인데 `verifier_type: verify_text` + 빈 `expected`로 합성됨 = **부정합**. enrichment 아닌 정합성 수정.

## 방법 (scope A — STAGE1 메타 설계노트만)

- `verifier_type: verify_text → focus_state` 정정 + `verifier_contract` 설계노트 삽입.
- **runner/validate_tc 스키마 무변경** (정식 focus 타입 도입은 STAGE2/runner 트랙으로 분리). step `expected([])`·`expected_texts_candidate([])` 무접촉.
- **발명 0**: `expectation`은 `expected_result_raw`에서 파생. 구체 selector는 **F0 dump 후** (`device_value: PENDING_F0`).
- 결정적 transform `scratch/warn35_focus_state_transform.py` (surgical 텍스트 치환, 주석/포맷 보존, 멱등). per-file +6/−1.

## verifier_contract 스키마

```yaml
verifier_type: focus_state
verifier_contract:
  assert: <7종>
  expectation: "<source 파생 기대>"
  method: "F0 dump 기반 focused=true 요소 채록·대조 절차"
  device_value: PENDING_F0
```

## assert 분류 (35)

| assert | n | 의미 | tc |
|---|---|---|---|
| focus_move | 20 | 방향 입력 후 focused 요소 이동 | BSC_038~045 · HDK_043/044/045/047/069 · MSG_069/070/071/072/077 · QPN_169/170 |
| focus_invariant | 6 | 경계/무효 입력 시 focused 불변(무반응) | HDK_095 · LCH_007/028/147 · MGN_010 · SST_009 |
| focus_boundary_stop | 3 | 이동 후 끝단 정지·비루프 | CALC_025/026 · CAL_335 |
| focus_retained | 3 | 팝업/back/OK 후 직전 focused 복귀·유지 | CNT_060 · LCH_155 · QPN_171 |
| focus_created | 1 | 초점 부재→입력 시 생성 | HDK_034 |
| focus_position | 1 | focused 요소가 특정 입력 필드 | CAL_355 |
| focus_absent | 1 | 진입 직후 focused 부재 | QPN_120 |

## gate — GREEN

- 271/271 parse · 35/35 contract OK(assert∈7종·device_value PENDING_F0·expectation/method 비공란).
- surgical: 35 files +210/−35 (per-file +6/−1, EOL churn 0).
- 비-WARN 236건 무접촉(focus_state 누출 0).

## F0 handoff

35건은 이제 **"WARN: verifier 없음"에서 "설계된 focus_state 계약"으로 승격** — 다음 F0 세션은 각 contract의 `method`대로 `focused=true` 요소의 resource-id·text·bounds를 캡처해 `device_value`를 채우면 됨. 텍스트 assert 불가가 명시돼 헛된 verify_text 시도 차단.

## non-goals / 상태

- runner/validate 스키마 변경 0 · selector 값 발명 0 · 단말 접촉 0.
- export_status는 STAGE1_DRAFT 유지 (validation_required=device_2run_green 불변).
- **commit 미실행** (글로벌 정책 — 하루 끝 batch·명시 승인).
