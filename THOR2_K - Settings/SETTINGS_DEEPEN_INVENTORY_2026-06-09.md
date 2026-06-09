# Settings menu-tree deepen inventory — Category A (PRIORITY_HIGH, depth≥2)

- source: `THOR2 - ALT Basic TC Audit/settings_anchor_gap_enriched_2026-06-09.csv`
- scope: `recommended_probe = PROBE_PRIORITY_HIGH` AND `depth ≥ 2` (= Category A,
  the genuine deeper-leaf gaps; d1 baseline screen already REACHED).
- **34 source TC → 19 unique leaves** (deduped by `area + menu_path leaf`).
- STATIC PROXY only. Entry actions below are **CANDIDATES**, not device-confirmed.
  No device execution performed. `observe_only` — screen entry + read-only
  observation; mutation/input actions are out of scope.

## Classification (19 leaves)

| leaf | area | depth | class | candidate entry / reason | source TC |
| --- | --- | ---: | --- | --- | --- |
| 인쇄 | 연결된 기기 | 3 | **PUBLIC_ACTION_CANDIDATE** | `ACTION_PRINT_SETTINGS` (AOSP public, API19+) — high | 78 |
| 앱N개 모두보기 | 앱 | 2 | **PUBLIC_ACTION_CANDIDATE** | `MANAGE_APPLICATIONS_SETTINGS` (AOSP public, API3+) — high | 82 |
| 편안한 화면 | 디스플레이 | 2 | **PUBLIC_ACTION_CANDIDATE** | `android.settings.NIGHT_DISPLAY_SETTINGS` (API26+) — medium (OEM "편안한 화면"=Eye comfort, verify screen match) | 403,405,407 |
| 실시간 자막 | 접근성 | 2 | **UNRESOLVED** | `CAPTIONING_SETTINGS` = video captions, not guaranteed = OEM Live Caption → discovery hypothesis only, resolve-only | 603,604,606,607,608,611,612 |
| 보청기 | 접근성 | 2 | **UNRESOLVED** | no confirmed public Settings action (`HEARING_DEVICES_SETTINGS` unverified) → resolve-only / TAP_ONLY | 631,632,633 |
| 전송 | 연결된 기기 | 3 | TAP_ONLY | 연결 환경설정 하위, no public action | 77 |
| 최근 실행한 앱 | 앱 | 2 | TAP_ONLY | within APPLICATION_SETTINGS, no sub-action | 81 |
| 기기 사용 시간 | 앱 | 2 | TAP_ONLY | no public action | 85 |
| 사용하지 않는 앱 | 앱 | 2 | TAP_ONLY | no public action | 86 |
| 진동 및 햅틱 | 소리 및 진동 | 2 | TAP_ONLY | no public action (source leaf "…off" = mutation; screen observe-only if ever seeded) | 278 |
| 밝기 자동 조절 설정 메뉴 | 디스플레이 | 2 | TAP_ONLY | no public adaptive-brightness action | 292,293,294,295 |
| 다크 모드 설정 | 디스플레이 | 2 | TAP_ONLY | DARK_THEME action not public | 364 |
| 화면 자동회전 설정 | 디스플레이 | 2 | TAP_ONLY | no public auto-rotate action | 408 |
| 터치 민감도 | 디스플레이 | 2 | TAP_ONLY | OEM, no public action | 414 |
| 텍스트 읽어주기 메뉴 | 접근성 | 2 | TAP_ONLY | TTS settings action not public | 483,484,489 |
| 색상 및 모션 메뉴 | 접근성 | 2 | TAP_ONLY | OEM grouping, no public action | 525 |
| 디스플레이 크기 및 텍스트 메뉴 | 접근성 | 2 | TAP_ONLY | no public action | 537 |
| Quick Share | 연결된 기기 | 3 | EXTERNAL_PACKAGE | OEM/Google share feature (separate package) | 79 |
| Android Auto | 연결된 기기 | 3 | EXTERNAL_PACKAGE | `com.google.android.projection.gearhead` | 80 |

### Tally (revised per review 2026-06-09)
- PUBLIC_ACTION_CANDIDATE: **3** — 인쇄 / 앱N개 모두보기 / 편안한 화면 (→ launch_candidates)
- UNRESOLVED: **2** — 실시간 자막 (CAPTIONING discovery hypothesis) / 보청기 (no public action) (→ resolve_only_candidates)
- TAP_ONLY: 12 (defer to v1.1+ tap-discovery / guarded DFS)
- EXTERNAL_PACKAGE: 2 (out of `com.android.settings` scope)
- EXPORTED_COMPONENT_CANDIDATE: 0

Probe protocol: resolve-only ALL 5 candidate ids; launch only the 3
PUBLIC_ACTION_CANDIDATE; decide the 2 UNRESOLVED after their resolver result.
CONFIRMED = resolver present + am start ok + observed_focus = expected pkg/activity
+ uiautomator dump ok + target-leaf text evidence; else NO_RESOLVER / WRONG_TARGET
/ FOCUS_MISMATCH / DUMP_REJECTED.

## Excluded from this round

### Category B — depth-1 d1-reach gaps (22 TC, NOT deeper-leaf)
These PRIORITY_HIGH rows are depth-1 (leaf == d1) flagged PARTIAL only because the
baseline d1 screen itself was FOCUS_MISMATCH. They are **not** deepen targets.
- **개인 정보 보호 (8 TC)** — `PRIVACY_SETTINGS` action is valid; the FOCUS_MISMATCH
  was the one-off `settings_d1_privacy` OBSERVED anomaly (subsequent 0/20 mismatch,
  closed). **NOTE: stale gap from an old baseline state**, not a live gap.
- **디지털 웰빙 및 자녀 보호 기능 (14 TC)** — confirmed coverage-gap: no shell-launchable
  exported activity / public action (WELLBEING_SETTINGS / DIGITAL_WELLBEING_SETTINGS
  both "No activity found"). Kept for **v1.1+ tap-discovery** follow-up.

### TAP_ONLY / EXTERNAL_PACKAGE (14 leaves)
Deferred — reachable only by tap-navigation (out of current deep-link explorer
scope) or in another package.

## Device probe verdicts (F0, 2026-06-09) — supersedes static candidacy above
Read-only probe done (resolver + focus + screen text). Full evidence:
`SETTINGS_DEEPEN_PROBE_RESULTS_2026-06-09.md`.

| leaf | static class | **F0 verdict** |
| --- | --- | --- |
| 인쇄 | PUBLIC_ACTION_CANDIDATE | **CONFIRMED** → v1.2 seed |
| 앱N개 모두보기 (모든 앱) | PUBLIC_ACTION_CANDIDATE | **CONFIRMED** → v1.2 seed |
| 편안한 화면 | PUBLIC_ACTION_CANDIDATE | **DOCUMENT_DRIFT_CANDIDATE** (label "야간 조명"; promotion withheld) |
| 실시간 자막 | UNRESOLVED | **WRONG_TARGET → TAP_ONLY** (CAPTIONING = 자막 styling, not Live Caption) |
| 보청기 | UNRESOLVED | **NO_RESOLVER → TAP_ONLY** |

Promoted seed = `THOR2_K - Settings/menu_tree_deepen_seed_v1_2.yaml` (CONFIRMED ×2 only).
Pre-probe draft `_deepen_subset_seed_2026-06-09.yaml` retained as the candidacy record.
Canonical `menu_tree_seed.yaml` untouched.
