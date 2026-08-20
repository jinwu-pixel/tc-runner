# C02 (11.Hard Key) F0 v1 discovery summary — 2026-08-19

## Scope and wording

- Scope: batch10 Part B C02, `source_sheet=11.Hard Key`, 29 TC discovery run.
- Evidence level: `manual evidence observed` only.
- This was not a 2-run. It is not `runtime PASS`, `validate PASS`, or a `RUNNABLE_NOW` promotion.
- Inputs were keyevent-only. No tap, swipe, direct `am start`, setting change, send, delete, call, reboot, install, stage, commit, or push was performed.

## Identity gate

| Item | Observed |
|---|---|
| attached devices | F0 only |
| serial | `B06201249E0002F0` |
| model | `AT-M140` |
| build | `RY07260601S` |
| locale | `ko-KR` |
| package count | 219 |
| `io.appium` packages | 0 |

The handoff identity pins matched with drift 0.

## Result distribution

| Status | Count |
|---|---:|
| `LITERAL_CONFIRMED` | 2 |
| `LITERAL_PENDING` | 11 |
| `NOT_PRESENT` | 3 |
| `ENTRY_FAILED` | 3 |
| `DISCOVERY_BLOCKED` | 4 |
| `PRECONDITION_MISMATCH` | 2 |
| `DEVICE_FIT_SKIP` | 0 |
| `FOCUS_OBSERVED` | 4 |
| **Total** | **29** |

`FOCUS_OBSERVED` is added because HDK_035~038 are `focus_state` contracts, not literal verifiers. Folding them into a literal bucket would misstate the observation. The runsheet's reporting bucket list omitted this focus-only case.

## Driver-pattern inputs

### Confirmed key behavior

- `187` opened recent apps. The state contained `닫기 설정` and `모두 닫기`; the empty-state literal `최근항목이 없습니다` was not present.
- `207` opened `com.hnlens.contacts`.
- `27` opened `com.hnlens.camera`; no shutter or OK input followed.
- Candidate `65` opened `com.google.android.gm`, not the message app. Message-button keycode remains `KEYCODE_UNRESOLVED` and was not retried.
- `--longpress 3` did not open Quick Panel on the observed HOME surface.
- BACK (`4`) closed the power menu and collapsed the expanded notification shade.

### HOME focus model

The launcher uses a `node` model: the focused node itself moves; no list-container/selected-child model was observed.

- UP: no focus → `rl_home_app[전화]`; long UP → `weather_view`.
- DOWN: `rl_home_app[갤러리]` → `rl_home_app[전화]`; long DOWN → `연락처` node.
- LEFT: `rl_home_app[전화]` → `rl_first[1 - 30]`; long LEFT retained the same node.
- RIGHT: `rl_home_app[전화]` → `rl_home_app[메시지]`; long RIGHT → `t_all_apps[모든 앱]`.

The HOME command does not clear launcher focus. A driver must capture the current focused node instead of assuming a fixed baseline.

### Power-menu focus graph

Actual literals were `긴급 전화`, `전원 끄기`, and `다시 시작`.

- Initial focus: `긴급 전화`.
- RIGHT: `긴급 전화` → `전원 끄기`; further RIGHT inputs retained `전원 끄기`.
- LEFT from initial: retained `긴급 전화`.
- DOWN: `긴급 전화` → `다시 시작`.
- UP: `다시 시작` → `긴급 전화`.

No OK input was sent in the power menu. Each case exited by BACK and the popup was absent afterward.

### Settings navigation

The first `설정` tile OK resumed a stale screen-timeout dialog. BACK three times traversed dialog → `SubSettings` → `Settings` → HOME. Re-entering the focused `설정` tile then reached the Settings root.

Observed root focus order:

1. 네트워크 및 인터넷
2. 연결된 기기
3. 해외 로밍
4. 앱
5. 안심 기능
6. 알림
7. 알림 읽어주기
8. 배터리
9. 저장용량
10. 소리 및 진동
11. 디스플레이
12. 배경화면 및 스타일
13. 모드 설정
14. 접근성
15. 보안
16. 개인 정보 보호
17. 위치
18. 안전 및 긴급 상황

