# Device-sourced Menu Tree Baseline (v1) — Design

- 날짜: 2026-06-02
- 상태: design approved (spec review 대기)
- repo: tc-runner (학습 루프·탐색 영역 §2.5)
- 타깃 단말: THOR2_K — AT-M140 `B06201249E0002B8`, Android 14, build `RY07260302M`, locale `persist.sys.locale=ko-KR` (`ro.product.locale=en-US`), SIM SKT, viewport 480×800 @ 220dpi
- 대상 앱: `com.android.settings`

## 1. Goal (v1)

실기 자동 탐색으로 **device-sourced ground-truth 메뉴트리 artifact**를 안전·재현 가능하게 생성한다.
이 artifact는 figma_pipeline처럼 **TC 합성·drift 분석의 입력 source**가 된다(합성 자체는 별도 stage).

- 탐색 방식 = **deep-link/intent enumeration**: 큐레이션 seed의 각 화면을 `am start`로 진입 → read-only dump + node inventory + scroll sweep.
- **DFS/tap 기반 child discovery 제외.** scroll·read-only dump·node inventory까지만.
- 산출물 schema는 thor2j figma `ExtractionRecord`와 **평행 구조**로 잡아 v1.1 drift를 저비용화한다.

## 2. Non-goals (v1.1+ 분리)

- pm 정적 auto-enumeration (coverage 확장) — Approach B
- tap 기반 DFS child discovery / hybrid(scroll+tap)
- ja-JP baseline + KR↔JP cross-locale 비교
- device↔figma **drift 리포트** (v1은 diff-ready 까지만)
- artifact 기반 **TC 합성** (thor2j-tc-appium 별 stage)
- 동적값(배터리%/시각) 정규화
- thor2j `references/MENU_TREE.snapshot.md` 재생성 브리지

## 3. Architecture & module layout

| 신규/변경 | 파일 | 역할 |
|---|---|---|
| 신규 | `THOR2_K - Settings/menu_tree_seed.yaml` | 큐레이션 seed (사람 편집, 재현성 핵심) |
| 신규 | `src/menu_tree.py` | canonical schema(dataclasses) + JSON/MD emitter. **device 무관 순수 모듈** |
| 신규 | `scripts/settings_tree_explorer.py` | thin 드라이버(orchestration) |
| 변경(소) | `scripts/menu_mapper.py` | 순수 파서 4종 + DENYLIST/ALLOWLIST를 module-level로 노출 |
| 변경(1줄) | `THOR2_K - Settings/catalog_schema.md` | Tier D 분류 추가 |

**레이어링 규칙 (불변)**:
- `src/menu_tree.py`는 `scripts/menu_mapper.py`를 **import하지 않는다** (src→scripts 의존 금지).
- 드라이버 `settings_tree_explorer.py`만 `src.menu_tree` + `scripts.menu_mapper` 양쪽을 import.

**menu_mapper refactor**: `extract_nodes` / `generate_fingerprint` / `is_node_safe` / `parse_bounds` + `DENYLIST` / `ALLOWLIST_PACKAGES`를 module-level 함수/상수로 추출.
기존 `MenuMapper` 메서드는 **module-level 함수로 위임하는 wrapper로 잔존** → 동작 변경 0 (회귀 테스트로 가드). DENYLIST 중복 제거 → §2.3 source-of-truth 정합.

**산출 경로**: `THOR2_K - Settings/catalog/menu_tree_baseline_<run_id>.json` + `.md` (run_id = `YYYYMMDDTHHMMSSZ` UTC, §5.6 포맷). raw dump는 **`catalog/raw/<run_id>/<screen_id>.xml`** 로 per-run namespacing 저장(append-only — 이전 run raw를 덮어쓰지 않음). 매 run = 새 run_id 번들(overwrite 없음).

## 4. Canonical schema (`src/menu_tree.py`)

JSON이 계약, MD는 렌더 뷰. `MenuScreen ≈ per-screen figma ExtractionRecord`.

