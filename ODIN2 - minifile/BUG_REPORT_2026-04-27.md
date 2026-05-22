# MiniFile 버그 리포트 (2026-04-27 갱신본)

**대상 앱**: `com.example.mnnr_files` v1.0.26042210 (2026-04-22 배포 `minifiles_1.0.26042210.apk`)
**검증 단말**: ODIN2 (AT-M150) Android 14, 720x1560 @ 320dpi, ADB serial `c4324122`
**리포터**: jinwu@altech.kr
**수신**: 서정우 수석 (jungwoo@altech.kr)
**근거 테스트**: Phase 2 전수 TC 34건 (2026-04-23) + 4건 실기 재검증 (2026-04-24/27)
**전 버전**: `BUG_REPORT_2026-04-23.md` (재검증으로 일부 항목 갱신 — 본 문서 하단 "정정 이력" 참조)

---

## 요약

| ID | 심각도 | 영역 | 상태 | 요약 |
|---|---|---|---|---|
| MNF-GAP-01 | **높음** | 권한·런치 | CONFIRMED | 권한 미부여 상태에서 앱 실행 시 권한 요청 다이얼로그 미표시, MainActivity 직행 |
| MNF-GAP-03 | 중간 | 권한·Manifest | SPEC_GAP | USE_BIOMETRIC / USE_FINGERPRINT 권한 Manifest 잔존, 호출 경로 0건 (불필요 권한) |
| MNF-GAP-04 | 중간 | 선택 모드 | SPEC_GAP | 선택 모드 toolbar/팝업 어디에도 "전체 선택" 항목 없음 (스펙 page5 §3 명시) |
| MNF-NOTE-03 | 낮음~중간 | 파일 뷰어 | NOTE | 같은 MIME 파일이 출처별로 라우팅 다름 (인앱/chooser/launcher3 혼재) + 오디오 ViewerActivity 빈 화면 |

---

## MNF-GAP-01 · 권한 미부여 시 권한 요청 다이얼로그 미표시 (심각도: 높음)

- **기능 영역**: 권한 / 앱 런치
- **상태**: CONFIRMED
- **요약**: `READ_MEDIA_*` 권한 revoke 상태에서 앱 실행 시 PermissionController 다이얼로그가 표시되지 않고 MainActivity 로 직행함. 권한 없이 정상 UI 진입.
- **기대 결과**: 권한 미허용 시 앱이 권한 요청 다이얼로그 표시 또는 기능 제한 화면 노출
- **실제 결과**: `dumpsys window | grep mCurrentFocus` = `MainActivity`, `permissioncontroller` 표시 0건
- **재현 절차**:
  ```
  # READ_MEDIA_* revoke 만으로 재현됨 (MANAGE_EXTERNAL_STORAGE appops 조작은 필수 아님)
  adb -s c4324122 shell pm revoke com.example.mnnr_files android.permission.READ_MEDIA_IMAGES
  adb -s c4324122 shell pm revoke com.example.mnnr_files android.permission.READ_MEDIA_VIDEO
  adb -s c4324122 shell pm revoke com.example.mnnr_files android.permission.READ_MEDIA_AUDIO
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # → 앱이 권한 요청 없이 MainActivity 표시
  ```
- **증거**: `evidence/SMOKE_1B_home.png`
- **권고**: `MainActivity.onCreate()` 에서 필수 권한 체크 후 부족 시 `ActivityCompat.requestPermissions()` 호출 또는 permission rationale 화면으로 분기

---

## MNF-GAP-03 · 불필요 생체 권한 Manifest 잔존 (심각도: 중간)

