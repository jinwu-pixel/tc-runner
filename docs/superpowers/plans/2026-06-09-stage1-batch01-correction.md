# STAGE1 batch01 정정 (D1/D2 정렬 + Phase 1 단말 환류) Implementation Plan

> **For agentic workers:** 본 플랜은 데이터(YAML) 정정 작업이다. 코드 변경/테스트 추가 없음.
> "테스트" = 정적 검증 명령(grep/yaml-parse/diff). Steps use checkbox (`- [ ]`) syntax.

**Goal:** batch01 16개 STAGE1 draft를 batch02 스키마(reference)로 정렬하고, Phase 1(F0)
단말 진입 실측을 entry 계약에 환류한다 — 단, **정적 anchor_state는 enriched CSV(SoT)에서
가져오고 단말 evidence로 덮어쓰지 않는다.**

**Architecture:** batch02 audit_meta 키셋을 unified reference로 채택. batch01만 편집(batch02
무변경). 편집 방식 = 파일별 surgical `Edit`(주석·flow 포맷·키 순서 보존, 최소 diff) —
`yaml.dump` 라운드트립 **금지**(주석 소실 + 전체 reformat). 정적 anchor_state/matched_screen_id =
`settings_anchor_gap_enriched_2026-06-09.csv`. 단말 verdict = per-file 헤더 주석 + entry_type/
shell_hint에 layering(별도 구조 필드 신설 안 함).

**Tech Stack:** YAML(CTF draft), ripgrep/grep, python `yaml.safe_load`(parse 검증 only),
git diff. 단말 접근 0(F0 점유 중·단일단말 게이트).

---

## Decisions (locked)

| # | 결정 | 근거 |
| --- | --- | --- |
| D-1 | `anchor_state`/`matched_screen_id` = enriched CSV에서 인용, 발명 금지 | batch02도 동일 SoT로 채워짐; §2.3 |
| D-2 | 단말 verdict는 **별도 레이어**(헤더 주석 + entry_type/shell_hint), static anchor_state **덮어쓰기 금지** | 정/관찰 혼용 방지(3-way 분리 규율) |
| D-3 | unified schema = batch02 키셋. batch01을 거기에 정렬, **batch02 무편집** | batch02가 최신·locked |
| D-4 | 편집 = surgical `Edit`(주석/포맷 보존). `yaml.dump` 금지 | diff 리뷰성·주석 보존 |
| D-5 | **commit 금지(작업 중)**. batch commit = 사용자 명시 승인 후만 | 글로벌 commit policy(스킬 "frequent commits" override) |
| D-6 | entry_type vocab에 `settings_deeplink_confirmed` 추가(batch01 device-verified deeplink용) | batch01만 실 deeplink 보유 |
| D-7 | `validate_tc.py` 미적용 | STAGE1 CTF draft ≠ compiled TC schema(execution_type/manual_detail). 돌리면 오탐 FAIL |

## Unified audit_meta 스키마 (batch02 reference, 15 keys, 순서 고정)

```
automation_class       # SEMI_AUTO_CANDIDATE (D1: batch01 FULL_AUTO_CANDIDATE → 강하)
safety_class           # NAVIGATION_ONLY (유지)
recovery_likelihood    # HIGH (신규 추가)
entry_type             # 아래 vocab (Phase1 환류)
verifier_type          # verify_text (유지)
anchor_state           # CSV 인용 (신규 추가)
menu_tree_anchor       # anchor_state에서 파생: TARGET_REACHED→matched_screen_id / PARTIAL→baseline_partial / MISSING→none
matched_screen_id      # CSV baseline_screen_id (screen_id 또는 null) — 한글 영역명에서 교체
deepen_anchor_link     # none (신규 추가)
risk_note              # 규칙: leaf에 On/Off control 있으면 control_presence string, 없으면 "none"
export_status          # STAGE1_DRAFT (유지)
evidence_level         # STATIC_ONLY (유지)
validation_required    # device_2run_green (유지)
target_repo            # thor2j-tc-appium (유지)
focusrule_evidence_transfer  # false (유지)
```

