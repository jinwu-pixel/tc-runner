# Menu-Tree Baseline — Run Ledger (THOR2_K, time-series)

device menu-tree baseline 트랙의 **run_id 시계열 대장** (append-only). 단발 작업 아님 —
run_id 기준으로 reach / focus / text 변화 · coverage-gap · driver-fix 영향을 누적한다.
commit/push 단위와 분리한다. (Tier D: `catalog_schema.md` §1.)

## 운영 규칙
- run_id = UTC `YYYYMMDDTHHMMSSZ`. 1 run = Tier D bundle(JSON+MD) + `raw/` + 본 대장 1 entry.
- **비교 규칙**: full↔full 만 total count 직접 비교. **subset run 은 per-screen 증거로만 기록**(total 직접 비교 금지).
- **귀인**: reach 변화는 `device.build / locale / sim / seed_version / tool_commit` 를 함께 봐야 단말·build vs driver vs seed 분리 가능.
- **raw_policy**: raw XML = 기본 local carry(미커밋). JSON/MD digest + 본 대장 = append-only commit.
- **tool_code_state legend**: `clean(==commit)` / `dirty-carry-only`(`.gitignore`·`CLAUDE.md` 등 carry 만 dirty, explorer clean) / `dirty-code`(explorer/tool 코드 자체 dirty).
- **tool_commit** = 해당 run 을 생성한 explorer 코드를 담은 commit. (schema_version=1 JSON 엔 git SHA 필드 없음 → 본 대장에 기록. schema v2 `tool_commit` 필드는 별도 티켓.)

## Ledger (시계열 인덱스)
| run_id | type | scope | base/diff | tool_commit | reached/ext | fm | unreach | dump_rej | viol | artifact |
|---|---|---|---|---|---|---|---|---|---|---|
| 20260604T074020Z | full | 17 | — (first) | ad045a1 | 13/1 | 3 | 0 | 0 | 0 | `catalog/…074020Z.{json,md}` |
| 20260604T085840Z | subset(3) | google·device_info·wellbeing | vs 074020Z (per-screen) | ee59ac7 | 2/0 | 1 | 0 | 0 | 0 | `catalog/v1_1_verify/…085840Z.{json,md}` |
| 20260604T102316Z | full | 17 | vs 074020Z (full↔full) | 3a84b41† | 14/1 | 2 | 0 | 0 | 0 | `catalog/…102316Z.{json,md}` |

† explorer behavior == ee59ac7 (3a84b41 = tc_loader drift fix, explorer 무영향). ⚠ run 102316Z 에 예상 밖 privacy REACHED→FOCUS_MISMATCH 1회 관측(OBSERVED, 미확정) — 상세 블록 참조.

---

## Run 20260604T074020Z — full v1 baseline
- **type / scope**: full / 17 screens
- **base_run_id / diff_against**: — (first baseline, no prior)
- **tool_commit**: `ad045a1` (pre-`$`-fix explorer)
- **tool_code_state**: clean (explorer == ad045a1; repo carry-dirty 무관)
- **seed_version**: 1 · **package**: com.android.settings · **target_mismatch_ack**: false
- **device**: serial `B06201249E0002F0` / build_id `UP1A.231005.007` (incr `RY07260600S`) / android 14 / locale ko-KR / sim LG U+ / viewport 480x800 / dpi 220
- **summary**: reached 13 / reached_external 1 / focus_mismatch 3 / unreachable 0 / dump_rejected 0
- **counts**: observed_texts_total 353 / elements_total 365 / scroll_passes_total 49 / denylist_recorded 29
- **violations**: 0
- **artifact_path**: `catalog/menu_tree_baseline_20260604T074020Z.json` (+ `.md`)
- **raw_policy**: raw 14 XML @ `catalog/raw/20260604T074020Z/` = local carry(미커밋)
- **focus_mismatch 3 screens** (후속 분석 대상):
  - `settings_d1_google`      FOCUS_MISMATCH · focus `…/Settings` (base) · el 0 · texts 0
  - `settings_d1_device_info` FOCUS_MISMATCH · focus `…/Settings` (base) · el 0 · texts 0
  - `settings_d1_wellbeing`   FOCUS_MISMATCH · focus `com.hnlens.simplemode/…MainActivity` (런처 home) · el 0 · texts 0
