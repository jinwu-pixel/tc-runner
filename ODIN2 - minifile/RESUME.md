# MiniFile ODIN2 TC 프로젝트 재개 가이드

**마지막 업데이트**: 2026-04-24 (FAIL 9건 중 7건 수리 → 누적 **26/28 PASS**, 잔여 2건은 TC_30/31 viewer intent — 개발팀 확인 대기)
**대상 앱**: `com.example.mnnr_files` v1.0.26042210 (2026-04-22 배포)
**대상 단말**: ODIN2 (AT-M150) 720x1560 @ 320dpi, ADB serial `c4324122`
**프로젝트 폴더**: `C:\Users\momen\Projects\tc-runner\ODIN2 - minifile\`
**스펙**: `doc/minifile.pdf` (서정우 2026-04-21 메일, 6p)

## 역할 분리

- **계획/스켈레톤 (Opus)**: 본 문서, MENU_TREE, BUG_LOG, SMOKE yaml, preset 스크립트
- **실행 (Sonnet)**: Phase 0~2 수행, TC 본문 작성, 좌표 채우기, 리포트

---

## 진행 순서 (고정)

```
Phase 0 → Phase 1A → gate → Phase 1B → gate → Phase 2
```

### Phase 0. 환경 정리 + preset 주입 (Sonnet 최초 1회)

```bash
# 단말 연결 확인
adb devices   # c4324122 present 확인

