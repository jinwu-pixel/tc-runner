# STAGE1 draft 정합 감사 + Phase 1 단말 환류 (32 drafts, 2026-06-09)

batch01(16) + batch02(16) = **32 STAGE1 draft** 전수 정적 감사 + Phase 1 read-only
단말 probe 결과 환류. read-only(Read/Grep)만 사용, **draft 편집·commit·push 0**.

- 입력: `stage1_settings_batch01/` · `stage1_settings_batch02/`
- 단말 근거: [STAGE1_BATCH01_DEVICE_PROBE_2026-06-09.md](STAGE1_BATCH01_DEVICE_PROBE_2026-06-09.md) (Phase 1, F0)
- 성격: **정적 감사 + manual evidence**. validate/runtime PASS 아님. 승격 0.

## APPLIED 2026-06-09 — D1/D2 + Phase1 환류 batch01 16건 반영 완료

플랜 [`docs/superpowers/plans/2026-06-09-stage1-batch01-correction.md`](../docs/superpowers/plans/2026-06-09-stage1-batch01-correction.md)
대로 surgical Edit 적용(**commit 없음**). 검증: 금지토큰 0 · automation_class SEMI 16 / FULL 0 ·
anchor_state·deepen_anchor_link 16/16 · YAML parse 16/16 · diff surgical(182+/117−). **batch02 무편집**.
단말 verdict는 per-file 헤더 주석 + entry_type/shell_hint에 layering(static anchor_state=CSV 인용, 무변).
아래 **§3 D1/D2 · §4 환류 = applied**. export_status 승격 0(STAGE1_DRAFT 유지).

---

## 1. Vocabulary-lock 준수 (GREEN)

| 항목 | 결과 |
| --- | --- |
| 금지토큰 `RUNNABLE_NOW` / `runnable: true` / `tc_class: FULL_AUTO` / `am start` | **0 / 32** ✓ |
| `tc_class: SEMI_AUTO` | 32 / 32 ✓ |
| `export_status: STAGE1_DRAFT` | 32 / 32 ✓ |
| `evidence_level: STATIC_ONLY` | 32 / 32 ✓ |
| `validation_required: device_2run_green` | 32 / 32 ✓ |
| `focusrule_evidence_transfer: false` | 32 / 32 ✓ |

핵심 가드는 전건 정합 — false-promote / 증거전이 위험 토큰 없음.

## 2. batch02 anchor 계약 정합 (GREEN)

| anchor_state | n | intent type | entry_type | 정합 |
| --- | --- | --- | --- | --- |
| MISSING (알림6+안전2) | 8 | `shell_candidate` | `tap_navigation_unresolved` | ✓ (action 미발명) |
| PARTIAL (웰빙) | 6 | `navigate` | `tap_navigation_required` | ✓ (shell_candidate 0) |
| TARGET_REACHED (Google) | 2 | `navigate` | `baseline_reached_parent_then_tap` | ✓ |

batch02는 선언한 anchor 계약과 16/16 일치.

## 3. Drift / 불일치 (FIX 후보 — 편집은 승인 게이트)

| # | 항목 | 내용 | 권고 |
| --- | --- | --- | --- |
| D1 | **automation_class batch 간 drift** | batch01 16 = `FULL_AUTO_CANDIDATE`, batch02 16 = `SEMI_AUTO_CANDIDATE`. 둘 다 `tc_class: SEMI_AUTO`. batch02 summary "common guards"가 `SEMI_AUTO_CANDIDATE` 명시 → batch01이 lock 이전 산출. SEMI_AUTO·entry 미확정·verify paraphrase인 draft에 `FULL_AUTO_CANDIDATE`는 **over-claim**. | batch01 16건 → `SEMI_AUTO_CANDIDATE` 정렬 (일관성 + over-claim 제거) |
| D2 | **audit_meta 필드셋 불일치** | batch01 = `safety_class`/`verifier_type`/`menu_tree_anchor`/`matched_screen_id`/`risk_note`. batch02 = `entry_type` 변형(`tap_navigation_*`/`baseline_reached_*`) 중심. 같은 STAGE1 산출이 필드 스키마 상이. | STAGE1 draft 공통 스키마 1장 고정 후 양 batch 정렬 (별도 정의 PR, §2.3 source-of-truth) |

D1/D2는 draft YAML 편집 필요 → **사용자 승인 후** 별도 작업. 본 감사는 식별까지.

## 4. Phase 1 단말 환류 — batch01 draft별 정정 계획

Phase 1(F0)에서 batch01 16건 진입을 실측한 결과를 draft `shell_hint`/`entry_type`에 환류.
**verdict는 manual evidence**(anchor 진입), 편집은 승인 후.