- **hypothesis/result**: 첫 full baseline 수립 → reached 13+1 고정. google/device_info/wellbeing FOCUS_MISMATCH (원인 미확정 → 후속 분석).
- **notes**: google/device_info 는 이후 `$` launch fidelity 결함으로 root-cause 됨(→ ee59ac7). wellbeing 은 coverage-gap 후보.

## Run 20260604T085840Z — subset v1.1 verify (Class A `$` fix)
- **type / scope**: subset / 3 screens (google · device_info · wellbeing)
- **base_run_id / diff_against**: 20260604T074020Z (**per-screen only** — total count 직접 비교 금지)
- **tool_commit**: `ee59ac7` (`$` launch fidelity fix)
- **tool_code_state**: clean (explorer == ee59ac7; 본 run 산출물이 ee59ac7 에 포함; repo carry-dirty 무관)
- **seed_version**: 1 · **package**: com.android.settings · **target_mismatch_ack**: false
- **device**: serial `B06201249E0002F0` / build_id `UP1A.231005.007` / android 14 / locale ko-KR / sim LG U+ / viewport 480x800 (**== 074020Z → 교란변수 통제**)
- **summary (subset)**: reached 2 / reached_external 0 / focus_mismatch 1 / unreachable 0 / dump_rejected 0 / screen_count 3
- **counts (subset)**: observed_texts_total 44 / elements_total 47 / scroll_passes_total 5 / denylist_recorded 6
- **violations**: 0
- **artifact_path**: `catalog/v1_1_verify/menu_tree_baseline_20260604T085840Z.json` (+ `.md`)
- **raw_policy**: raw 2 XML @ `catalog/v1_1_verify/raw/20260604T085840Z/` = local carry(미커밋). JSON/MD digest = ee59ac7 commit.
- **per-screen Δ vs 074020Z**:
  - `settings_d1_google`:      FOCUS_MISMATCH → **REACHED** | focus base `Settings` → `Settings$AccountDashboardActivity` | el 0 → 13 | texts 0 → 11
  - `settings_d1_device_info`: FOCUS_MISMATCH → **REACHED** | focus base `Settings` → `Settings$MyDeviceInfoActivity` | el 0 → 34 | texts 0 → 33
  - `settings_d1_wellbeing`:   FOCUS_MISMATCH → FOCUS_MISMATCH (**변화 없음**) | focus `hnlens.simplemode` home 동일 | el 0 → 0 | texts 0 → 0
- **hypothesis/result**: `$` fix 후 google/device_info REACHED 예상 → **확인됨** (alias focus 보존, el/texts 신규 수집). wellbeing FOCUS_MISMATCH 유지 → **coverage-gap 확정** (probe: shell-launch 가능한 exported activity / 공개 action / Settings `$`-alias 전무).
- **notes**: build/locale/seed 동일 → 전환은 driver `$` fix 귀인. wellbeing 은 deep-link enumeration 범위 밖 (v1.1+ tap-discovery 필요).