# preset 적용 (멱등)
venv/Scripts/python.exe scripts/setup_preset.py --app minifile
```

스크립트가 수행하는 것:
1. /sdcard 루트 Gallery 잔존 XML 정리 (`ui_*.xml`, `dlg.xml`, `trash_sel*.xml`, `ui.xml`)
2. `output/minifile_preset/` 에 최소 preset 생성 (WAV×2, TXT×2, PDF×1, ZIP×1)
3. `/sdcard/Music`, `/sdcard/Documents`, `/sdcard/Download` 에 push + MediaScanner
4. 권한/파일 개수 스냅샷 출력

**Phase 0 완료 조건**:
- `Music/minifile_*` = 2
- `Documents/minifile_*` = 2
- `Download/minifile_*` = 2
- `DCIM/MyGallery_TC` = 27 (Gallery preset 재사용)
- `Movies` >= 3
- /sdcard 루트에 `ui_*.xml`/`dlg.xml` 없음

### 오디오 포맷 판정 규칙

스펙은 "오디오 파일 재생"만 명시, 포맷 미지정. Preset 은 WAV 로 나간다.

오디오 카테고리에 WAV 가 **미노출되어도** 즉시 앱 SPEC_GAP 으로 판정하지 말 것. 아래 3단계를 순서대로 수행:

1. **MIME filter 로그 확인** — `adb logcat | grep -iE 'audio|mime'` 로 카테고리 스캔 쿼리의 MIME 필터 관찰
2. **`audio/mpeg` 한정이면 MP3 push 후 재확인** — preset 포맷 영향 배제 절차. 별도 MP3 1개를 `/sdcard/Music/` 에 수동 push 하고 MediaScanner 재실행 후 카테고리 재확인
3. **재확인에도 미노출이면 SPEC_GAP 등록** — MNF-GAP 추가 + BUG_LOG 갱신

WAV 관찰 자체는 Phase 2 리포트에서 지우지 말 것 (MP3 재확인은 "preset 포맷 영향 배제 절차" 로 기록).

### Phase 1A. First-launch smoke

`SMOKE_MNNR.yaml` 내 `===== 1A =====` 블록.

목적:
- 앱 론칭 가능 확인
- `MANAGE_EXTERNAL_STORAGE` 권한 진입/복귀 플로우 관찰
- 이후 단계 위한 권한 부여

Gate: Sonnet 이 1A PASS 보고한 후 1B 진행.

### Phase 1B. Granted-state smoke

`SMOKE_MNNR.yaml` 내 `===== 1B =====` 블록.

경로:
1. 홈 구성 확인 (검색바 / 저장공간 카드 / 카테고리 / 휴지통 / 최근)
2. 폴더 진입 (`DCIM/MyGallery_TC`)
3. 파일 1개 외부 앱 열기 (FileProvider)
4. 파일 1개 선택 모드 → 삭제 (휴지통 이동)
5. 휴지통 진입 → 복원
6. 검색 1회

Gate: Sonnet 이 1B PASS 보고 + 홈/선택모드/휴지통 화면의 좌표·ID 를 수집해 본 파일 하단 "좌표 캐시" 섹션에 추가한 후 Phase 2 진행.

### Phase 2. 기능 전수

`functional/<bucket>/` 에 TC 작성·실행. Bucket 별 charter 는 아래 "TC Bucket Charter" 참조.

---

## TC Bucket Charter (Opus 확정, 세부 TC 는 Sonnet 이 작성)

| Bucket | 목표 | 예상 TC 수 | 근거 스펙 |
|---|---|---|---|
| `nav/` | 최초 launch, 권한 플로우, 뒤로가기, 회전 | 3~4 | page 5 §1~§2 |
| `dashboard/` | 검색바, 저장공간 카드, 카테고리 그리드, 휴지통 진입점, 최근 항목 애니메이션 | 4~5 | page 5 §1 |
| `browse/` | 폴더 진입 리스트/페이징/잔상 제거/FileProvider 외부앱 | 3~4 | page 5 §2 |
| `selection/` | long-press/더보기 진입, 카운트, 공유/삭제/X, 전체선택, 단일전용(이름/정보) | 5~6 | page 5 §3 |
| `ops/` | 이동, 복사, 이름변경, 정보, 휴지통이동, 복원, 완전삭제, 붙여넣기 다이얼로그 | 6~8 | page 5 §3~§5 |
| `search/` | 검색바 → SearchActivity 진입/쿼리 | 2 | page 5 §1 |
| `categories/` | 이미지/동영상/오디오/문서/다운로드/설치된 앱 (6종) | 6 | page 5 §1 |
| `storage_analysis/` | 분석 버튼 → StorageAnalysisActivity | 2 | page 5 §1 |
| `trash/` | 진입, 복원, 완전삭제 경고, 빈 상태 | 3~4 | page 5 §5 |
| `viewer/` | 이미지 열기, **동영상 컨트롤러 (신규)**, **오디오 재생 (신규)** | 3 | page 1 배포 노트 |
| `spec_gap/` | 보안폴더 진입점 부재, 생체권한 미사용 확인 | 2 | page 1 "보안폴더 삭제" |

합계 추정: **37~44개** + SMOKE 1건.

**작성 원칙** (CLAUDE.md + 본 플랜):
- metadata 에 `execution_type`/`manual_detail` 필수 (STAGE2_COMPILE.md Step 4 규칙 준수)
- 중복 TC 는 합치고 차이 명확한 것만 분리
- `spec_gap/` 은 smoke blocker 아님 — 별도 bucket 유지, BUG_LOG 등록 후보
- viewer bucket 은 Phase 2 후순위 (smoke 통과 후)

### Phase 2 재조정 확인 대상 (기존 bucket 귀속)

초기 charter 에 명시 누락됐지만 Phase 2 작성 시 아래 기존 bucket 안에서 확인할 것. 독립 bucket 신설 금지.

| 영역 | 귀속 bucket | 확인 지점 |
|---|---|---|
| 백그라운드 복귀 | `nav/` | HOME 키로 백그라운드 → 재진입 시 이전 경로/선택모드/검색쿼리 보존 여부 |
| 정렬·필터 | `browse/` | 폴더 리스트에 정렬/필터 UI 존재 여부 (스펙 silent — Phase 1B 에서 UI 확인 후 TC 범위 확정) |
| 공유 intent 외부 대상 | `ops/` | 공유 버튼 탭 → chooser 노출 → 외부 앱 전달 결과 (selection 은 진입까지만, 전달 완료는 op 귀속) |

Phase 1B PASS 후 본 매핑 재검토. UI 실존 여부에 따라 TC 수량 조정.

---

## 검증 명령

```bash
# 디렉터리 단위 validate
for d in nav dashboard browse selection ops search categories storage_analysis trash viewer spec_gap; do
  PYTHONIOENCODING=utf-8 venv/Scripts/python.exe \
    validate_tc.py --dir "ODIN2 - minifile/functional/$d"
done

# SMOKE
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe \
  validate_tc.py "ODIN2 - minifile/SMOKE_MNNR.yaml"