- **기능 영역**: 권한 / Manifest
- **상태**: SPEC_GAP
- **요약**: `android.permission.USE_BIOMETRIC` / `android.permission.USE_FINGERPRINT` 가 AndroidManifest.xml 에 선언되어 있으나, 앱 사용 중 `BiometricPrompt.authenticate` 또는 `FingerprintManager` 호출이 로그에 나타나지 않음. 보안폴더 기능 삭제 후속 정리 미완료 추정.
- **기대 결과**: 사용하지 않는 권한은 Manifest 에서 제거 (Play Store 정책 및 최소 권한 원칙)
- **실제 결과**:
  - `dumpsys package com.example.mnnr_files | grep -c BIOMETRIC` → **2** (Manifest 선언 + permission grant)
  - 폴더 진입 / 파일 정보 / 이름 변경 / 선택 모드 / 공유 / 삭제 / 검색 / 휴지통 / 카테고리 전 플로우 실행 후 `logcat -d | grep -iE 'BiometricPrompt|FingerprintManager|biometric|fingerprint|authenticate'` → **0건**
- **재현 절차**:
  ```
  adb -s c4324122 shell logcat -c
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # 홈 → 폴더 진입 → 파일 정보 → 이름 변경 → 선택 모드(공유/삭제) → 검색 → 휴지통 → 카테고리 진입 등 기본 플로우 실행
  adb -s c4324122 shell logcat -d | grep -iE "BiometricPrompt|FingerprintManager|biometric|fingerprint|authenticate"
  # → 0건
  adb -s c4324122 shell dumpsys package com.example.mnnr_files | grep -c BIOMETRIC
  # → 2
  ```
- **증거**: `evidence/gap03_review_logcat.log` (10,757 라인, 앱 활동 134건 라인 중 biometric 키워드 0건)
- **권고**: AndroidManifest.xml 에서 `USE_BIOMETRIC` / `USE_FINGERPRINT` 선언 제거 (보안폴더 기능 부재 전제)

---

## MNF-GAP-04 · 선택 모드 "전체 선택" 기능 부재 (심각도: 중간)

- **기능 영역**: 파일 선택 모드
- **상태**: SPEC_GAP
- **요약**: 스펙 page5 §3 "파일 선택 및 조작" 에 "전체선택/해제" 기능 기재되어 있으나 실제 앱 선택 모드에는 해당 항목 없음. 선택 모드 toolbar 와 row btn_more 팝업 어디에도 "전체 선택" 노출 없음.
- **기대 결과**: 선택 모드 진입 후 toolbar 또는 btn_more 메뉴에 "전체 선택 / 전체 해제" 항목 존재
- **실제 결과**:
  - **선택 모드 toolbar (5개 요소)**: btn_selection_close (X) / tv_selection_count / btn_selection_share / btn_selection_delete / btn_selection_more (정보 단일 버튼) — 오버플로우 메뉴 없음
  - **row btn_more 팝업 · 단일 선택 (6개)**: 다음으로 이동 / 다음으로 복사 / 이름 바꾸기 / 휴지통으로 이동 / 파일 정보 / 다른 앱에서 열기
  - **row btn_more 팝업 · 다중 선택 카운트 2 (4개)**: 다음으로 이동 / 다음으로 복사 / 휴지통으로 이동 / 다른 앱에서 열기 (단일 전용 항목 자연 숨김)
  - 위 3개 위치 모두에서 `전체 선택 / 전체선택 / select_all / SelectAll` 키워드 grep → **0건**
- **재현 절차**:
  ```
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # 홈 → 2회 스크롤 → 내부 저장소(360,1000) → DCIM(360,934) → MyGallery_TC(360,626) 진입
  # 첫 파일 long-press → 선택 모드 진입
  # toolbar 확인 (전체 선택 부재)
  # 다른 파일 추가 탭으로 카운트 2 → row btn_more (x≈608, y=355) 탭 → 팝업 4개 항목
  # 추가 파일 다시 탭으로 선택 해제 → 카운트 1 → row btn_more 다시 탭 → 팝업 6개 항목
  # → 어느 상태에도 "전체 선택" 없음
  ```
