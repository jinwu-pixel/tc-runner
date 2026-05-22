# Gallery ODIN2 TC 프로젝트 재개 가이드

**마지막 업데이트**: 2026-04-22
**대상 앱**: `com.example.mygalleryapp` v1.0.26042114
**대상 단말**: ODIN2 (AT-M150) 720x1560 @ 320dpi, ADB serial `c4324122`
**프로젝트 폴더**: `C:\Users\momen\Projects\tc-runner\ODIN2 - My gallary\`
  (2026-04-21 이관: 이전 `exported_tc1/gallery_odin2/` 에서 단말×앱 루트 폴더 구조로 변경)
**신규 단말×앱 작업 규칙**: 각 조합마다 루트에 `"<단말명> - <앱명>"` 형식 폴더 생성

---

## 빠른 상태 확인 (먼저 실행)

```bash
# 1. 디바이스 연결 확인
adb devices          # c4324122 device 가 있어야 함

# 2. 다중 디바이스 주의 — 모든 adb 호출에 -s c4324122 prefix 필수
#    (Thor2 B06201249E00030C 가 함께 연결되는 경우 있음)

# 3. preset 무결성 체크
adb -s c4324122 shell "ls /sdcard/DCIM/MyGallery_TC/ | wc -l"
#    기대: 27 (사진 25 + 영상 2)

# 4. 앱 상태 확인
adb -s c4324122 shell "dumpsys package com.example.mygalleryapp | grep versionName"
#    기대: versionName=1.0.26042114
```

## preset 복구 (문제 있을 때)

```bash
# 사진 재생성
venv/Scripts/python.exe scripts/gen_gallery_photos.py

# 단말 push (기존 지우고 새로)
venv/Scripts/python.exe scripts/reset_gallery_media.py
venv/Scripts/python.exe scripts/setup_gallery_media.py

# 회전 세로 고정
adb -s c4324122 shell "settings put system accelerometer_rotation 0"
adb -s c4324122 shell "settings put system user_rotation 0"
```

---

## 완료한 TC (23개, 모두 validate PASS)

```
"ODIN2 - My gallary"/functional/
├── photo/    (13) FUNC_01~13 — browse/detail/multi_select/share/delete
│                                 /info/gps/model_gap/edit_rotate/crop/filter
│                                 /save_copy/wallpaper_cancel
├── album/    (3)  FUNC_17 browse, FUNC_18 sort_5종, FUNC_19 inside
├── video/    (3)  FUNC_14 play_pause, FUNC_15 seek, FUNC_16 orientation
├── trash/    (1)  FUNC_20 empty_state
└── nav/      (3)  FUNC_00 first_launch_permission, FUNC_21 tab_roundtrip,
                   FUNC_22 portrait_lock_enforcement
```

스모크: `"ODIN2 - My gallary"/GAL_SMOKE_ODIN2.yaml`

검증:
```bash
for d in photo album nav trash video; do
  PYTHONIOENCODING=utf-8 venv/Scripts/python.exe \
    validate_tc.py --dir "ODIN2 - My gallary/functional/$d"
done
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe \
  validate_tc.py "ODIN2 - My gallary/GAL_SMOKE_ODIN2.yaml"
```

## 다음 확인 항목

- [ ] 개별 선택 복원 가능 여부 (GAL-BUG-004)
- [ ] 동영상 상세의 '배경화면으로 설정'이 스펙인지 미지원인지 (GAL-BUG-007)

2026-04-22 세션 결과는 `BUG_LOG.md` 하단 `세션 결과` 참조.

---

## 주요 좌표/ID 캐시 (빠른 재진입용)

### 사진 탭 (preset 기본 상태)
```
하단 네비  사진(120,1408)  앨범(360,1408)  휴지통(600,1408)
4/21 섹션 셀 (세 번째 열부터, 위에서 2행)
  cell(0,0)=VID_3min     center (120, 418)
  cell(0,1)=VID_20s      center (360, 418)
  cell(0,2)=IMG 24       center (600, 418)
  cell(1,0)=IMG 23       center (120, 662)
  cell(1,1)=IMG 22       center (360, 662)  ← GPS 있음
  cell(1,2)=IMG 21       center (600, 662)
  cell(2,0)=IMG 20       center (120, 906)
```

### 사진 상세 상단바
```
btnBack(72,128)  btnShare(360,128)  btnEdit(456,128)
btnFavorite(552,128)  btnMore(648,128)
```

### 사진 상세 ⋮ 메뉴
```
상세 정보(524,241)   삭제(524,337)   배경화면으로 설정(524,433)
```

### 다중 선택 하단 플로팅바
```
전체 선택(172,1245)   공유(359,1245)   삭제(547,1245)
```

### 편집 화면
```
btnBack(72,144)        btnSave(624,144)
btnRotate(188,1148)    btnCrop(532,1148)
필터 스트립 y=1312 (원본 112, 흑백 272, 세피아 432, 자동보정 592
               → 스와이프 → 빈티지 447, 폴라로이드 607)
```

### 편집 자르기 서브스크린
```
비율 스트립 y=1256 (1:1 71, 3:4 215, 원본 360, 3:2 504, 16:9 647)
상태 탭 y=1392 (aspect_ratio 120, rotate 360, scale 600)
```

### 앨범 탭
```
정렬 라벨(614,220) → 드롭다운 5개 y=313/409/505/601/697 (x=524)
  최신순 / 이름순 ㄱ-ㅎ / 이름순 ㅎ-ㄱ / 수정 날짜순 / 크기순
MyGallery_TC 앨범(180,408)   Screenshots(540,408)   Movies(180,775)
```

---

## 자동화 함정 (기록해둔 것)

1. **멀티 디바이스** — `adb -s c4324122` 프리픽스 필수
2. **`screencap -p //sdcard/foo.png`** — 저장 후 반드시 `rm` + scan 갱신, 안 그러면 앨범에 오염됨
3. **uiautomator dump "could not get idle"** — 비디오 플레이어는 Compose/custom → `screencap` + manual 검증
4. **validate_tc.py placeholder 파서** — `{}` 를 미해결 변수로 오인 → `find -exec ... {}` 금지, `sh -c 'for f in ...; do ... ; done'` 사용
5. **BACK 키 편집 폐기** — 편집 중 BACK 은 확인 다이얼로그 없이 즉시 취소 (GAL-BUG-005)
6. **편집 저장 경로** — `/sdcard/Pictures/MyGallery/EDIT_COPY_{ts}.jpg`, 원본 덮어쓰기 안됨 (GAL-BUG-006)
7. **.trashed 파일 복구** — `sh -c 'for f in /sdcard/DCIM/MyGallery_TC/.trashed-*NAME*; do mv "$f" /sdcard/DCIM/MyGallery_TC/NAME.jpg; done'` + MEDIA_SCANNER 브로드캐스트

---

## 다음 세션 시작 시 첫 동작

1. 이 파일 다 읽기 + `BUG_LOG.md` + `MENU_TREE.md`
2. 위 '빠른 상태 확인' 실행
3. preset 깨졌으면 복구 명령 실행
4. `GAL_SMOKE_ODIN2.yaml` 실행으로 핵심 플로우 회귀 (10분 내 완료)
5. 이후 다음 확인 항목 중 하나 선택하여 진행