## Run 20260604T102316Z — full rerun (post Class A `$` fix)
- **type / scope**: full / 17 screens
- **base_run_id / diff_against**: 20260604T074020Z (full↔full)
- **tool_commit**: `3a84b41` (HEAD). ⚠ **explorer behavior change 는 ee59ac7 까지** — `3a84b41` 은 tc_loader drift fix 라 menu-tree explorer 동작 무영향.
- **tool_code_state**: clean (explorer == ee59ac7; repo carry-dirty 무관)
- **seed_version**: 1 · **package**: com.android.settings · **target_mismatch_ack**: false (preflight serial == F0)
- **device**: serial `B06201249E0002F0` / build_id `UP1A.231005.007` / android 14 / locale ko-KR / sim LG U+ / viewport 480x800 / dpi 220 (**== 074020Z → 교란변수 통제**)
- **ADB 경유**: 전 호출 `-s B06201249E0002F0` (ADB(device_serial=F0) 주입). Appium `B2700125BW000083` 미접촉.
- **summary**: reached 14 / reached_external 1 / focus_mismatch 2 / unreachable 0 / dump_rejected 0
- **counts**: observed_texts_total 368 / elements_total 383 / scroll_passes_total 49 / denylist_recorded 27
- **violations**: 0
- **artifact_path**: `catalog/menu_tree_baseline_20260604T102316Z.json` (+ `.md`)
- **raw_policy**: raw 15 XML @ `catalog/raw/20260604T102316Z/` = local carry(미커밋)
- **full↔full summary Δ vs 074020Z**: reached 13→14 (+1) · focus_mismatch 3→2 (−1) · reached_external 1→1 · unreachable 0 · dump_rejected 0 · observed_texts_total 353→368 (+15) · elements_total 365→383 (+18) · scroll_passes_total 49→49 · denylist_recorded 29→27 (−2)
- **per-screen reach transitions vs 074020Z**:
  - `settings_d1_google`:      FOCUS_MISMATCH → **REACHED** | focus base `Settings` → `Settings$AccountDashboardActivity` | el 0→13 | texts 0→11  ← `$` fix 효과 (ee59ac7)
  - `settings_d1_device_info`: FOCUS_MISMATCH → **REACHED** | focus base `Settings` → `Settings$MyDeviceInfoActivity` | el 0→34 | texts 0→33  ← `$` fix 효과 (ee59ac7)
  - `settings_d1_wellbeing`:   FOCUS_MISMATCH → FOCUS_MISMATCH (**유지**) | focus `hnlens.simplemode` home 동일 | coverage-gap 유지
  - `settings_d1_privacy`:     REACHED → **FOCUS_MISMATCH** ⚠ **예상 밖** | observed_focus `Settings$PrivacyDashboardActivity` → `Settings$MyDeviceInfoActivity` | launched_cmd 정상(`am start -a android.settings.PRIVACY_SETTINGS`)
- **hypothesis/result**: `$` fix 후 google/device_info REACHED 예상 → **확인됨**(alias focus 보존, el/texts 신규 수집). wellbeing FOCUS_MISMATCH 유지 → **coverage-gap 유지**. **예상 밖**: privacy REACHED→FOCUS_MISMATCH.
- **privacy anomaly (진단 `OBSERVED`, 미확정)**: observed_focus 가 privacy 가 아닌 device_info(`MyDeviceInfoActivity`)로 잡힘. launched_cmd 정상 + privacy 는 action 기반(`$` fix 무관). 의심 = 직전 run(085840Z subset)이 띄운 device_info 잔류 window / settle race(focus read 시점 미정착). **1회 관측 → 실 regression 미확정**. → 결정성 재확인(재run) 필요. coverage-gap 아님.
- **notes**: build/locale/seed/viewport == 074020Z → google/device_info 전환은 driver `$` fix(ee59ac7) 귀인. privacy 이상은 `$` fix 무관·별도 settle/잔류상태 의심. tool_commit=HEAD(3a84b41)이나 explorer behavior == ee59ac7.

---

## Append 절차 (다음 run)
1. explorer run → `catalog/`(full) 또는 서브디렉토리(subset/verify)에 JSON/MD + `raw/` 생성.
2. 본 파일에: (a) Ledger 표 1행 추가, (b) `## Run <run_id>` 상세 블록 추가 (위 필드 세트 + per-screen Δ + hypothesis/result).
3. `base/diff_against` 명시. full↔full 만 total 비교, subset 은 per-screen.
4. `tool_commit` / `tool_code_state` 기록. raw = local carry, digest+대장만 commit.
5. commit = batch, push = batch push audit 후.

## 다음 권장 run (승인 대기)
- **privacy 결정성 재확인** (우선): `settings_d1_privacy` REACHED→FOCUS_MISMATCH (run 102316Z, observed_focus=`Settings$MyDeviceInfoActivity`)가 residual-window/settle race 인지 실 regression 인지 — full(또는 privacy 단독) 재run 으로 결정성 확인. 의심 검증: 직전 device_info 잔류 여부 → run 시작 전 home 정착/대기 영향. tool_commit=HEAD, **단말 호출 별도 승인 필요**.
- (완료) full 17-screen rerun = run `20260604T102316Z` — google/device_info REACHED 확인, wellbeing coverage-gap 유지, privacy OBSERVED 이상 1건.