Settings also used the `node` focus model.

- `소리 및 진동` OK exposed volume controls; no value changed.
- `디스플레이` OK exposed brightness, keypad-light, lock-display, and screen-timeout controls; no value changed.
- `배경화면 및 스타일` opened `com.hnlens.wallpaper`; no wallpaper change was applied.
- `안심 기능` opened `com.hnlens.safetyfeature`; the exact literal was present and no SOS-related option was entered.
- `안전 및 긴급 상황` exposed the exact `긴급 상황 정보` literal. No further OK was sent.
- Wi-Fi is not a standalone root item. The actual read-only route was `네트워크 및 인터넷` → `Wi-Fi`; SSIDs were not transcribed and no toggle, AP selection, or connection action occurred.

## Divergences and blocked cases

| TC | Observation |
|---|---|
| HDK_019 | HOME long-press did not open Quick Panel. |
| HDK_021 | Actual empty label was `연락처가\n없습니다.`; `새 연락처 만들기` was exact. |
| HDK_023 | Keycode 65 opened Gmail; message entry unresolved. |
| HDK_041, HDK_042 | `Navi 키(모든)` has no mapped keycode; blocked without guessing. |
| HDK_046 | Entry requires swipe to the second HOME page; blocked by keyevent-only contract. The launcher remains 3-page. |
| HDK_050 | BACK from expanded notifications returned directly to HOME, not a split panel with Wi-Fi focus. |
| HDK_052 | Repeated RIGHT stopped at `전원 끄기`; no three-item cycle. |
| HDK_053 | LEFT from initial `긴급 전화` retained the same focus. |
| HDK_055, HDK_056 | Message app entry unavailable after the sole keycode candidate failed. |
| HDK_062, HDK_070 | Empty-contact screen had no `더보기` control; required focus precondition mismatched. |
| HDK_064 | Empty-contact premise matched, but `Navi 키(전체)` remained unresolved. |
| HDK_094 | First OK reproduced stale Settings resume; BACK-loop recovery was required. Expected simplified list labels/path did not match the actual root. |
| HDK_096 | One DOWN moved `소리 및 진동` → `디스플레이`; the source's bottom-boundary clause was not exercised by its single-step procedure. |
| HDK_098 | Actual Wi-Fi route requires two OK presses and uses the literal `Wi-Fi`, not `WIFI 설정`. |

## New and confirmed cautions

- Message and contact raw dumps remain local-only. No personal content or SSIDs are transcribed into the ledger or this summary.
- The remote `/data/local/tmp` directory contained artifacts dated 2026-07-20/23 before cleanup. Only this session's exact `/data/local/tmp/ui.xml` was removed; pre-existing artifacts were not touched.
- MediaStore was not at the runsheet's stated baseline 0. The final query returned 17 rows, all dated 2026-07-22 (16) or 2026-07-31 (1). Rows created on 2026-08-19: 0. This is a stale-baseline `NOTE`, not evidence of session mutation.
- No `/sdcard` dump or screenshot path was used.

## Exit gates

| Gate | Observed |
|---|---|
| final surface | `com.hnlens.simplemode` HOME |
| packages pre/post | 219 / 219 |
| package diff | 0 |
| package snapshot SHA-256 | both `936DDFBABF926B51EB93C3905B50AF378E5E2736AE64F0D115764081EA690956` |
| session remote temp residual | 0 (`/data/local/tmp/ui.xml` absent) |
| MediaStore rows created this session | 0 |
| stage / commit / push | 0 / 0 / 0 |

## Outputs

- Local-only evidence: `THOR2 - ALT Basic TC Audit/catalog/f0_c02_hdk_nav_2026-08-19/`
- Ledger: `THOR2 - ALT Basic TC Audit/DISCOVERY_C02_LEDGER_2026-08-19.csv`
- Summary: `THOR2 - ALT Basic TC Audit/DISCOVERY_C02_HDK_SUMMARY_2026-08-19.md`

STOP: driver slice design, YAML backfill, 2-run promotion, commit, and push remain outside this session.
