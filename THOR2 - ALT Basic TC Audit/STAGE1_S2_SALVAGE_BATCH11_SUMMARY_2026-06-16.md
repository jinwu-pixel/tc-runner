# STAGE1 batch11 — REVIEW device-free 구제 합성 (2026-06-16)

입력 = Stream 2 직독 재판정(`S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`)의 **SALVAGE_CONFIRMED 29**. 사용자 승인 = 전체 29 합성.

## 방법 (batch10 모델)

1. **tc_id 결정적 배정** — sheet→prefix(HDK/QPN/SET/LCH/CAL/CLK/CALC/SST) + `ALTBASIC_<PREFIX>_<excel_row3>`.
2. **합성 Workflow** `altbasic-s2-synth-batch11` (6 청크) — 에이전트가 procedure/expected를 STAGE1 CTF 구조로 정규화(발명 0·HARD토큰 금지·salvage_pattern 안전기제 인코딩) → 구조화 반환.
3. **결정적 YAML 렌더** `scratch/s2_render_batch11.py` — canonical 포맷 + redesign_source/pattern/removed. focus/presence는 `verifier_contract`(Stream 1 일관, PENDING_F0), step expected는 verify_text/빈칸만(새 runner verb 0).

## 합성 결과 — 29

- **batch11 = 29** STAGE1 CTF draft `stage1_s2_salvage_batch11/` (전부 STAGE1_DRAFT / STATIC_ONLY / validation_required=device_2run_green).
- 정정 이력: 합성 중 **워크플로 에이전트 side-effect**로 4개 phantom yaml(CALC_027·028·SST_010·011, `rejudge_pass=s2_salvage_confirmed`)이 batch10 dir에 잘못 기록됨 → 일시적으로 batch10 기존 draft로 오인해 4건 drop(batch11=25 보고). **git 추적 검증**으로 phantom = untracked 에이전트 산출물 확정(fc56cf8 미포함) → phantom 삭제 + 4건 batch11 복원 = **29 확정**.

## gate — GREEN

- 29/29 parse · **tc_id 충돌 0** (phantom 삭제 후, cross-batch 검사) · HARD 토큰 0 · 산술 정합 29/29.
- intent: press_key 다수 · navigate (전부 관찰형).
- verifier_type: focus_state 13 · element_presence 10 · verify_text 6 — **WARN 0**(전건 literal 또는 contract).
- redesign_pattern: transient_input 12 · popup_cancel 8 · observe_split 6 · selection_gated 3.

## 안전 기제 (재설계 인코딩)

- popup_cancel 8: 확인 다이얼로그는 고정 literal presence만 관찰 → 취소/back 이탈 (mutation 0, 확정 tap 금지).
- transient_input 12: 하드키/숫자 입력 가역(AC/clear/back), 저장·발신 금지, display/focus 관찰만.
- selection_gated 3: focus/선택만, OK 확정 실행 금지.
- observe_split 6: 핵심 axis(presence/focus 계약)만 verify, 보강 axis(단말 의존)는 risk_note 강등.

## STAGE1_DRAFT 누적

455 → **484** (batch11 +29).

## 산출 / 상태

- `stage1_s2_salvage_batch11/ALTBASIC_*_canonical.yaml` 29건.
- handoff: `handoff_device_validation/VALIDATION_MANIFEST_BATCH11_2026-06-16.csv`(64 = batch11 29 + WARN35 35) + `THOR2J_HANDOFF_BATCH11_2026-06-16.md`.
- 작업 중간물(untracked): `_s2_synth_input.json` · `_s2_synth_structured.json` · `_s2_synth_alts.json`.
- **단말 2-run·commit 미실행 = 승인 대기.** 13 focus_state + 10 element_presence는 F0 selector 캡처 동반 필요.

## 발견 (§8.2 proposed 후보)

1. **워크플로 에이전트 side-effect (실 버그)**: 합성 에이전트(Bash/Write 권한)가 구조화 반환 대신 yaml 4개를 batch10 dir에 직접 기록 + 슬라이스 over-read로 53 반환(29 기대). → **합성 워크플로 에이전트는 read-only/return-only로 제약, 실행 후 untracked 오염 스캔 필수**. 본 건은 git 추적 검증으로 포착·정정.
2. **tc_id 스킴 비단사 + Excel 중복 TC ID**: `ALTBASIC_<PREFIX>_<excel_row3>`는 sheet 내 중복 TC ID(감사 결과 Safety/Launcher/Call/Camera 4 sheet·83건) 시 cross-pool 충돌 가능. → prep 단계 cross-batch 충돌검사 도구화(`scratch/altbasic_tcid_collision_check.py`), 후속 합성 선행 게이트로 사용.
