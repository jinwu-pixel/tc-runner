# ODIN2 - Music · MENU_TREE (draft)

> Phase 0 단계: 메뉴 트리는 catalog ingestion 결과로 후속 보강.
> 본 문서는 Step 10 Phase 0 Result 보고에서 actual screen evidence 기반으로 1차 갱신한다.

## 알려진 사실 (2026-04-30 Phase 0 preflight 결과)
- launcher activity: `com.mive.music/.presentation.main.MainActivity`
- monkey 1회로 launch 성공 (keyguard 해제 상태)
- 진입 직후 노출되는 화면 = **Music HOME** (별도 onboarding 다이얼로그 미관찰)

### Music HOME 변형 — 두 screen_id 관찰됨 (text 동일, XML 구조 미세 차이)
- `4d9cbbcad953…` (manual_music_home_seed, 02:26:23Z)
- `16925695fea9…` (manual_music_smoke01_seed, 02:38:13Z) — SMOKE_01 cold-launch 직후
- 두 변형 모두 visible_texts set 100% 동일 (jaccard=1.0)

### Music HOME 화면 (`screen_id: 4d9cbbcad953…`, `manual_music_home_seed`)
- 앱 헤더: `Mive Music`
- 탭/네비게이션: `전체` · `최근 재생` · `즐겨찾기` · `플레이리스트`
- 검색 hint: `곡, 아티스트 검색…`
- 첫 화면 곡 항목 형태 (행 = 곡명 / 아티스트 / duration):
  - `After The Hurricane` · `Jazmine Sullivan` · `3:58`
  - `너 말이야` · `5dolls` · `3:37`

### Lockscreen / non-target baseline (`screen_id: 4d6ac23e2757…`, `manual_music_lockscreen_seed`)
- 노출 텍스트: `11:20` · `4월 30일 (목)` · `충전됨`
- current_activity: 파싱 실패 (lockscreen 상태 — preflight WARN 정상)

### HOME 4 탭 화면 (Phase 1B SMOKE_02 probe, 2026-04-30)
- 단일 Activity (`…/MainActivity`) 내부에서 fragment 전환. `current_activity` 변동 없음.
- 4 탭 라벨은 모든 탭 화면에서 항상 노출 (전환 anchor 부적합).
- selected="true" 속성 미노출 — 활성 indicator는 그래픽만, XML 미반영.
- 탭 leaf TextView clickable=false, 그 한 단계 위 parent View clickable=true. resource-id / content-desc 모두 빈 값.

| tab | xml_sha256 | visible_texts_count | unique anchor |
| --- | --- | --- | --- |
| 전체 (default) | `33b419fc…` | 12 | `곡, 아티스트 검색…` (preset-stable) |
| 최근 재생 | `8c30eef1…` | 8 | 없음 (positive anchor 부재) |
| 즐겨찾기 | `2e17446e…` | 6 | `즐겨찾기한 곡이 없습니다` (preset-dependent empty) |
| 플레이리스트 | `093d87fd…` | 6 | `플레이리스트가 없습니다` (preset-dependent empty) |

탭 parent bounds:
- 전체/최근 재생 화면: `[24,208][204,304] / [204,208][384,304] / [384,208][564,304] / [564,208][720,304]`
- 즐겨찾기/플레이리스트 화면 (컨텐츠 reflow): `[0,208][149,304] / [149,208][329,304] / [329,208][509,304] / [509,208][696,304]`

## 미확인 (Phase 1 SMOKE 작성 시 보강)
- 곡 탭 시 진입하는 player 화면 구성 (재생/일시정지/스크럽바 좌표)
- 탭 내부 정렬·필터 옵션 (탭 헤더 외 영역)
- 곡 항목 long-press / 메뉴 진입 시 컨텍스트 액션
- 권한 요청 다이얼로그 유무 (지금까지 미관찰)
- 화면 회전 / 백그라운드·foreground 복귀 시 상태
- 즐겨찾기 0건 → 1건 전이 시 즐겨찾기 탭 화면
- 플레이리스트 0건 → 1건 전이 시 플레이리스트 탭 화면