**entry_type vocabulary (locked):**
- `settings_deeplink_confirmed` — 공개 action 단말 검증됨(082/143/145/149)
- `tap_navigation_required` — 부모 도달, leaf tap 필요(081/085/086/922/923)
- `baseline_reached_parent_then_tap` — 부모 baseline-reached, leaf tap(827/955/956/957/962)
- `tap_navigation_unresolved` — deeplink 부재·entry 미해소(848/871)

**intent type (normalized_intent.type) 규칙:**
- `shell_candidate` — deeplink 기반(082/143/145/149 = confirmed hint; 848/871 = UNRESOLVED hint). `shell_hint` 유지.
- `navigate` — tap 기반(081/085/086/827/922/923/955/956/957/962). `target` + `value: null`, **`shell_hint` 제거**(batch02 navigate 형식).

## 16건 정정 매핑 (per-tc, locked)

| tc | leaf | area | anchor_state | matched_screen_id | menu_tree_anchor | entry_type | intent | Phase1 환류 핵심 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 081 | 최근 실행한 앱 | 앱 | PARTIAL | settings_d1_apps | baseline_partial | tap_navigation_required | navigate | APPLICATION_SETTINGS=WRONG_TARGET(모든앱 리스트). leaf는 앱 대시보드(home→앱 tap) **present 확인** |
| 082 | 모두 보기 | 앱 | PARTIAL | settings_d1_apps | baseline_partial | settings_deeplink_confirmed | shell_candidate | MANAGE_APPLICATIONS_SETTINGS→ManageApplicationsActivity(=모든앱 list, leaf 자체) **CONFIRMED**. static anchor PARTIAL 유지 |
| 085 | 기기 사용 시간 | 앱 | PARTIAL | settings_d1_apps | baseline_partial | tap_navigation_required | navigate | WRONG_TARGET. leaf UNVERIFIED(2 viewport 미노출, 의심 웰빙 하위) Phase2 |
| 086 | 사용하지 않는 앱 | 앱 | PARTIAL | settings_d1_apps | baseline_partial | tap_navigation_required | navigate | WRONG_TARGET. leaf UNVERIFIED Phase2 |
| 143 | 대화 | 알림 | MISSING | null | none | settings_deeplink_confirmed | shell_candidate | NOTIFICATION_SETTINGS→ConfigureNotificationSettingsActivity, leaf "대화" present. **알림은 17-screen baseline 부재 → baseline-add 후보(별도)** |
| 145 | 기기 및 앱 알림 | 알림 | MISSING | null | none | settings_deeplink_confirmed | shell_candidate | NOTIFICATION_SETTINGS, leaf "기기 및 앱 알림" present. baseline-add 후보 |
| 149 | 방해금지 모드 | 알림 | MISSING | null | none | settings_deeplink_confirmed | shell_candidate | NOTIFICATION_SETTINGS 부모 CONFIRMED; leaf "방해금지 모드" below-fold **UNVERIFIED** Phase2 scroll |
| 827 | 모두 보기 | 위치 | TARGET_REACHED | settings_d1_location | matched_screen_id | baseline_reached_parent_then_tap | navigate | LOCATION_SOURCE_SETTINGS CONFIRMED 부모; leaf "모두 보기" control present |
| 848 | 의료 정보 | 안전 및 긴급 상황 | MISSING | null | none | tap_navigation_unresolved | shell_candidate | EMERGENCY/MEDICAL_INFORMATION_SETTINGS=No activity(F0). UNRESOLVED 정당. **PII(의료) redaction** Phase2 |
| 871 | 비상 연락처 | 안전 및 긴급 상황 | MISSING | null | none | tap_navigation_unresolved | shell_candidate | 공개 action 부재(F0). UNRESOLVED 정당. **PII(연락처) redaction** Phase2 |
| 922 | 대시보드 | 디지털 웰빙 및 자녀 보호 기능 | PARTIAL | settings_d1_wellbeing | baseline_partial | tap_navigation_required | navigate | WELLBEING/DIGITAL_WELLBEING=No activity(F0) coverage-gap. Phase2 tap |
| 923 | 취침 모드 | 디지털 웰빙 및 자녀 보호 기능 | PARTIAL | settings_d1_wellbeing | baseline_partial | tap_navigation_required | navigate | coverage-gap. Phase2 tap |
| 955 | 맞춤설정 | Google | TARGET_REACHED | settings_d1_google | matched_screen_id | baseline_reached_parent_then_tap | navigate | GOOGLE_SETTINGS=No activity. 외부 Google pkg. **account redaction** Phase2 |
| 956 | 광고 | Google | TARGET_REACHED | settings_d1_google | matched_screen_id | baseline_reached_parent_then_tap | navigate | 외부 pkg. Phase2 |
| 957 | 기기 및 공유 | Google | TARGET_REACHED | settings_d1_google | matched_screen_id | baseline_reached_parent_then_tap | navigate | 외부 pkg. Phase2 |
| 962 | 위급 상황 정보 | Google | TARGET_REACHED | settings_d1_google | matched_screen_id | baseline_reached_parent_then_tap | navigate | 외부 pkg. **account redaction** Phase2 |

