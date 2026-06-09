# 23.Settings Menu-Tree Anchor-Gap Decomposition

> STATIC PROXY classification — NOT device-validated. No FULL_AUTO /
> RUNNABLE_NOW / automation-rate claim. FocusRule/Appium evidence is NOT
> transferred. Expected text is NOT device-observed text. Deep-link /
> component entries are *_CANDIDATE until device measurement.

## Population & filter
- source CSV: `THOR2 - ALT Basic TC Audit/overlap_join_2026-06-08.csv`
- source Excel (read-only): `doc/[THOR 2] ALT Basic Test Case_FULL.xlsx`
- baseline: `THOR2_K - Settings/catalog/menu_tree_baseline_20260604T102316Z.json` (run_id `20260604T102316Z`)
- filter: `source_sheet=23.Settings` AND `recommended_next_action=EXPORT_TO_APPIUM`
- population: **528** TC · Excel join 528/528 (missing 0)

## area × anchor_state
> TARGET_REACHED = d1 target screen reached. LEAF_LABEL_OBSERVED = leaf
> label seen in the d1 single-pass observation only (label, not a reached
> target). Neither requires menu-tree deepening.
| area | TARGET_REACHED | LEAF_LABEL_OBSERVED | PARTIAL | MISSING | UNKNOWN | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Google | 8 | 0 | 0 | 0 | 0 | 8 |
| 개인 정보 보호 | 0 | 0 | 12 | 0 | 0 | 12 |
| 검색 | 0 | 0 | 0 | 2 | 0 | 2 |
| 디스플레이 | 0 | 53 | 33 | 0 | 0 | 86 |
| 디지털 웰빙 및 자녀 보호 기능 | 0 | 0 | 21 | 0 | 0 | 21 |
| 배경화면 및 스타일 | 0 | 0 | 0 | 28 | 0 | 28 |
| 배터리 | 0 | 0 | 0 | 6 | 0 | 6 |
| 보안 | 0 | 0 | 0 | 63 | 0 | 63 |
| 소리 및 진동 | 0 | 5 | 5 | 0 | 0 | 10 |
| 시스템 | 0 | 0 | 0 | 14 | 0 | 14 |
| 시스템 언어 | 0 | 0 | 0 | 2 | 0 | 2 |
| 안심 기능 | 0 | 0 | 0 | 2 | 0 | 2 |
| 안전 및 긴급 상황 | 0 | 0 | 0 | 28 | 0 | 28 |
| 알림 | 0 | 0 | 0 | 23 | 0 | 23 |
| 알림 읽어주기 | 0 | 0 | 0 | 18 | 0 | 18 |
| 앱 | 0 | 0 | 4 | 0 | 0 | 4 |
| 연결된 기기 | 0 | 0 | 5 | 0 | 0 | 5 |
| 위치 | 3 | 0 | 0 | 0 | 0 | 3 |
| 일반 충전기 연결 | 0 | 0 | 0 | 1 | 0 | 1 |
| 잠금화면 | 0 | 0 | 0 | 1 | 0 | 1 |
| 저장용량 | 0 | 0 | 0 | 9 | 0 | 9 |
| 접근성 | 6 | 118 | 41 | 0 | 0 | 165 |
| 테마 및 배경화면 | 0 | 0 | 0 | 1 | 0 | 1 |
| 테마 셋팅 | 0 | 0 | 0 | 3 | 0 | 3 |
| 홈 설정 | 0 | 0 | 0 | 1 | 0 | 1 |
| 휴대전화 정보 | 12 | 0 | 0 | 0 | 0 | 12 |
| **ALL** | 29 | 176 | 121 | 202 | 0 | 528 |

## depth distribution
- depth 1: 125
- depth 2: 345
- depth 3: 37
- depth 4: 15
- depth 5: 6

## entry_method distribution
- DEEPLINK_CANDIDATE: 326
- MENU_NAVIGATION: 198
- SEARCH_CANDIDATE: 4

## recommended_probe distribution
- NO_ANCHOR_DEEPEN_NEEDED: 205
- PROBE_DEFER_MUTATION: 173
- PROBE_PRIORITY_MEDIUM: 58
- PROBE_PRIORITY_HIGH: 56
- PROBE_DEFER_INPUT: 36

## trait counts
- text_input_required: 150
- focus_nav_required: 0
- mutation_suspected: 253

## baseline-deepen recommendation (clean read-only gaps by area)
- 접근성: 15
- 디지털 웰빙 및 자녀 보호 기능: 14
- 알림: 14
- 보안: 12
- 안전 및 긴급 상황: 11
- 디스플레이: 10
- 저장용량: 9
- 개인 정보 보호: 8
- 배경화면 및 스타일: 4
- 앱: 4
- 연결된 기기: 4
- 배터리: 3
- 시스템: 2
- 소리 및 진동: 1
- 안심 기능: 1
- 일반 충전기 연결: 1
- 잠금화면: 1

## heuristic limits
- menu_path / depth parsed from Korean procedure text (deepest 설정-rooted `>` line).
- entry_method beyond hard-key/search is baseline-derived candidacy only.
- baseline is a shallow single-pass observation; PARTIAL means
  'leaf not observed yet', never 'leaf absent'. Confidence is capped.
- LEAF_LABEL_OBSERVED is a label sighting on the d1 dashboard, NOT a
  reached/verified target — it only means menu-tree deepening is unneeded.
- mutation_suspected reads the expected-result column too (result-form
  state-change verbs); observation verbs (노출/표시) are not mutations.
- deferral (mutation/input) applies to GAP candidates (PARTIAL/MISSING)
  only; anchor-resolved TCs are excluded from deepening regardless.
