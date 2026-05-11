# ODIN2 - Music · RESUME

## 단말 / 앱
- 단말: ODIN2 (AT-M150) · serial `c4324122` · 720x1560 @ 320dpi · ko_KR portrait
- 대상 앱: `com.mive.music` v`1.0.2604231952` (versionCode 26042319, minSdk 33, targetSdk 35)
- launcher activity: `com.mive.music/.presentation.main.MainActivity`

## Phase 0 진행 (2026-04-30) — 완료
- Step 1-2 device + package discovery
- Step 3 launcher activity 확정 (monkey + dumpsys window)
- Step 4 skeleton 4종 작성 (validate PASS, lint 0/0)
- Step 5 lockscreen/non-target preflight (`manual_music_lockscreen_seed`, WARN: activity_parse_failed — 정상)
- Step 6 target foreground preflight (`manual_music_home_seed`, OK, 12 visible texts)
- Step 7-8 catalog build x2 + show (target 1 / non-target 1)
- Step 9 catalog delta (verdict: known_screen)
- Step 10 9-section 보고 — manual evidence observed

## Phase 1A 진행 (2026-04-30)
- SMOKE_01 작성: `MUSIC_SMOKE_01_app_launch.yaml` — force-stop → monkey launch → wait → 6 anchor verify
- validate PASS, lint 1 WARN (`전체` length=2 WEAK_VERIFY_TEXT, sidecar 보존)
- preflight `manual_music_smoke01_seed` OK, coverage 1.0 (6/6 anchors)
- catalog delta verdict: **`changed_texts`** (jaccard 1.0, added/removed 모두 빈 set, screen_id 변동 — UI 구조 미세 변화)
- catalog 누적 후 total=3 (target 2 + non-target 1)
- lint 정리: step_index=5 verify_text "전체" 에 `lint_allow:[WEAK_VERIFY_TEXT]` step-level suppress 적용 → actionable warnings 0 (sidecar에 `suppressed:true`로 보존)
- **runtime PASS** (`cli run`): 10/10 steps PASS, exit 0, 18.5s, HTML report `reports/20260430_114641_report.html`

## Phase 1B 진행 (2026-04-30) — runtime gate 대기
- 4 탭 manual probe (`manual_music_smoke02_probe_{all,recent,favorite,playlist}`) 완료. 결과 요약 → MENU_TREE.md HOME 4 탭 화면 섹션 참조
  - 4 탭 모두 `selected="true"` 미노출, resource-id / content-desc 빈 값, leaf TextView clickable=false / parent View clickable=true
  - 전체/즐겨찾기/플레이리스트는 unique anchor 확보 (`곡, 아티스트 검색…` / `즐겨찾기한 곡이 없습니다` / `플레이리스트가 없습니다`)
  - 최근 재생은 positive anchor 부재 → absence-only (`verify_gone "곡, 아티스트 검색…"`)
- SMOKE_02 작성: `MUSIC_SMOKE_02_navigate_home_tabs.yaml` — 24 step (3 SETUP + 5 baseline + 4 cycles × 4 step). 좌표 tap 0
- validate PASS, lint actionable 0 (`전체` length=2 step-level suppress, sidecar `reports/lint/20260430T052512Z.json`)
- preflight `manual_music_smoke02_seed` WARN `expected_texts_missing` (coverage 0.75, 6/8). 누락 2건은 post-tap empty-state anchors — probe 실측 확인. xml_sha256=`33b419fc…` (HOME baseline 일치)
- catalog: build 1 updated (read-only invariant 유지, 신규 screen 0). delta verdict=`known_screen`, baseline_screen_id=`16925695fea9…`, jaccard=null, interpretation_flags=[`preset_unknown`]
- **runtime PASS** (`cli run`): 24/24 steps PASS, exit 0, 50.6s, HTML report `reports/20260430_181555_report.html`
- 핵심 검증: tap_text가 leaf TextView clickable=false → parent View clickable=true 로 정상 ancestor bubbling (4 탭 tap 모두 PASS). wait 1000ms 안정성 확인. verify_gone "곡, 아티스트 검색…" 최근 재생 화면에서 PASS