`risk_note`: 081/082/085/086/848/871 = `"none"`; 143/145/149(알림 토글)·827(앱별 위치 권한 토글)·
922/923(웰빙 On/Off)·955~962(광고 등 토글) = batch02 control_presence string
(`"control_presence_only — On/Off controls verified for existence only, current state NOT asserted"`).
편집 시 각 draft `expected_result_raw`에 On/Off·버튼·사용 토큰 유무로 최종 확정.

---

## Task 1: 파일럿 3건 surgical Edit

대표 3 패턴으로 컨벤션·diff를 잠근다: 081(WRONG_TARGET→tap), 143(deeplink-confirmed/MISSING),
082(deeplink-confirmed/PARTIAL).

**Files:**
- Modify: `THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_081_canonical.yaml`
- Modify: `THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_143_canonical.yaml`
- Modify: `THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_082_canonical.yaml`

- [ ] **Step 1: 081 헤더 주석 추가** — 파일 1행(`# STAGE1 CTF draft …`) 다음 줄에 삽입:

```
# F0 2026-06-09 (Phase1): android.settings.APPLICATION_SETTINGS = WRONG_TARGET
# (→ ManageApplicationsActivity = 모든앱 list, NOT the 앱 dashboard). leaf
# '최근 실행한 앱' confirmed PRESENT on 앱 dashboard via 설정 home → '앱' tap.
# static anchor_state=PARTIAL (settings_d1_apps) retained per enriched CSV.
```

- [ ] **Step 2: 081 normalized_intent 정정** — `type: shell_candidate` → `type: navigate`;
  `shell_hint:` 줄 **삭제**; `target: "설정 > 앱 > 최근 실행한 앱"` 유지하고 그 아래 `value: null` 추가.

- [ ] **Step 3: 081 audit_meta 정렬** — 아래로 교체(키 순서·신규키 반영):

```yaml
audit_meta:
  automation_class: SEMI_AUTO_CANDIDATE
  safety_class: NAVIGATION_ONLY
  recovery_likelihood: HIGH
  entry_type: tap_navigation_required
  verifier_type: verify_text
  anchor_state: PARTIAL
  menu_tree_anchor: baseline_partial
  matched_screen_id: "settings_d1_apps"
  deepen_anchor_link: none
  risk_note: "none"
  export_status: STAGE1_DRAFT
  evidence_level: STATIC_ONLY
  validation_required: device_2run_green
  target_repo: thor2j-tc-appium
  focusrule_evidence_transfer: false
```

- [ ] **Step 4: 143 헤더 주석 추가** — 1행 다음:

```
# F0 2026-06-09 (Phase1): android.settings.NOTIFICATION_SETTINGS = CONFIRMED
# → ConfigureNotificationSettingsActivity; leaf '대화' present (control_presence).
# NOTE: '알림' is absent from the 17-screen menu-tree baseline → baseline-add
# candidate (separate menu_tree_seed track). static anchor_state=MISSING retained.
```

- [ ] **Step 5: 143 normalized_intent 정정** — `type: shell_candidate` 유지;
  `shell_hint:` → `"CONFIRMED — android.settings.NOTIFICATION_SETTINGS reaches ConfigureNotificationSettingsActivity; leaf '대화' present (F0 2026-06-09)"`.

- [ ] **Step 6: 143 audit_meta 정렬**:

