# STAGE1 Settings Batch 01 — Synthesis Summary (2026-06-08)

- scope: 23.Settings EXPORT 1st-slice -> final gate -> **KEEP 16** synthesized as STAGE1 CTF drafts.
- form: CTF (tc_prompts/STAGE1_NORMALIZE.md) + `audit_meta` overlay. **1 TC = 1 file.**
- status: **STATIC_ONLY draft. NOT device-validated. NOT runnable. evidence reuse from FocusRule = none.**
- vocabulary lock: `tc_class: SEMI_AUTO`; entry = `shell_candidate` (deeplink unconfirmed); verify = `expected_texts_candidate`.
- validation_required (each): `device_2run_green` (run later in thor2j-tc-appium, not here).

## KEEP — synthesized (16)
| tc_id | source_row | menu_anchor | sub_target | expected_texts_candidate |
| --- | --- | --- | --- | --- |
| ALTBASIC_SET_081 | 81.0 | 앱 | 최근 실행한 앱 | 최근 실행한 앱 |
| ALTBASIC_SET_082 | 82.0 | 앱 | 모두 보기 | 모두 보기, 모든 앱 |
| ALTBASIC_SET_085 | 85.0 | 앱 | 기기 사용 시간 | 기기 사용 시간 |
| ALTBASIC_SET_086 | 86.0 | 앱 | 사용하지 않는 앱 | 사용하지 않는 앱, 사용하지 않는 앱 없음 |
| ALTBASIC_SET_143 | 143.0 | 알림 | 대화 | 대화 |
| ALTBASIC_SET_145 | 145.0 | 알림 | 기기 및 앱 알림 | 기기 및 앱 알림 |
| ALTBASIC_SET_149 | 149.0 | 알림 | 방해금지 모드 | 방해금지 모드, 지금 사용 설정, 사람, 앱 |
| ALTBASIC_SET_827 | 827.0 | 위치 | 모두 보기 | 모두 보기 |
| ALTBASIC_SET_848 | 848.0 | 안전 및 긴급 상황 | 의료 정보 | 의료 정보, 이름, 생년월일, 혈액형, 키, 체중 |
| ALTBASIC_SET_871 | 871.0 | 안전 및 긴급 상황 | 비상 연락처 | 비상 연락처 |
| ALTBASIC_SET_922 | 922.0 | 디지털 웰빙 및 자녀 보호 기능 | 대시 보드 | 대시 보드 |
| ALTBASIC_SET_923 | 923.0 | 디지털 웰빙 및 자녀 보호 기능 | 취침 모드 | 취침 모드 |
| ALTBASIC_SET_955 | 955.0 | Google | 공유 데이터를 사용하여 맞춤 설정 | 공유 데이터를 사용하여 맞춤 설정 |
| ALTBASIC_SET_956 | 956.0 | Google | 광고 | 광고 |
| ALTBASIC_SET_957 | 957.0 | Google | 기기 및 공유 | 기기 및 공유, ChromeBook, QuickShare, 기기, 전송 옵션, 패스키로 연결된 기기 |
| ALTBASIC_SET_962 | 962.0 | Google | 위급 상황 정보 | 위급 상황 정보 |

## EXCLUDE — state/data mutation, NOT synthesized (6)
| source | reason |
| --- | --- |
| #822 | 위치 사용 토글 Off — 상태 변경/외부효과 |
| #823 | 위치 사용 토글 On — 상태 변경 |
| #469 | 홈 설정 적용하기 → 일반 홈 전환 — 런처 변경(고위험) |
| #929 | 집중 모드 지금 사용 — 모드 활성화 |
| #931 | 집중 모드 휴식 시간 적용 — 변이 |
| #872 | 비상 연락처 추가 — 데이터 추가 |

## REVIEW — held from first batch (2)
| source | reason |
| --- | --- |
| #875 | 긴급 SOS dialog 선택 — 민감, 관찰 범위 재설계 필요 |
| #140 | 알림 정렬 드롭박스 — 리스트 순서 변동, assert 곤란 |

## Guards
- no device / Appium / ADB call during synthesis.
- no thor2j-tc-appium modification; target_repo recorded as downstream destination only.
- FocusRule (ja-JP) evidence NOT transferred (`focusrule_evidence_transfer: false`).
- deeplink intents are CANDIDATES (APPLICATION_SETTINGS / LOCATION_SOURCE_SETTINGS where public; else UNRESOLVED) — confirm via device probe before execution.
- expected strings are paraphrase-derived candidates, not confirmed on-screen literals.

## Non-claims
NOT RUNNABLE_NOW · NOT automation-complete · NOT FULL_AUTO · static proxy synthesis only.