- **증거**: `evidence/gap04_review_sel_toolbar.xml`, `gap04_review_sel_more.xml` (다중), `gap04_review_sel_more_single.xml` (단일)
- **권고**: 선택 모드 toolbar 우측 또는 btn_more 팝업 첫 항목에 "전체 선택 / 전체 해제" 추가. 선택 상태에서 토글 형태로 노출 권장.

---

## MNF-NOTE-03 · 동영상·오디오 뷰어 라우팅 일관성 미흡 (심각도: 낮음~중간)

- **기능 영역**: 파일 뷰어 / Intent 라우팅
- **상태**: NOTE
- **요약**: 같은 MIME(`video/mp4`, `audio/x-wav`) 파일이라도 **파일 출처/이름에 따라 라우팅이 일관되지 않음**. 일부는 인앱 `ViewerActivity` 진입, 일부는 외부 `ChooserActivity` 또는 `launcher3` 로 포커스 이탈. 오디오는 `ViewerActivity` 진입 시에도 재생 컨트롤·파일명 표시 없는 **빈 화면** 으로 렌더되는 추가 이슈 존재.
- **기대 결과**: 파일 출처와 무관하게 같은 MIME 은 동일 라우팅. 오디오는 재생 컨트롤(재생/일시정지/시크바/파일명) 노출 또는 외부 chooser 분기로 silent failure 회피.
- **실제 결과** (`dumpsys window | grep mCurrentFocus` + UI dump 기준 라우팅 매트릭스):

  | 파일 | MIME | 결과 mCurrentFocus | UI 상태 |
  |---|---|---|---|
  | `DCIM/MyGallery_TC/IMG_*.jpg` | `image/jpeg` | `com.example.mnnr_files/.ViewerActivity` | 이미지 정상 표시 |
  | `DCIM/MyGallery_TC/VID_20s.mp4` | `video/mp4` | `com.example.mnnr_files/.ViewerActivity` | `id/videoView` 정상 재생 |
  | `Movies/screen-20260409-120516.mp4` | `video/mp4` | `com.android.intentresolver/.ChooserActivity` | **HTML 뷰어/Chrome 제안** (MIME 불일치 추정) |
  | `Music/minifile_tone_440.wav` | `audio/x-wav` | `com.example.mnnr_files/.ViewerActivity` | **빈 검은 화면** (재생 컨트롤·파일명 부재) |
  | `Music/minifile_silent.wav` | `audio/x-wav` | `com.hnlens.launcher3/.uioverrides.QuickstepLauncher` | **포커스 launcher3 로 이탈** |

  - DCIM 비디오 탭 시: ViewerActivity 진입 + UI dump 에 `id/videoView` 위젯 + toolbar 에 파일명 표시
  - Movies 스크린레코딩 탭 시: ChooserActivity 가 `Chrome / HTML 뷰어` 만 제안 (video 핸들러 미제안 — MediaStore MIME 은 `video/mp4` 정상이나 MiniFile 의 ACTION_VIEW intent 가 잘못된 MIME 사용 추정)
  - Music tone_440.wav 탭 시: ViewerActivity 진입은 OK 지만 UI dump ID 목록 = `action_bar_root / toolbar / view_pager` 만, 재생 위젯 부재 + toolbar 텍스트 = `미니파일` (앱명, 파일명 미표시)
  - Music silent.wav 탭 시: launcher3 로 포커스 이탈 (원본 리포트 증상 그대로 잔존)
- **재현 절차**:
  ```
  # 사례 1: DCIM 동영상 → 인앱 정상
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # DCIM/MyGallery_TC/VID_20s.mp4 탭 → ViewerActivity + videoView

  # 사례 2: Movies 스크린레코딩 → chooser
  # Movies/screen-*.mp4 탭 → ChooserActivity (HTML 뷰어 제안)

  # 사례 3: Music silent.wav → launcher3 이탈
  # Music/minifile_silent.wav 탭 → launcher3 포커스

  # 사례 4: Music tone_440.wav → 빈 ViewerActivity
  # Music/minifile_tone_440.wav 탭 → ViewerActivity (재생 컨트롤 없는 빈 화면)
  ```
