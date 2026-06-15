# STAGE1 batch10 — REVIEW_MAPPING KEEP_CONFIRMED 271 합성 (2026-06-15)

입력 = REVIEW_MAPPING fresh 1,130 재판정(2-pass + false-KEEP QA)의 **KEEP_CONFIRMED 271** (`KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv`). 사용자 승인 = 전체 271 합성 (2026-06-15).

## 방법

1. **tc_id 배정** (결정적) — sheet→prefix 맵(신규 HDK/QPN/CAL/SST/TLK/RAD/SLC + 기존 BSC/CNT/CAM/MSG/SET/CLK/LCH/PDM/PFW/MGN/SFT/CALC/VRC 재사용). tc_id = `ALTBASIC_<PREFIX>_<row3>`. 기존 190 draft와 충돌 0 / 내부 중복 0.
2. **합성 워크플로** `altbasic-stage1-synth-batch10` — 18 클러스터 배치, 18 에이전트가 procedure/expected를 STAGE1 CTF 구조(step 분해·intent[navigate/press_key/tap/wait]·verify literal 추출·title·risk_note·cleanup)로 정규화 → 구조화 반환. 발명 0 원칙.
3. **결정적 렌더** — 구조화 결과를 기존 canonical 포맷(header 주석·step boilerplate[ambiguity/confidence 0.5/source_trace]·audit_meta 18필드)으로 YAML 렌더. HTML 이스케이프(`&gt;`) unescape. 271 파일 `stage1_review_mapping_batch10/`.
4. **gate** — parse·tc_id 충돌·intent enum·금지 HARD 토큰·source_trace presence·automation_summary 산술·expected presence.

## gate 결과 — GREEN

- 271 파일 / 425 step, **FAIL 0**.
- intent: press_key 315 · navigate 75 · tap 31 · wait 4 (전부 관찰형).
- tc_id 충돌 0 · 내부 중복 0 · HARD 토큰(am start/adb/pm/settings put/shell…) 0 · 산술 정합 271/271.
- **WARN 35** = positive verifier 부재(무동작 "아무런 동작 없음" / focus 미표시 / 포커스 이동만 — 고정 literal 없음). FAIL 아님. 단말 검증 시 element-presence·focus-state verifier 설계 필요(텍스트 assert 불가) → handoff 플래그.

## 산출

- `stage1_review_mapping_batch10/ALTBASIC_*_canonical.yaml` 271건 (전부 STAGE1_DRAFT / STATIC_ONLY / validation_required=device_2run_green)
- **STAGE1_DRAFT 누적 184 → 455**
- 작업 중간물: `_synth_assign.json` · `_synth_batches/` (untracked)

## 다음 게이트 (승인 대기)

1. F0 단말 2-run 검증 handoff (thor2j) — manifest 작성 후 승인. WARN 35는 verifier 재설계 동반.
2. commit/push — 본 batch10 + 재판정 산출물(CSV·summary). 명시 승인.
3. REVIEW 812 / EXCLUDE 47은 DEFER·종결 트랙.