```yaml
audit_meta:
  automation_class: SEMI_AUTO_CANDIDATE
  safety_class: NAVIGATION_ONLY
  recovery_likelihood: HIGH
  entry_type: settings_deeplink_confirmed
  verifier_type: verify_text
  anchor_state: MISSING
  menu_tree_anchor: none
  matched_screen_id: null
  deepen_anchor_link: none
  risk_note: "control_presence_only — On/Off controls verified for existence only, current state NOT asserted"
  export_status: STAGE1_DRAFT
  evidence_level: STATIC_ONLY
  validation_required: device_2run_green
  target_repo: thor2j-tc-appium
  focusrule_evidence_transfer: false
```

- [ ] **Step 7: 082 헤더 주석 추가** — 1행 다음:

```
# F0 2026-06-09 (Phase1): android.settings.MANAGE_APPLICATIONS_SETTINGS = CONFIRMED
# → ManageApplicationsActivity (= '모든 앱' list, the leaf itself; no tap needed).
# static anchor_state=PARTIAL (settings_d1_apps, single-pass) retained per CSV.
```

- [ ] **Step 8: 082 normalized_intent 정정** — `type: shell_candidate` 유지;
  `shell_hint:` → `"CONFIRMED — android.settings.MANAGE_APPLICATIONS_SETTINGS reaches ManageApplicationsActivity (= 모든 앱 list = leaf); F0 2026-06-09"`.

- [ ] **Step 9: 082 audit_meta 정렬**:

```yaml
audit_meta:
  automation_class: SEMI_AUTO_CANDIDATE
  safety_class: NAVIGATION_ONLY
  recovery_likelihood: HIGH
  entry_type: settings_deeplink_confirmed
  verifier_type: verify_text
  anchor_state: PARTIAL
  menu_tree_anchor: baseline_partial
  matched_screen_id: "settings_d1_apps"
  deepen_anchor_link: none
  risk_note: "none"
  export_status: STAGE1_DRAFT
  evidence_level: STATIC_ONLY
  validation_required: device_2run_green
  target_repo: thor2j-tc-appium
  focusrule_evidence_transfer: false
```

- [ ] **Step 10: 파일럿 3건 parse + diff 검증**

Run: `venv/Scripts/python.exe -c "import yaml; [yaml.safe_load(open(f,encoding='utf-8')) for f in ['THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_%s_canonical.yaml'%i for i in ('081','143','082')]]; print('parse OK')"`
Expected: `parse OK`

Run: `git -C . --no-pager diff --stat -- "THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_081_canonical.yaml"`
Expected: 변경 줄 수가 작음(헤더 4줄 + intent 2~3줄 + audit_meta 키만). 전체 파일 재작성 아님.

- [ ] **Step 11: 사용자 체크포인트** — 파일럿 3건 diff 보고. 컨벤션 승인 후 Task 2 진입.

---

## Task 2: 나머지 13건 surgical Edit

매핑표대로 13건(085/086/145/149/827/848/871/922/923/955/956/957/962) 동일 방식 편집.
각 파일: ① 헤더 주석(F0 verdict) ② normalized_intent(intent type/shell_hint/target+value) ③ audit_meta 15키 정렬.

**Files (Modify, batch01):**
`ALTBASIC_SET_{085,086,145,149,827,848,871,922,923,955,956,957,962}_canonical.yaml`

- [ ] **Step 1: navigate 그룹 (085/086/827/922/923/955/956/957/962)** — intent `type: navigate`,
  `shell_hint` 삭제, `target` 유지 + `value: null`. audit_meta는 매핑표 값.
- [ ] **Step 2: shell_candidate 그룹 (145/149/848/871)** — intent `type: shell_candidate`,
  `shell_hint` 갱신(145=confirmed, 149=confirmed parent+leaf unverified, 848/871=UNRESOLVED No-activity).
  audit_meta는 매핑표 값.
- [ ] **Step 3: 각 파일 헤더 주석** — 매핑표 "Phase1 환류 핵심"을 2~4줄 주석으로(F0 2026-06-09 prefix).
- [ ] **Step 4: risk_note 확정** — 각 draft `expected_result_raw`에 On/Off·버튼·사용 토큰 있으면
  control_presence string, 없으면 `"none"`(매핑표 규칙).