# 리포트 (검증 전원 PASS 후)
venv/Scripts/python.exe gen_excel.py
```

---

## 좌표 캐시 (Phase 1B 실기 확인 완료 2026-04-22)

### 홈 (Dashboard) — portrait 720x1560
```
앱 타이틀 "미니파일": [32,112][688,179]
검색 바 (search_bar_container): [32,211][688,323]  center=(360,267)
저장공간 카드 (card_storage): [32,371][688,604]  center=(360,488)
  저장공간 분석 버튼 (btn_analyze_storage, scrolled): [468,1122][648,1218]  center=(558,1170)
최근 항목 RecyclerView: y=727~1067
카테고리 그리드 (1st viewport):
  이미지 (cat_images): [32,1202][234,1444]   center=(133,1323)
  동영상 (cat_videos): [258,1202][461,1444]  center=(360,1323)
  오디오 (cat_audio):  [485,1202][688,1444]  center=(587,1323)
카테고리 그리드 2행 (scrolled ~600px):
  문서 (cat_docs):      [32,780][234,1022]   center=(133,901)
  다운로드 (cat_downloads): [258,780][461,1022] center=(360,901)
  앱 (cat_apps):        [485,780][688,1022]  center=(587,901)
  ※ 카테고리 라벨 실제: "앱" (스펙의 "설치된 앱" 아님)
저장공간 상세 카드 (scrolled): [32,1082][688,1394]
휴지통 카드 (layout_trash_row, scrolled ~600px): [32,1426][688,1538]  center=(360,1482)
  스크롤 후 위치 다름: [32,1128][688,1240]  center=(360,1184)
```

### File Browser (루트 / 일반 폴더 공통)
```
타이틀 (tv_app_title): [32,112][592,179]  (동적 — 폴더명 반영)
뷰 토글 버튼 (btn_view_toggle): [592,97][688,193]
저장소 제목 (tv_storage_title): [40,355][203,406]
파일 리스트 (rv_files): y=430~ (루트 기준)
  행 높이: 144px
  Row 0: y=430~574  center y=502
  Row 1: y=574~718  center y=646
  Row 2: y=718~862  center y=790
  Row 3: y=862~1006 center y=934
  Row 4: y=1006~1150 center y=1078
  Row 5: y=1150~1294 center y=1222
  Row 6: y=1294~1438 center y=1366
  Row 7: y=1438~1560 center y=1494
항목 더보기 버튼 (btn_more): x=[560,656] 각 행 수직 중앙  content-desc="More options"
```

### Selection Mode Toolbar (파일 브라우저 선택 모드)
```
toolbar_selection: [0,80][720,208]
  취소 (btn_selection_close): [16,96][112,192]   center=(64,144)
  선택 카운트 (tv_selection_count): [136,116][416,171]
  공유 (btn_selection_share): [416,96][512,192]  center=(464,144)
  삭제 (btn_selection_delete): [512,96][608,192] center=(560,144)
  정보 (btn_selection_more): [608,96][704,192]   center=(656,144)
  ※ "더보기 오버플로우" 없음 — 정보 단일 버튼
파일 리스트 (선택 모드): y=208~ 부터 시작 (toolbar 축소로 y offset 변경)
  Row 0: y=283~427  center y=355
  행 높이: 144px (동일)
  체크박스 (checkbox): x=[64,160] 각 행 수직 중앙
  파일 아이콘 (iv_icon): x=[176,256]
  이름/상세 영역: x=[288,560]
  더보기 (btn_more): x=[560,656]
삭제 확인 다이얼로그:
  "~을(를) 정말로 삭제하시겠습니까?" title
  삭제 (android:id/button1): [518,825][646,921]  center=(582,873)
  취소 (android:id/button2): 좌측 예상 (실기 미측정)
```

### Trash (휴지통)
```
타이틀: "휴지통"
파일 리스트: y=430~ (일반 파일브라우저와 동일)
항목 btn_more → 팝업: 복원 y=438~482 center=(524,460), 완전삭제 y=534~578 center=(524,556)
  ※ 선택 toolbar 에 복원 버튼 없음 — btn_more 팝업 전용
```

### SearchActivity
```
진입: 홈 search_bar_container (360,267) 탭
검색 입력창 (et_search_input): [112,80][608,208]  center=(360,144)
필터 칩 행: y=222~318
  전체 (chip_all): [24,222][169,318]
  이미지 (chip_images): [185,222][307,318]
  동영상 (chip_videos): [323,222][445,318]
  오디오 (chip_audio): [461,222][583,318]
  문서 (chip_docs): [599,222][696,318]
