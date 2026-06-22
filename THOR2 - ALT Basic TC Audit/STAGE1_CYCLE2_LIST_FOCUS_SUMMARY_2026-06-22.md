# Cycle2 — list-aware focus verifier 계약 (무단말, 2026-06-22)

F0 cycle1(2026-06-17) NOT_GREEN 5건(MSG_069/070/071/072/077)의 root cause = **R1 위음성**: list/scroll 화면은 컨테이너 자체가 `focused=true`·DPAD 시 불변, 이동은 자식 `selected=true` + scroll 델타로 표현. 무단말 scope A로 **R2 list-aware 계약**을 STAGE1 메타에 도입. (WARN35 패턴 미러: 스키마 무변경 / 단말 0 / selector 발명 0.)

## 설계 — `focus_model` 직교 필드

`verifier_contract` 에 `focus_model: node|list` 1축 추가(부재⇒node, back-compat). 7종 assert 불변 유지 → list 화면도 move/invariant/boundary_stop/retained 그대로 사용. assert별 `method` 를 selected 자식+scroll index 절차로 교체. 모호 화면은 `model_confidence: device_confirm`.

근거: 직교성(assert 곱집합) · runner 측정전략만 분기(assert PASS 어휘 공유) · idempotent transform 최소 diff. 상세 = `THOR2J_R2_LIST_FOCUS_HANDOFF_2026-06-22.md`.

## 변환 — 13건 (batch10 9 + batch11 4)

| 구분 | tc | assert | confidence |
|---|---|---|---|
| MSG(차단/스팸·설정 list) | MSG_069/070/071/072/077 | focus_move | strong (cycle1 단말 확정) |
| 설정 list | HDK_069(focus_move) · HDK_095/SST_009(focus_invariant) · CAL_335(focus_boundary_stop) | — | strong |
| 런처 앱메뉴 list (batch11) | LCH_014(focus_move) · LCH_015(focus_retained) | — | strong |
| 시계 탭 strip (batch11) | CLK_030/031 | focus_move | **device_confirm** (tab vs list 단말 확인) |

batch11 LCH_014/015 는 WARN35 35-list 누락분 — 양 디렉토리 glob으로 포착.

## GREEN gate — 통과

| 항목 | 결과 |
|---|---|
| parse | 13/13 yaml.safe_load OK (transform re-parse) |
| 필드 유효성 | focus_model=list 13 · assert∈7 · device_value=PENDING_F0 13 · list-method 적용 13 · CLK 2 model_confidence=device_confirm |
| non-target 무접촉 | `git diff --name-only` == 정확히 13 타깃 |
| diff stat | +28/−13 (11×`+2/−1`, CLK 2×`+3/−1`), EOL churn 0 |
| validate_tc 무영향 | 변경 MSG_069 ≡ 미변경 형제 BSC_038 (동일 verdict; STAGE1 DRAFT는 compiled-TC 스키마 비대상 = 선재 mismatch, 본 편집 무관) |
| idempotency | 2차 --apply = 0 changed / 13 skipped |

## 산출물

- transform: `scratch/cycle2_list_focus_model_transform.py` (멱등·dry-run default)
- YAML 편집 13: `stage1_review_mapping_batch10/` 9 + `stage1_s2_salvage_batch11/` 4
- handoff: `handoff_device_validation/THOR2J_R2_LIST_FOCUS_HANDOFF_2026-06-22.md`
- manifest: `handoff_device_validation/VALIDATION_MANIFEST_R2_LIST_2026-06-22.csv` (13, +focus_model/model_confidence) — 생성기 `scratch/gen_r2_list_manifest.py`

## 잔여 / device-gated (오늘 X)

- 실 selected/scroll 채록 + device_value backfill(PENDING_F0 해소) = F0 run1 (thor2j).
- CLK_030/031 컨테이너 타입(탭 vs list) 단말 확정 → STAGE1 환류.
- thor2j 러너 R2 구현(`has_selection_moved_from_baseline`) = thor2j 영역(§2.5).
- 후속 cycle: QPN 169/170·HDK_069 진입경로, WARN35 잔여 assert 변형, batch11 29 안전 핸들러.

## non-goals 준수

runner/validate 스키마 변경 0 · 단말 접촉 0 · selector 발명 0 (`android:id/list`는 method 설명 내 예시, 실 id는 PENDING_F0) · `export_status=STAGE1_DRAFT`·`validation_required=device_2run_green` 불변 · commit/push 미실행(별도 승인).
