# Settings batch01+02 (32건) → Device Validation Handoff Package — 2026-06-10

**성격**: sidecar 패키지. 기존 pushed YAML 32건 **무수정** — 판정·실측 반영은 본 패키지 레이어에만 기록.
**소비자**: thor2j-tc-appium 2-run gate (단말 배정 = 해당 트랙 결정). F0 배치 run은 RUNNABLE_NOW 성공률 확인용으로 별도 (tc-runner 측).
**증거 전이 금지**: thor2j FocusRule(ja-JP, 별개 corpus) 증거는 본 패키지에 전이하지 않음 (`focusrule_evidence_transfer=false` 유지).
**표기 상한**: `DEVICE_VALIDATION_READY_CANDIDATE`까지만. READY 확정·승격은 소비 트랙의 단말 실측 후.

## 결과

| handoff_status | 건수 | tc_id |
|---|---|---|
| `DEVICE_VALIDATION_READY_CANDIDATE` | **14** | 081, 082, 086, 143, 144, 145, 149, 827, 954, 955, 956, 957, 958, 962 |
| `NOT_READY_PROBE_REQUIRED` | 18 | 085, 152, 159, 162, 164, 167, 848, 871, 888, 893, 921, 922, 923, 932, 934, 938, 942, 944 |

상한 20 대비 14건 — **숫자 채우기 위한 모호 건 승격 안 함** (운영 원칙).

## DVR_CANDIDATE 14 판정 근거 (entry tier)

| tier | entry_method | tc_id | 근거 |
|---|---|---|---|
| 1 | deeplink_confirmed | 082 | F0 Phase1 deeplink CONFIRMED, leaf 자체 도달 |
| 2 | parent_deeplink_plus_tap | 143, 145, 149, 144, 827 | 부모 화면 F0 deeplink CONFIRMED + 1 tap (149/144는 leaf UNVERIFIED 명기) |
| 2 | home_tap_path | 081, 086 | 설정홈→'앱' tap 경로 + leaf PRESENT(081) / below-fold UNVERIFIED(086) |
| 3 | parent_baseline_plus_tap | 954, 955, 956, 957, 958, 962 | Google d1 baseline-reached + 1 tap (외부 pkg 가능 비단정) |

- **144 sidecar 승격 주석**: batch02 YAML은 `tap_navigation_unresolved` 유지(무편집) — batch02 커밋 후 수행된 F0 Phase1이 부모(NOTIFICATION_SETTINGS→알림) 확정한 것의 사후 반영. YAML과 패키지 간 의도된 차이.
- **PII 3건 (955/962 REQUIRED, 956 CHECK)**: 검증 run 캡처 산출물은 redaction gate 경유, raw dump commit 금지 ([[project_redaction_policy_task41]] 정책 준수).

## NOT_READY 18 사유 분포

| 사유 | 건수 | tc_id |
|---|---|---|
| 웰빙 d1 = CONFIRMED coverage-gap (tap-discovery 선결) | 8 | 921, 922, 923, 932, 934, 938, 942, 944 |
| depth-3 chain 미확정 (중간 hop '방해금지 모드' UNVERIFIED — 149 통과 후 연쇄 승격 후보) | 5 | 152, 159, 162, 164, 167 |
| entry UNRESOLVED (tap-discovery 선결) | 2 | 888, 893 |
| entry UNRESOLVED + PII redaction gate 선결 | 2 | 848, 871 |
| leaf 위치 모호 (앱 대시보드 vs 웰빙 하위 — FAIL 판별 불가) | 1 | 085 |

## 파일

- `HANDOFF_PACKAGE_2026-06-10.csv` — 32행 × 18필드 (source trace / entry 상태(F0 Phase1 실측) / verifier 후보+caveat / cleanup / risk / redaction / handoff_status / not_ready_reason)
- 본 summary

## 검증 run 공통 규칙 (소비 트랙 전달사항)

1. 전 건 관찰 전용 — 토글/저장/선택/입력/실행 금지, verifier는 presence-only (On/Off 현재 상태 비단정)
2. verifier 후보는 source paraphrase — 1차 관찰에서 on-screen literal 확정 후 verifier 고정 (paraphrase 그대로 PASS 단정 금지)
3. FAIL 시 분류: entry FAIL(화면 미도달) / leaf FAIL(미노출) / verifier FAIL(문구 불일치) 구분 기록
4. 2-run green 충족 시에만 RUNNABLE 승격 — 본 패키지 단독으로 runnable 주장 금지