결과 리스트 (rv_search_results): y=330~1464
```

### StorageAnalysisActivity
```
진입: 홈 scrolled → btn_analyze_storage (558,1170) 탭
세부 UI: Phase 2 storage_analysis/ 에서 실기 확인
```

---

## 단말 세션 함정 (Gallery 에서 이관, 중요)

1. **멀티 디바이스** — `adb -s c4324122` 프리픽스 필수 (Thor2 `B06201249E00030C` 동시 연결)
2. **`screencap -p //sdcard/foo.png`** — 저장 후 반드시 `rm` + MediaScanner 갱신, 안 그러면 이미지 카테고리 오염
3. **uiautomator dump "could not get idle"** — 애니메이션 중 발생. 다이얼로그/플로팅은 wait 1.5s 후 dump
4. **validate_tc.py placeholder 파서** — `{}` 리터럴은 미해결 변수로 오인. `find -exec ... {}` 대신 `sh -c 'for f in ...; do ... ; done'`
5. **회전 세로 고정** — 매 세션 시작 시:
   ```
   adb -s c4324122 shell settings put system accelerometer_rotation 0
   adb -s c4324122 shell settings put system user_rotation 0
   ```

---

## TC 작성 함정 (2026-04-23 실기 실행 회고)

Phase 2 TC 28건 FAIL 의 근본 원인 3개 — 앱 버그 아님, TC 작성 측 오류. 향후 동일 패턴 재발 방지용.

### 1. NAV_PATH (21건) — cat_images 가 폴더 브라우저가 아님

- **오가정**: 홈 "이미지" 카테고리 (`cat_images`, 133,1323) 탭 → "내부 저장소" 루트 폴더 브라우저 진입
- **실제**: MediaStore 평면 이미지 리스트 (타이틀 "이미지") 진입
- **올바른 루트 브라우저 경로**: 홈 2회 스크롤 다운 → `layout_internal_storage` (360,~1000) → DCIM (360,914) → MyGallery_TC (360,626)
- **영향 TC**: MNF_FUNC_02, 03, 07~16, 19~23, 29~34
- **원칙**: 카테고리 그리드는 MediaStore 뷰로, 폴더 브라우저는 `layout_internal_storage` 경로로 — 두 경로를 절대 혼동 말 것

### 2. COORD_DRIFT (3건) — 좌표 캐시 재측정 필요

- `btn_analyze_storage`: 캐시 y=1170 → 실제 y≈1061 (TC_05, 25, 26)
- 휴지통 진입: 스크롤 1회로는 카드 미노출, 2회 필요 (TC_27, 28)

### 3. ASSERT_PRECISION (5건) — 타이틀·카운트 실측 불일치

- 카테고리 진입 타이틀은 폴더명이 아닌 카테고리명 그대로 — "이미지/동영상/오디오/문서/다운로드" (TC_19~23)
- `USE_BIOMETRIC` grep count = **2** (expected 1) — Manifest 선언 + feature 태그 중복 카운트 (TC_32)

---

## 다음 세션 시작 시 첫 동작 (Sonnet 인계 문구 최종본)

1. 본 파일 + `MENU_TREE.md` + `BUG_LOG.md` 정독
2. `adb devices` 로 c4324122 연결 확인 (멀티 디바이스 시 Thor2 `B06201249E00030C` 무시)
3. Phase 0 실행 (멱등 — 재실행 안전):
   ```
   venv/Scripts/python.exe scripts/setup_preset.py --app minifile
   ```
4. `SMOKE_MNNR.yaml` Phase 1A 블록 실행 → PASS 보고 후 Phase 1B 블록 실행 → PASS 보고
   - 1A: first-launch, `MANAGE_EXTERNAL_STORAGE` 진입 관찰
   - 1B: granted-state, 홈 구성 7건 verify + spec_gap 앵커(보안 문자열 ABSENT)
   - 1B 의 manual_pause 3건(폴더진입/삭제-복원/검색)을 실기 좌표로 교체하면 SMOKE 메타데이터를 `FULL_AUTO / AUTO / NONE` 로 승격
5. 좌표 캐시 섹션 채우고 Phase 2 진입
   - **재조정 확인 대상 3건** (백그라운드 복귀 / 정렬·필터 / 공유 intent 외부 대상) 반영
   - 오디오 카테고리 미노출 시 위 **오디오 포맷 판정 규칙 3단계** 를 따를 것