| tc | 영역 | 현재 shell_hint(요지) | Phase1 verdict | 환류 정정안 |
| --- | --- | --- | --- | --- |
| 082 | 앱 | APPLICATION_SETTINGS → 모두 보기 | CONFIRMED | action `MANAGE_APPLICATIONS_SETTINGS`로 확정(leaf 화면 자체 도달); `entry_type` deeplink 유지 |
| 827 | 위치 | LOCATION_SOURCE_SETTINGS → 모두 보기 | CONFIRMED (control) | action `LOCATION_SOURCE_SETTINGS` 확정; leaf "모두 보기" present |
| 143 | 알림 | settings_root UNRESOLVED → 대화 | CONFIRMED (control) | parent action `NOTIFICATION_SETTINGS`로 **UNRESOLVED 해소**; leaf "대화" present |
| 145 | 알림 | settings_root UNRESOLVED → 기기 및 앱 알림 | CONFIRMED (control) | parent `NOTIFICATION_SETTINGS` 확정; leaf present |
| 081 | 앱 | APPLICATION_SETTINGS → 최근 실행한 앱 | **WRONG_TARGET** | action 폐기 → `entry_type: tap_navigation_required`(설정홈 "앱" 대시보드 tap). leaf "최근 실행한 앱"은 대시보드 최상단 present(파일럿 확인) |
| 085 | 앱 | APPLICATION_SETTINGS → 기기 사용 시간 | **WRONG_TARGET** | 동일 정정. leaf는 대시보드 2 viewport 미노출 = **Phase2 잔여**(의심: 디지털 웰빙 하위) |
| 086 | 앱 | APPLICATION_SETTINGS → 사용하지 않는 앱 | **WRONG_TARGET** | 동일 정정. leaf **Phase2 잔여** |
| 149 | 알림 | settings_root UNRESOLVED → 방해금지 모드 | 부모 CONFIRMED / leaf UNVERIFIED | parent `NOTIFICATION_SETTINGS` 확정; leaf below-fold = **Phase2 scroll 잔여** |
| 848 | 안전긴급 | settings_root UNRESOLVED → 의료 정보 | NO_RESOLVER | UNRESOLVED 유지 정당; Phase2 tap. **PII(의료) redaction 주의** |
| 871 | 안전긴급 | settings_root UNRESOLVED → 비상 연락처 | NO_RESOLVER | UNRESOLVED 유지 정당; Phase2 tap. **PII(연락처) redaction 주의** |
| 922 | 웰빙 | settings_root UNRESOLVED → 대시보드 | NO_RESOLVER | coverage-gap 재확인; UNRESOLVED 유지. Phase2 tap (batch02 웰빙 PARTIAL과 동일 영역) |
| 923 | 웰빙 | settings_root UNRESOLVED → 취침 모드 | NO_RESOLVER | 동일 |
| 955 | Google | settings_root UNRESOLVED → 맞춤설정 | NO_RESOLVER | 외부 Google pkg; UNRESOLVED 유지. Phase2 tap. **계정정보 redaction 주의** |
| 956 | Google | settings_root UNRESOLVED → 광고 | NO_RESOLVER | 동일 |
| 957 | Google | settings_root UNRESOLVED → 기기 및 공유 | NO_RESOLVER | 동일 |
| 962 | Google | settings_root UNRESOLVED → 위급 상황 정보 | NO_RESOLVER | 동일 |

**환류 정정 분류:**
- **action 확정 5** (082/827/143/145 + 149 parent): UNRESOLVED/후보 → device-confirmed action. draft 품질 상향.
- **entry 정정 3** (081/085/086): `APPLICATION_SETTINGS` 폐기 → `tap_navigation_required`(설정홈 "앱" 대시보드). WRONG_TARGET 해소.
- **UNRESOLVED 유지 정당 8** (848/871/922/923/955/956/957/962): 단말이 공개 action 부재 입증 → draft가 action 미발명한 게 옳았음. Phase2 tap-discovery 대상.

## 5. thor2j-tc-appium 핸드오프 readiness (cross-commit 금지 = read-only 핸드오프)

| 등급 | drafts | 상태 |
| --- | --- | --- |
| **A. entry device-validated** | 082·827·143·145 (4) | parent+control 단말 확인. 2-run green 착수 고신뢰. leaf 내부는 control_presence 계약으로 충족 |
| **B. entry 정정 후 handoff** | 081·085·086·149 (4) | shell_hint/entry_type 정정 필요(§4). 081 leaf 확인·085/086/149 leaf = Phase2 잔여 |
| **C. tap-discovery 필요** | 848·871·922·923·955·956·957·962 (8) | 공개 deeplink 부재. thor2j tap-nav 탐색. 871/848/Google = PII redaction gate 경유 |
| **D. 미probe (Phase2 대기)** | batch02 16 | 단말 probe 전. entry 계약 선언만, 미검증 |

## 6. 후속 (승인/단말 게이트)

1. **draft 편집(D1/D2 + §4 정정)** — 사용자 승인 후. STAGE1 공통 스키마 정의 → batch01/02 정렬(§2.3).
2. **Phase 2 재개** — F0 재연결 시 085/086 below-fold + 149 알림 scroll + batch02 16 tap-discovery. PII leaf redaction 필수.
3. **classifier cue-set 강화** — batch02 summary NOTE의 mutation 누락 cue(유지된다/처리된다/선택-적용) → `scripts/settings_anchor_gap.py` 별도 트랙(승인 후).
4. **export_status 승격** — 전건 device_2run_green(thor2j) 후에만. 본 감사로 승격 0.
