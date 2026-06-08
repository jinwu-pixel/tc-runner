# ALT Basic × thor2j FocusRule — Focused Overlap Join Summary

- generated_at: 2026-06-08 (UTC date)
- method: **B. focused overlap join** (read-only, static/synthesis proxy)
- tc-runner SoT source: `doc/[THOR 2] ALT Basic Test Case_FULL.xlsx` (ko, 5,717 unique TC)
- thor2j reference source: `testcases/focusrule/focusrule_tc_catalog.yaml` (FocusRule v1.0.5 PDF, ja-JP, 151 FR)
- companion data: `overlap_join_2026-06-08.csv` (5717 rows × 17 cols)

## VERDICT — evidence reuse NOT possible; pattern reuse only
ALT Basic 와 thor2j FocusRule 은 **서로 다른 source corpus** (ID namespace / locale / device / spec 모두 상이).
따라서 thor2j Appium PASS 를 ALT Basic TC 의 PASS 또는 RUNNABLE_NOW 로 **전이하지 않는다.** 본 문서는
그 경계를 수치로 고정한 **false-evidence 방지 근거**다.

- exact_id join = 0 (구조적으로 불가)
- 최상위 fuzzy score 0.47~0.59 → reuse 근거로 약함
- **TWO_RUN_GREEN reuse 가능 = 0건**
- overlap 내 `IMPLEMENTED_*` 전이 행 = 0건 (증거전이 가드 통과)

## Scale
| metric | value |
| --- | --- |
| ALT Basic unique TC (SoT) | 5717 |
| overlap-theme candidates | 1286 |
| non-overlap NOT_FOUND | 4431 |

## theme_bucket distribution (overlap)
| theme_bucket | n |
| --- | --- |
| HARD_KEY | 739 |
| FOCUS_NAV | 251 |
| QUICK_PANEL | 221 |
| SETTINGS_DEFAULT_APP | 42 |
| BASIC_FOCUS | 33 |

## appium_existing_status (overlap)
| status | n |
| --- | --- |
| UNKNOWN | 1270 |
| PARTIAL | 16 |

## appium_evidence_level (overlap)
| evidence_level | n |
| --- | --- |
| THEME_OVERLAP | 1286 |

- overlap 중 FR 에 매칭된 행 = 441 (manual_candidate 1 / theme_overlap 1285)

## recommended_next_action (all 5717)
| action | n |
| --- | --- |
| EXPORT_TO_APPIUM | 1867 |
| MANUAL_ONLY | 1406 |
| REVIEW_MAPPING | 1196 |
| BLOCKED | 561 |
| GUIDE_OBSERVE | 503 |
| NEEDS_DEVICE_PROBE | 184 |

## reuse_policy lock
- `reuse_allowed=YES` ⟺ `appium_evidence_level=TWO_RUN_GREEN` AND `join_method=manual_candidate` (non-ambiguous).
- 본 데이터셋에서 해당 = 0. 즉 재사용 가능한 device-validated 증거 없음.

## Known limitation — SETTINGS_DEFAULT_APP over-capture
`SETTINGS_DEFAULT_APP` 버킷(42)은 'sms'/'기본값' 등 substring 으로
무관 Settings TC(잠금화면/보안/긴급상황 등)를 일부 끌어옴. 단 전부 `UNKNOWN`+`REVIEW_MAPPING` 으로
격리되어 false-promote 없음. 버킷 키워드 정밀화는 후속(낮은 우선순위 — reuse 0 이므로).

## Reuse stance (closing)
- thor2j 자산은 **TC 증거 재사용 대상 아님**.
- 재사용 대상 = 실행 패턴: `runner/appium_runner.py`, `runner/focus_snapshot.py`, `runner/fail_parser.py`,
  `runner/safe_fixture*.py` (cleanup), 2-run gate 절차.
- 본게임 = ALT Basic 자체의 `EXPORT_TO_APPIUM` (1867) 후보를 신규 합성.

## Non-claims
RUNNABLE_NOW 아님 · 자동화 완료/자동화율 아님 · Appium PASS ≠ ALT Basic PASS · static proxy 분류일 뿐.
