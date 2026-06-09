# Settings deepen probe results — F0, 2026-06-09 (LOCAL CARRY, uncommitted)

- device: `B06201249E0002F0` (AT-M140 / thor2, THOR2_K). B27 (`B2700125BW000083`) NOT
  addressed — every adb command used `-s B06201249E0002F0` (both devices connected).
- protocol: read-only. HOME / launch / dumpsys / uiautomator only. NO tap / input /
  toggle / settings put / pm / reboot.
- **persistent data mutation: 0** (no toggle/write). **process-state reset: yes** —
  `am start -S` was used to force a fresh Settings launch (Settings is single-task;
  re-launching a sibling action while Settings is foreground is otherwise "delivered
  to the top-most instance"). `-S` resets the Settings process/task only; it does not
  change any persistent setting.
- run label: `deepen-probe-2026-06-09` (informal; no MENU_TREE_RUNS bundle contract).
- raw XML kept on-device only (pull to spaced path failed) → text evidence inline.
  On-device stray dump: `/sdcard/window_dump.xml` (path reported; not deleted).
  No redacted sidecar committed.

## Stage 1 — resolve-only (5)
| candidate | wire action | resolver | resolved activity |
| --- | --- | --- | --- |
| 인쇄 | `android.settings.ACTION_PRINT_SETTINGS` | present | `Settings$PrintSettingsActivity` |
| 앱 모두보기 | `android.settings.MANAGE_APPLICATIONS_SETTINGS` | present | `Settings$ManageApplicationsActivity` |
| 편안한 화면 | `android.settings.NIGHT_DISPLAY_SETTINGS` | present | `Settings$NightDisplaySettingsActivity` |
| 실시간 자막 | `android.settings.CAPTIONING_SETTINGS` (hypothesis) | present | `Settings$CaptioningSettingsActivity` |
| 보청기 | `android.settings.HEARING_DEVICES_SETTINGS` (hypothesis) | **No activity found** | — |

## Stage 2 — launch (4 launched; resolver-present)
| candidate | focus activity (display 0) | screen text evidence | verdict |
| --- | --- | --- | --- |
| 인쇄 | `Settings$PrintSettingsActivity` | "인쇄 서비스", "기본 인쇄 서비스", "서비스 추가" | **CONFIRMED** |
| 앱 모두보기 | `Settings$ManageApplicationsActivity` | all-apps list (간편 모드 + installed app labels) | **CONFIRMED** (= 모든 앱) |
| 편안한 화면 | `Settings$NightDisplaySettingsActivity` | "야간 조명 사용", "야간 조명을 사용하면 화면이 황색광으로…" | **DOCUMENT_DRIFT_CANDIDATE** |
| 실시간 자막 | `Settings$CaptioningSettingsActivity` | "자막 보기", "자막 크기 및 스타일", "읽기 쉽도록 자막 크기 및 스타일을 맞춤설정하세요" | **WRONG_TARGET → TAP_ONLY** |
| 보청기 | (not launched — NO_RESOLVER) | — | **NO_RESOLVER → TAP_ONLY** |

### Verdict notes
- **인쇄 / 앱 모두보기 = CONFIRMED**: resolver + `am start` ok + focus = expected
  activity + dump ok + target-leaf text present. Device-verified deepen anchors on F0.
- **편안한 화면 = DOCUMENT_DRIFT_CANDIDATE** (not WRONG_TARGET): the action reaches a
  valid screen (NightDisplaySettingsActivity), but the on-device label is **"야간 조명"**
  (Night Light), while the source TC says "편안한 화면". Feature is plausibly the
  equivalent blue-light reduction, so this is a doc/UI label drift, not a wrong screen.
  **Semantic equivalence is a separate review; seed promotion withheld.**
- **실시간 자막 = WRONG_TARGET → TAP_ONLY**: `CAPTIONING_SETTINGS` lands on caption
  styling (자막 크기 및 스타일), not Live Caption (실시간 자막). The hypothesis is refuted;
  Live Caption has no confirmed public action → tap-discovery follow-up.
- **보청기 = NO_RESOLVER → TAP_ONLY**: no public Settings action on F0.

## Outcome
| verdict | candidates |
| --- | --- |
| CONFIRMED | 인쇄, 앱 모두보기 (→ v1.2 deepen seed) |
| DOCUMENT_DRIFT_CANDIDATE | 편안한 화면 (seed promotion withheld; semantic-equivalence review) |
| WRONG_TARGET → TAP_ONLY | 실시간 자막 |
| NO_RESOLVER → TAP_ONLY | 보청기 |

- Promoted seed: `THOR2_K - Settings/menu_tree_deepen_seed_v1_2.yaml` (CONFIRMED only).
- canonical `menu_tree_seed.yaml` untouched. No commit.