---

## Task 3: 전수 검증 (16건)

- [ ] **V1 금지토큰 0**

Run: `rg -nE "RUNNABLE_NOW|runnable:\s*true|tc_class:\s*FULL_AUTO|am start" "THOR2 - ALT Basic TC Audit/stage1_settings_batch01"`
Expected: no matches.

- [ ] **V2 automation_class 전건 SEMI_AUTO_CANDIDATE (FULL 0)**

Run: `rg -n "automation_class:" "THOR2 - ALT Basic TC Audit/stage1_settings_batch01" | rg -v "SEMI_AUTO_CANDIDATE"`
Expected: no matches.

- [ ] **V3 신규 3키 16건 존재**

Run: `for k in anchor_state deepen_anchor_link recovery_likelihood; do echo -n "$k="; rg -c "$k:" "THOR2 - ALT Basic TC Audit/stage1_settings_batch01" | rg -c ":1"; done`
Expected: 각 키 16 파일 hit.

- [ ] **V4 anchor_state가 CSV와 일치(스팟)**

Run: `rg -n "anchor_state:" "THOR2 - ALT Basic TC Audit/stage1_settings_batch01/ALTBASIC_SET_{827,955,143,922}_canonical.yaml"`
Expected: 827=TARGET_REACHED, 955=TARGET_REACHED, 143=MISSING, 922=PARTIAL.

- [ ] **V5 16건 YAML parse OK**

Run: `venv/Scripts/python.exe -c "import glob,yaml; n=0;\nimport pathlib\n[ (yaml.safe_load(open(f,encoding='utf-8')), ) for f in glob.glob('THOR2 - ALT Basic TC Audit/stage1_settings_batch01/*.yaml')]; print('all parse OK')"`
Expected: `all parse OK`

- [ ] **V6 diff가 surgical(전체 재작성 아님)**

Run: `git --no-pager diff --stat -- "THOR2 - ALT Basic TC Audit/stage1_settings_batch01"`
Expected: 16 파일, 각 파일 added/deleted 줄이 제한적(헤더+intent+audit_meta만). 대량 reformat 없음.

- [ ] **V7 감사 doc 갱신** — `STAGE1_DRAFT_AUDIT_2026-06-09.md` §3 D1/D2를 "applied(batch01 16)"로,
  §4 환류를 "반영됨"으로 갱신. (문서 편집, commit 아님.)

---

## Task 4: 보고 + commit 게이트

- [ ] **Step 1: 결과 보고** — V1~V7 결과 + 변경 파일 목록(16 batch01 + 감사 doc).
- [ ] **Step 2: commit DEFER** — 글로벌 정책상 작업 중 commit 금지. batch commit은
  **사용자 명시 "commit now"** 후 명시 path만 stage(§7). 자체 판단 commit/push 0.

---

## Success Criteria

- batch01 16건: automation_class=SEMI_AUTO_CANDIDATE, audit_meta 15키 = batch02와 동형,
  anchor_state/matched_screen_id = CSV 인용, entry_type/intent = Phase1 환류.
- 금지토큰 0, 필수 guard 16/16, YAML parse 16/16.
- diff = surgical(주석 보존, 최소 변경). batch02 무변경.
- 단말 evidence는 헤더 주석 + entry_type/shell_hint에만(별도 구조 필드 신설 0, static anchor_state 무변).
- export_status 승격 0(STAGE1_DRAFT 유지). commit 0.

## Non-Goals

- export_status 승격(= device_2run_green/thor2j 후 별도).
- batch02 편집 / menu_tree_seed.yaml 편집(알림 baseline-add는 별도 후보 트랙).
- 단말 접근(F0 점유 중; Phase2는 별도).
- classifier(`settings_anchor_gap.py`) 변경.
- REVIEW 10 / EXCLUDE 10 재설계.
- commit / push.

## Open question (사용자)

- 143/145/149에서 NOTIFICATION_SETTINGS가 device-confirmed → `menu_tree_seed.yaml`에
  `settings_d1_notification` baseline 추가할지? **별도 트랙 권장**(본 플랜 범위 밖, Non-Goal).