```
MenuTreeBaseline
  schema_version: 1
  tool_version: "menu-tree-baseline-v1"
  generated_at_utc, run_id
  device: { serial, model, product, device, build_fingerprint, build_id,
            android, locale_persist, locale_product, viewport, dpi, sim }
  package: "com.android.settings"
  seed_ref: { source_menu_tree, seed_version, seed_path }
  target_mismatch_ack: false            # --allow-target-mismatch 시 true
  summary: { screen_count, reached, reached_external, unreachable,
             launch_failed, focus_mismatch, dump_rejected,
             denylist_recorded, observed_texts_total, scroll_passes_total }
             # reached_external = count(reach_kind == "external"), status와 무관
  screens: [ MenuScreen ]

MenuScreen
  screen_id                # seed 안정 id (예: settings_d1_privacy)
  label_ko, nav_path[]     # 예: ["설정","개인정보 보호"]
  entry: { method:"deeplink", action|null, component|null, launched_cmd }
  reach_status             # 6상태 (§6)
  reach_kind               # internal | external | null — 도달 종류 (DUMP_REJECTED여도 보존)
  observed_focus, expect_activity_regex, activity_match: bool
  fingerprint|null         # generate_fingerprint (focus+texts+rids md5[:8]); DUMP_REJECTED 시 null
  observed_texts: { ko:[], en:[], other:[] }   # arbitrary lang key 허용 (future ja)
  elements: [ MenuElement ]                    # DUMP_REJECTED 시 []
  scroll: { passes, swipes:[{dir,x1,y1,x2,y2}], new_texts_per_pass[],
            terminated:"no_new"|"max_passes" }
  dump_info: { dump_error|null, dump_size, raw_present }
  risk_flags[]             # 기록만 하고 진입 안 한 denylist 라벨
  raw_dump_ref|null        # catalog/raw/<run_id>/<screen_id>.xml; DUMP_REJECTED(raw 미저장) 시 null

MenuElement
  label, resource_id|null
  kind                     # title | menu_row | button | toggle | input | unknown
  source_class             # 원본 android class (보존)
  text_role_hint           # primary | summary | unknown (보존)
  clickable, focusable, checkable: bool
  risk                     # none | denylist | toggle | checkable  (record-not-enter)
  bounds|null              # evidence용 (탭 안 함)
```

**kind 파생**: checkable=true 또는 class∈{Switch,CheckBox,RadioButton}→`toggle`; EditText류→`input`; Button/clickable leaf→`button`; 상단 비클릭 헤더→`title`; summary 동반 clickable row→`menu_row`; 그 외 `unknown`. (figma `Title/Menu/Button`과 매핑)

**observed_texts 버킷**: Hangul→`ko`, Latin→`en`, 그외→`other`. schema는 임의 lang key 허용(KR baseline에서 `ja` 비어도 포맷상 추가 자연스럽게).

## 5. Seed (`menu_tree_seed.yaml`)

reuse-first 1회 수기 작성 — 기존 `THOR2_K - Settings/MENU_TREE.md`에서:
depth0 home + deep-link batch #2 (13) + depth1 (privacy/location/google/wellbeing/device_info/lensusb) ≈ **~20 screen**.

```yaml
seed_version: 1
locale: ko-KR
target_serial: "B06201249E0002B8"
target_serial_label: "THOR2_K (AT-M140)"
source_menu_tree: "THOR2_K - Settings/MENU_TREE.md"
package: com.android.settings
screens:
  - id: settings_d1_privacy
    label_ko: "개인 정보 보호"
    nav_path: ["설정", "개인 정보 보호"]
    entry: { action: "android.settings.PRIVACY_SETTINGS" }   # 또는 component
    expect_activity_regex: "PrivacyDashboardActivity"
  # ...
```

## 6. 드라이버 flow (`settings_tree_explorer.py`)

seed 순서 = 결정론 순서. 화면별 **독립 실행** — 한 화면 실패해도 status 기록 후 다음 진행(abort 안 함).