## Phase 1A/1B Commit (2026-04-30) — closed
- HEAD `cd879cb` (origin/master `ahead 1`, push 보류)
- commit 메시지: `testdata(music): add ODIN2 Music smoke seeds and tab navigation TCs`
- 포함 6개: `RESUME.md`, `MENU_TREE.md`, `BUG_LOG.md`, `MUSIC_SEED_HOME.yaml`, `MUSIC_SMOKE_01_app_launch.yaml`, `MUSIC_SMOKE_02_navigate_home_tabs.yaml`
- 제외: `catalog/`, `probe_dump_*.xml`, `reports/`, `src/*`, schema 파일 — generated/probe-only는 untracked 유지

## Phase 1C 진행 (2026-04-30 작성, 2026-05-11 runtime PASS)
- 사전 probe (`probe_dump_smoke03_home.xml` / `probe_dump_smoke03_post.xml`, untracked): 첫 곡 row container clickable=true, leaf TextView clickable=false, 우측 NAF Button (더보기) 회피 가능. tap (360,500) 으로 player surface 진입 확인. `1.0x` 텍스트가 player-unique anchor (HOME 부재 ↔ player 등장)
- BT 오디오 disconnect 환경에서 `media_session state=ERROR(7)` 관찰 (NOTE only, 본 TC scope 밖). cleanup `am force-stop` 1회로 회수 충분
- 사용자 결정 옵션 1 채택: preset baseline 고정 (`전체 첫 곡 = After The Hurricane / Jazmine Sullivan / 3:58`)
- SMOKE_03 작성: `MUSIC_SMOKE_03_open_first_track_player.yaml` — 12 step (3 SETUP + 4 baseline + 1 ACTION + 1 wait + 2 player ASSERT + 1 cleanup). 좌표 tap 0
- validate PASS, lint actionable 0 (`reports/lint/20260430T095936Z.json`, "1.0x" length=3 lint 통과, suppress 불필요)
- preflight `manual_music_smoke03_seed`: WARN `expected_texts_missing` coverage 0.75 (3/4). 누락 1건은 `1.0x` post-tap player anchor — 정상 범위. xml_sha256=`33b419fc…` HOME baseline 일치
- catalog: build 1 updated (read-only invariant 유지, 신규 screen 0). delta verdict=`known_screen`, baseline_screen_id=`16925695fea9…`, jaccard=null, interpretation_flags=[`preset_unknown`]
- **runtime PASS** (`cli run`, 2026-05-11): 12/12 steps PASS, exit 0, 22.5s, HTML report `reports/20260511_122359_report.html`
- 검증 결과 요약: preset baseline (After The Hurricane / Jazmine Sullivan / 3:58) 실측 일치. tap_text 첫 곡 row → player surface 진입 → `1.0x` anchor verify PASS. mutation 0, capability gap 0, TEARDOWN `am force-stop` 1회로 cleanup 완료

## Schema gate 결정 (2026-04-30)
- B 채택: schema-compliant placeholder
  - `tc_class: AMBIGUOUS_NL` (SEED placeholder)
  - `manual_detail: "NONE"` (AUTO 강제)
  - SEED 의도는 description / metadata.source 에 자유 문자열로 보존
- A(우회) 기각, C(schema-only mini-PR) → PR 5 prebook
- `validate_tc.py` 우회 금지

## Phase 0 boundary
- SMOKE 5건 작성 금지 / playback 자동화 금지 / audio focus·background 검증 금지
- src/* 코드 수정 금지
- generated 산출물(`reports/preflight/manual_music_*`, `reports/catalog_delta/*`, `ODIN2 - Music/catalog/*`) commit 금지
- skeleton MD/YAML 도 안정화 시점까지 untracked 유지

## Deferred (Phase 0 종료 후 재선택)
- Phase 1 — Music SMOKE 5건 / playback automation
- PR 5 — batch delta + path normalization (PR 4 회수) + tc_step_schema SEED 확장
