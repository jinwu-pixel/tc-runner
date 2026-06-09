# STAGE1 batch01 — device read-only entry probe (F0, 2026-06-09)

Phase 1 read-only device probe of the **16 batch01 STAGE1 drafts**
(`stage1_settings_batch01/`). Resolves each draft's candidate entry on-device and
classifies whether the named `am start` action actually reaches the intended
parent/leaf.

- This is **manual evidence observed** (anchor entry resolution), **not** validate
  PASS / runtime PASS. All 16 drafts remain `STAGE1_DRAFT`; **no promotion**.
- device: `B06201249E0002F0` (AT_M140 / thor2, THOR2_K). B27
  (`B2700125BW000083`) NOT addressed — every adb used `-s B06201249E0002F0`.
- protocol: read-only. `cmd package resolve-activity`, `am start -W -S`, `dumpsys`,
  `uiautomator dump` only. **persistent mutation: 0** (`-S` = process/task reset
  only; no tap / input / toggle / settings put / pm / reboot in Phase 1).
- track: ALT Basic STAGE1 draft (separate from menu-tree v1.2 deepen anchor track).

## Resolve-only outcome (candidate actions)

| action | resolver | resolved activity |
| --- | --- | --- |
| `APPLICATION_SETTINGS` | present | `Settings$ManageApplicationsActivity` |
| `MANAGE_APPLICATIONS_SETTINGS` | present | `Settings$ManageApplicationsActivity` (동일) |
| `LOCATION_SOURCE_SETTINGS` | present | `Settings$LocationSettingsActivity` |
| `NOTIFICATION_SETTINGS` | present | `Settings$ConfigureNotificationSettingsActivity` |
| `WELLBEING_SETTINGS` / `DIGITAL_WELLBEING_SETTINGS` | **No activity found** | — |
| `EMERGENCY_SETTINGS` / `MEDICAL_INFORMATION_SETTINGS` | **No activity found** | — |
| `GOOGLE_SETTINGS` | **No activity found** | — |

## Per-draft verdict (16)

summary: **CONFIRMED 4 · WRONG_TARGET 3 · 부모CONFIRMED/leaf UNVERIFIED 1 · NO_RESOLVER 8**

| tc_id | leaf (영역) | 후보 action | observed focus | leaf 관찰 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 082 | 앱 > 모두 보기 | APPLICATION_SETTINGS | ManageApplicationsActivity | "모든 앱" 리스트 = leaf 화면 자체 | CONFIRMED (v1.2 일치) |
| 827 | 위치 > 모두 보기 | LOCATION_SOURCE_SETTINGS | LocationSettingsActivity | "모두 보기" entry present (leaf 내부 미진입) | CONFIRMED (control presence) |
| 143 | 알림 > 대화 | NOTIFICATION_SETTINGS | ConfigureNotificationSettingsActivity | "대화" entry present (leaf 내부 미진입) | CONFIRMED (control presence) |
| 145 | 알림 > 기기 및 앱 알림 | NOTIFICATION_SETTINGS | ConfigureNotificationSettingsActivity | "기기 및 앱 알림" entry present | CONFIRMED (control presence) |
| 081 | 앱 > 최근 실행한 앱 | APPLICATION_SETTINGS | ManageApplicationsActivity | leaf 부재 (모든앱 리스트로 진입) | WRONG_TARGET |
| 085 | 앱 > 기기 사용 시간 | APPLICATION_SETTINGS | ManageApplicationsActivity | leaf 부재 | WRONG_TARGET |
| 086 | 앱 > 사용하지 않는 앱 | APPLICATION_SETTINGS | ManageApplicationsActivity | leaf 부재 | WRONG_TARGET |
| 149 | 알림 > 방해금지 모드 | NOTIFICATION_SETTINGS | ConfigureNotificationSettingsActivity | 초기 viewport 부재 (scroll 금지로 미확인) | 부모 CONFIRMED / leaf UNVERIFIED |
| 848 | 안전긴급 > 의료 정보 | (EMERGENCY/MEDICAL_INFO hyp) | — | — | NO_RESOLVER |
| 871 | 안전긴급 > 비상 연락처 | (hyp) | — | — | NO_RESOLVER |
| 922 | 웰빙 > 대시보드 | WELLBEING/DIGITAL_WELLBEING | — | — | NO_RESOLVER (coverage-gap 재확인) |
| 923 | 웰빙 > 취침 모드 | (동일) | — | — | NO_RESOLVER |
| 955 | Google > 맞춤설정 | GOOGLE_SETTINGS | — | — | NO_RESOLVER |
| 956 | Google > 광고 | GOOGLE_SETTINGS | — | — | NO_RESOLVER |
| 957 | Google > 기기 및 공유 | GOOGLE_SETTINGS | — | — | NO_RESOLVER |
| 962 | Google > 위급 상황 정보 | GOOGLE_SETTINGS | — | — | NO_RESOLVER |

