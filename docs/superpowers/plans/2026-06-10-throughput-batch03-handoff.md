# 2026-06-10 Throughput batch plan (A: handoff 32 / B: Clock+Calc 재판정 / C: batch03 합성)

목표·KPI·게이트 = 사용자 /goal 지시 (2026-06-10) 그대로. 본 문서는 배치당 plan 1개 의례 산출물.

## KPI (주간)

| 지표 | 목표 | 판정 기준 |
|---|---|---|
| STAGE1_DRAFT | 120건/주 | YAML parse + 필수필드 + 금지토큰 0 |
| DEVICE_VALIDATION_READY (Primary) | 100건/주 | **정적 완결성 5필드**: source trace / entry 상태 / verifier 후보 / cleanup / risk 전부 기록 (단말 증거 불요) |
| RUNNABLE_NOW | 초기 20건/주 | 단말 2-run green (F0 배치 2회 실측 후 40건 stretch 승격 판단) |

## 오늘 실행 순서

1. **A. 기존 32건(batch01+02) handoff package** — pushed YAML 무수정, sidecar 패키지로:
   - `handoff_device_validation/HANDOFF_PACKAGE_2026-06-10.csv` (per-TC record) + `HANDOFF_SUMMARY_2026-06-10.md`
   - 필드: tc_id / source trace / entry 상태(F0 Phase1 실측 반영) / verifier 후보 / cleanup / risk / `handoff_status`
   - 상한 20건. `DEVICE_VALIDATION_READY_CANDIDATE`까지만 표기. anchor/action 미확정 = UNRESOLVED 유지. FocusRule 증거 전이 금지.
   - target = thor2j 2-run gate (단말 배정은 해당 트랙 결정). F0 배치는 RUNNABLE_NOW 성공률 확인용 별도.
2. **B. Clock(71)+Calculator(25)=96 전수 재판정** — KEEP / REVIEW_QUEUE / EXCLUDE:
   - mutation·input·알람 저장·시간 변경·기록 삭제·외부효과 cue 재검사
   - Clock 알람 생성·수정·삭제·타이머 실행 = observe-only와 분리 (KEEP 불가)
   - Calculator 계산 입력 = INPUT_REQUIRED 분리 (단순 진입 TC와 동일 안전등급 금지)
   - 1건 10분 초과 → REVIEW_QUEUE
3. **C. batch03 합성** — KEEP만. `stage1_clock_calc_batch03/ALTBASIC_<sheet>_<id>_canonical.yaml`
   - tc_class=SEMI_AUTO / export_status=STAGE1_DRAFT / evidence_level=STATIC_ONLY / validation_required=device_2run_green / focusrule_evidence_transfer=false
   - RUNNABLE_NOW · runnable:true · FULL_AUTO 승격 금지. 40 채우기 위한 무리 승격 금지.

## 리뷰 강도 (첫 throughput batch)

- 표본 = max(20건, 생성물 20%), Clock/Calculator × safety × verifier × anchor 상태 계층 분산
- **false-promote 정의 4종**: (a) anchor/entry 발명 (b) safety 등급 과소 (c) source 기대결과에 없는 verifier 단정 (d) 금지토큰
- 5% 이하 2회 연속 → 이후 10% 축소. 공통 결함 일괄 수정, 개별 문구 미세조정 금지.

## batch04 (같은 날 추가 — 사용자 지시)

- wave2 KEEP 49(human_confirmed) → `stage1_wave2_batch04/` STAGE1 draft + `HANDOFF_PACKAGE_BATCH04` DVR_CANDIDATE 전환
- 표기 보정: cue 단독 배제 211 = `EXCLUDE_CANDIDATE_UNREVIEWED` (확정 EXCLUDE 29와 분리, KPI 합산 금지)
- 신규 계약: `cleanup_candidate`(transient 원상복귀 기록) + `carrier_fit`(UNCONFIRMED_ON_TARGET_DEVICE 11건)
- commit = batch03 + batch04 + wave2 분석 1 의미 단위 (명시 승인 후)

## 금지 (오늘)

- 단말 호출 / commit / push (별도 승인 전)
- per-file 리뷰, 개별 commit
- 신규 인프라 (batch 10%+ 막는 공통 결함 시에만; 1회용 추출 스크립트는 인프라 아님, 사용 후 삭제)