- **증거**:
  - 인앱 정상 (DCIM 동영상): `evidence/note03_review_video_view.xml`, `note03_review_video_screen.png`
  - 빈 ViewerActivity (Music tone_440): `evidence/note03_review_audio_view.xml`, `note03_review_audio_screen.png`
  - chooser (Movies 스크린레코딩): `evidence/tc30_rerun_chooser.xml`
  - launcher3 이탈 (Music silent): TC_31 run3 + 2026-04-27 재실행 로그
- **권고**:
  1. ACTION_VIEW intent 생성 시 MediaStore MIME(`video/mp4`, `audio/x-wav`) 을 그대로 사용 — 현재 일부 파일에서 잘못된 MIME 사용으로 chooser 가 비관련 핸들러(HTML 뷰어) 제안
  2. 오디오 인앱 플레이어 구현 또는 ACTION_VIEW chooser 분기 — 현 빈 화면은 silent failure
  3. launcher3 포커스 이탈은 startActivity 후 결과 처리 누락 추정 — intent 핸들러 부재 시 fallback 로직 추가

---

## 정정 이력 (2026-04-23 → 2026-04-27)

2026-04-27 실기 재검증으로 일부 항목 갱신:

- **MNF-GAP-01** — repro steps 에서 `appops set ... MANAGE_EXTERNAL_STORAGE ignore` 라인 제거. `READ_MEDIA_*` revoke 만으로 재현 확인됨
- **MNF-GAP-04** — 원본 "선택 모드 btn_more 메뉴 6개 = 비선택 context menu 와 동일" 묘사를 "단일 선택 시 6개 / 다중 선택 시 4개 / toolbar 5개 — 어느 상태에도 '전체 선택' 부재" 로 정밀화. 다중 선택 시 단일 전용 항목(이름 바꾸기·파일 정보) 자연 숨김 동작은 정상 UX
- **MNF-NOTE-03** — 원본의 "타입별 라우팅 불일치 (이미지=ViewerActivity / 동영상=MainActivity / 오디오=launcher3)" 가 추가 검증 결과 **파일별 라우팅 불일치** 형태로 변형되어 잔존. DCIM 동영상은 인앱 ViewerActivity 정상 진입(개선)하지만 Movies 스크린레코딩은 ChooserActivity 가 비관련 HTML 뷰어를 제안하는 신규 증상 발견. 오디오는 같은 폴더 내에서도 파일별로 ViewerActivity(빈 화면) 또는 launcher3(원본 증상 잔존) 로 갈림. 5×라우팅 매트릭스로 본문 재서술

---

## 참고

- **내부 이슈 추적**: `BUG_LOG.md` (본 리포트 대상 4건 외에 TC 작성 측 이슈 MNF-OBS-01/02, 정보성 NOTE, 문서 정정 대상 MNF-GAP-02 포함)
- **실행 로그**: `evidence/run3_output.log` (run3 베이스라인 17/28 PASS), `evidence/run4_quickfix.log` + `evidence/run5_quickfix2.log` (TC 측 수정 검증)
- **재검증 증거** (2026-04-27):
  - GAP-03: `gap03_review_logcat.log`
  - GAP-04: `gap04_review_sel_toolbar.xml`, `gap04_review_sel_more.xml`, `gap04_review_sel_more_single.xml`
  - NOTE-03: `note03_review_video_view.xml`, `note03_review_video_screen.png`, `note03_review_audio_view.xml`, `note03_review_audio_screen.png`
- **UI 덤프**: `evidence/ui_*.xml` (btn_more 메뉴, 선택모드 메뉴, rename 다이얼로그, 홈 스크롤 후 레이아웃 등)
- **질문/재현 지원**: jinwu@altech.kr