seed 1개당:
1. **preflight**: 연결 단말 serial == seed `target_serial` 확인. 불일치 → **hard-abort**. 예외는 `--allow-target-mismatch` 명시 시만(+ `target_mismatch_ack:true` 기록). `--serial`은 ADB 대상 선택(별개). device baseline 캡처(getprop).
2. **launch**: `entry.action`→`am start -a <action>` / `entry.component`→`am start -n <comp>`. `launched_cmd` 기록.
3. **self-verify** (settle 1.2s 후 `dumpsys window` mCurrentFocus):
   - settings + activity가 `expect_activity_regex` 매치 → `REACHED`
   - ALLOWLIST 외부 pkg(wellbeing/permissioncontroller) → `REACHED_EXTERNAL_PACKAGE`
   - ALLOWLIST 밖 pkg / activity 불일치 → `FOCUS_MISMATCH` (+복구 HOME-only)
   - launch 무반응/에러 → `LAUNCH_FAILED`
4. **dump** (read-only `uiautomator dump`): 실패/0·tiny XML → `DUMP_REJECTED` (`dump_info`로 `dump_error`/`dump_size`/`raw_present` 분리 기록).
5. **parse**: `extract_nodes`→`fingerprint`→elements(kind/risk/source_class/text_role_hint)→`observed_texts` 버킷. denylist 라벨은 `risk_flags`에 기록(탭 안 함).
6. **scroll sweep**: **1 pass = swipe 1회 후 dump** (재현성 우선 — double-swipe의 row 건너뜀 회피). 신규 텍스트 merge(라벨+rid dedup). `no_new` 또는 `max_passes=8` 종료. 각 swipe의 방향/좌표를 `scroll.swipes[]`에 명시.
7. **raw 저장**: `catalog/raw/<run_id>/<screen_id>.xml` → `raw_dump_ref` (per-run, append-only). dump 실패 시 미저장 → `raw_dump_ref=null`.
8. **복구**: 다음 screen 전 `KEYCODE_HOME` 후 다음 deep-link (back-stack 오염 방지). `am force-stop`은 기본 아님 — ANR/crash용 `--force-stop-on-stuck` 옵션으로만.
9. **emit**: `MenuTreeBaseline` → `menu_tree.py` emitter → JSON + MD.

**reach_status 정의·우선순위 (단일 enum, 모호성 제거)**:
- `UNREACHABLE_NO_ACTION` — seed에 `action`/resolvable `component` 둘 다 없어 **launch 시도 자체 안 함** (pre-launch).
- `LAUNCH_FAILED` — launch command는 냈으나 focus가 settings/외부 어디에도 도달 못 함.
- `FOCUS_MISMATCH` — ALLOWLIST 밖 pkg 또는 activity가 `expect_activity_regex` 불일치.
- `REACHED` / `REACHED_EXTERNAL_PACKAGE` — 도달 성공(내부 / 정상 외부 라우팅).
- `DUMP_REJECTED` — **도달은 성공(REACHED 계열)했으나 dump가 0/tiny/에러**. 이 경우 reach 성공보다 `DUMP_REJECTED`를 status로 표기하되, **도달 종류는 `reach_kind`(internal/external)에 보존** → summary `reached_external` 집계가 status와 무관하게 정확. `dump_info`가 세부(`dump_error`/`dump_size`/`raw_present`)를 분리 보존. (reach 자체 실패 시엔 dump를 시도하지 않으므로 DUMP_REJECTED와 LAUNCH_FAILED/FOCUS_MISMATCH는 상호배타.)

`--dry-run`: device 호출 없이 plan(seed 화면 + launch cmd) 출력.

## 7. 안전 · 재현성 invariants