## Interpretation

- **CONFIRMED 4 (082 / 827 / 143 / 145)** — 082는 leaf 화면 자체 도달; 827·143·145는
  부모 도달 + leaf entry 노출(`control_presence_only` 계약 충족, leaf 내부 미진입).
- **WRONG_TARGET 3 (081 / 085 / 086)** — `APPLICATION_SETTINGS`가 이 빌드에서 앱 대시보드가
  아니라 **모든앱 리스트**(`ManageApplicationsActivity`)로 해석됨. 해당 leaf는 거기 없음.
  설정 홈에 "앱"(부제: 어시스턴트, 최근 앱, 기본 앱) 행 존재 → 올바른 진입은 설정 > 앱 대시보드
  tap = **Phase 2**. draft `shell_hint` action 정정 필요.
- **leaf UNVERIFIED 1 (149)** — 부모 알림 화면 도달, "방해금지 모드"는 초기 viewport 부재.
  Phase 1은 scroll(input) 금지라 below-fold 확정 불가 → **Phase 2** scroll 탐색.
- **NO_RESOLVER 8 (848 / 871 / 922 / 923 / 955 / 956 / 957 / 962)** — 공개 `android.settings.*`
  action 부재 재확인(웰빙=기존 coverage-gap 일치, Google=외부 pkg). draft가 action을 발명하지
  않은 게 옳았음 → 전부 **Phase 2 tap-discovery**.

## Status

- batch01 16 drafts: `STAGE1_DRAFT` 유지, device_2run_green 미충족, 승격 0.
- Phase 1 산출 = 본 doc. commit/push 없음.
- on-device scratch dump 정리됨(기존 stray `/sdcard/window_dump.xml` 1개는 이전 deepen probe
  잔존, 본 세션 무관).

## Phase 2 pilot (next)

대상 28건(batch02 16 + batch01 미해결 12) 중 **파일럿 4건 먼저**로 방법론·기록 포맷을 잠근다:

- 081 / 085 / 086 — 설정 홈 → "앱" 대시보드 tap → 최근 실행한 앱 / 기기 사용 시간 /
  사용하지 않는 앱 entry 노출 확인 (한 번의 navigation으로 3 leaf entry 동시 확인).
- 149 — 알림 화면에서 controlled scroll → "방해금지 모드" below-fold 존재 여부.

수칙: tap은 `NAVIGATION_ONLY` 노드에만(switch/checkbox/저장/선택/위저드-시작 금지),
selector는 text+resource-id+bounds 함께 기록(좌표 단독 X), PII leaf(871 비상연락처·848 의료정보·
Google 계정)는 redaction gate 경유. `-s B06201249E0002F0` 고정, B27 미접촉.

### pilot run — partial (F0 dropout, **INTERRUPTED**)

- **entry method (WRONG_TARGET 정정 검증)**: 설정 홈 → tap "앱" 행. selector =
  `text="앱"` / `resource-id="android:id/title"` / title bounds `[99,651][133,705]`
  (tap ≈ 116,678). 도달 = App dashboard(homepage activity host). → **설정 > 앱 tap이
  올바른 진입**임을 단말 확인(081/085/086의 `APPLICATION_SETTINGS` WRONG_TARGET 정정).
- **scroll method**: single `input swipe 240 600 240 300 400`이 480x800에서 유효
  (double-swipe 불요; content advanced).
- **findings**:

  | tc | leaf | viewport | 결과 |
  | --- | --- | --- | --- |
  | 081 | 최근 실행한 앱 | initial | **present** (앱 대시보드 최상단) |
  | 082 | 모두 보기 | initial | "앱 44개 모두 보기" present (재확인) |
  | 085 | 기기 사용 시간 | 2 viewport 미노출 | **UNVERIFIED** — 2nd scroll 전 F0 dropout. 의심=디지털 웰빙 하위 |
  | 086 | 사용하지 않는 앱 | 2 viewport 미노출 | **UNVERIFIED** — 동일 |

  관찰된 App dashboard rows(2 viewport): 최근 실행한 앱 / 앱 44개 모두 보기 /
  기본 앱(Chrome, 전화 및 메시지) / 디지털 웰빙 및 자녀 보호 기능 / 일반.
- **149 (알림 scroll)**: 미착수 (dropout).
- focus probe note: `dumpsys window | grep mCurrentFocus` 신뢰; 이 빌드에서
  `dumpsys activity activities | grep mResumedActivity`는 미매칭.
- **INTERRUPTED**: F0 USB dropout (`device 'B06201249E0002F0' not found`) 발생, 현재
  B27만 연결 → 작업 중단, F0 재연결 대기. persistent mutation 0 (navigation tap/scroll만).