**read-only command allowlist** (드라이버의 모든 adb 호출은 단일 게이트 메서드를 경유, allowlist 외 호출 시 raise):
- `am start -a|-n` (진입), `input swipe` (scroll), `input keyevent KEYCODE_HOME` (복구 — **HOME-only**), **`uiautomator dump /sdcard/<f>` + `cat /sdcard/<f>` + `rm -f /sdcard/<f>`** (dump 내부 3-step 전부 게이트 — `GuardedADB.dump()`가 `ADB.dump_ui()`에 위임하지 않고 직접 구현해 모든 adb 호출을 single gate 경유), `getprop`, `dumpsys window`, `wm size`/`wm density` (device baseline viewport/dpi)
- `am force-stop com.android.settings`는 generic allowlist에 **넣지 않음** — opt-in `force_stop_settings()`에서만 flag-gate(우회 방지). 기본 OFF.
- `KEYCODE_BACK`은 v1 기본 복구에서 **제외**(HOME으로 모든 복구 충분). 필요 시 v1.1에서 명시 stuck-recovery 용도로만 재도입.
- 옵션: `am force-stop com.android.settings` (`--force-stop-on-stuck` 시만)
- **금지**: `input tap` (의미적 탭) / `KEYCODE_POWER` / `KEYCODE_ENTER` / `KEYCODE_DPAD_CENTER` (thor2j Forbidden 정합)

**가드**: DENYLIST = record-not-enter(어차피 탭 안 함). ALLOWLIST_PACKAGES 밖 focus → `FOCUS_MISMATCH` + 복구(외부 walk 안 함).

**encoding**: adb 출력 bytes→`utf-8` replace(cp949 host 함정). `/sdcard` 경로는 `MSYS_NO_PATHCONV=1`.

**재현성**: 결정론 순서 + 고정 settle + 정렬된 text 버킷 + 안정 fingerprint. 동적값(배터리%/시각)은 v1에선 그대로 record + note(정규화는 v1.1).

## 8. catalog_schema.md Tier D 추가 (정확 문구)

> Tier A/B/C는 hand-written catalog 정본이다. Tier D는 device-sourced machine baseline으로, tool-generated append-only artifact이며 hand-written catalog와 구분한다. Tier D는 TC 합성·drift 분석의 입력 source로 사용할 수 있지만, 사람이 해석한 catalog 정본을 대체하지 않는다.

## 9. Testing (offline-first, 무단말)

강점: 기존 `THOR2_K - Settings/catalog/_raw_*.xml` **현재 39개+**를 golden fixture로 재사용 → 실제 device 데이터로 schema 검증.

- `tests/test_menu_tree.py` (`src/menu_tree.py`): fixture XML → `extract_nodes`/kind 분류/`ko·en·other` 버킷/fingerprint 안정/JSON round-trip/MD 스냅샷. **byte-identical JSON은 고정 clock/run_id 주입 단위테스트 한정** (동적 필드 `generated_at_utc`/`run_id`/raw path 때문).
- `tests/test_menu_mapper_refactor.py`: module-level 함수 == 기존 메서드 출력(wrapper 회귀 가드).
- `tests/test_settings_tree_explorer.py`: **stub ADB 주입** → reach_status 6분류 / scroll `no_new` 종료 / 복구 시퀀스 / summary 집계 / target-mismatch abort / `--dry-run` / **command allowlist 위반 0 단언**.

## 10. Acceptance criteria (v1 done)

1. pytest GREEN (menu_tree unit + driver stub + menu_mapper 회귀).
2. THOR2_K 실기 1 run → `catalog/menu_tree_baseline_<run_id>.json/.md`, **screen == seed count** (v1 seed-only — 중복/누락 record는 실패 신호), reach 집계. **read-only invariant: 허용 command allowlist 위반 0**(stub 단언 + 실기 run에서 schema/deterministic ordering 검증). 보고 = "device smoke: baseline bundle 생성, N/M REACHED".
3. `catalog_schema.md` Tier D 문구 추가.
4. §2.3 source-of-truth: schema/driver/seed/tests **같은 PR 정렬**.

## 11. Source-of-truth & policy 정합

- DENYLIST/ALLOWLIST 단일화(menu_mapper module-level) — 중복 drift 제거.
- Tier D = §2.3 정의→코드→테스트 같은 PR 정렬.
- commit/push는 글로벌 정책 — 명시 승인 전까지 working-tree 저장만.

## 12. Future (v1.1+)

§2 Non-goals 항목들. baseline artifact 포맷 안정 후 별 cycle로 진행: pm auto-enum(coverage) → hybrid(scroll+tap) → ja-JP/cross-locale → device↔figma drift → TC 합성 브리지.
