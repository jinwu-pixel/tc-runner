# MiniFile 45건 BUG 전수 검증 (2026-04-27)

**대상**: com.example.mnnr_files v1.0.26042210
**단말**: ODIN2 (AT-M150) 720x1560, ADB serial <device_serial>
**검증 방식**: 실기 ADB + uiautomator dump + logcat + screencap

---

## 결과 요약

| 분류 | 건수 | ID |
|---|---|---|
| **CONFIRMED** (재현됨) | 27 | #1, #4, #5, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20, #21, #22, #25, #26, #27, #28, #29, #30, #32, #35, #38, #40, #41, #44, #45 |
| **NOT_REPRO** (재현 안 됨, 동작 정상) | 4 | #9, #36, #39 |
| **N/T** (환경 의존, 미검증) | 13 | #2, #3, #6, #7, #8, #23, #24, #31, #33, #34, #37, #42, #43 |

---

## CONFIRMED (재현 완료)

### #1 미디어뷰어 - 상태바 미노출
- **재현**: 동영상/오디오 ViewerActivity 진입 시 시스템 상태바 hidden, toolbar 만 노출
- **증거**: `evidence/bug1_25_26_32_video_viewer.png`, `bug21_audio_viewer.png`

### #4 설치된 앱 - 앱 제거 안됨
- **근본 원인**: `REQUEST_DELETE_PACKAGES` / `DELETE_PACKAGES` 권한 미선언
- **logcat**: `E UninstallerActivity: Uid 10266 does not have android.permission.REQUEST_DELETE_PACKAGES or android.permission.DELETE_PACKAGES`
- **체감**: 제거 메뉴 탭 → 무반응 (UninstallerActivity 즉시 종료)
- **증거**: `evidence/bug04_app_remove.png`

### #5 파일 검색 바 - 휴지통 검색 시 커서 미노출 (한번 더 눌러야)
- **재현**: 휴지통 → 검색바 첫 탭 → 검색 화면 전환되나 EditText `focused=false`, 커서/키보드 미노출. 두 번째 탭 (input 영역) 후 `focused=true`, 키보드 노출
- **증거**: `evidence/bug05_trash_search_first_tap.png`, `bug05_search_after_2nd_tap.png`

### #10 설치된 앱 - 저장용량 크기 시스템과 다름
- **재현**: MiniFile 앱 카테고리 표시 **7.68MB** vs 시스템 설정 표시 **7.01MB** (차이 0.67MB)
- **증거**: `evidence/bug04_apps_list.png`

### #11 더보기 아이콘 - 선택모드 진입용 더보기 없음
- **재현**: 폴더 view toolbar 우측에 `btn_view_toggle` (그리드/리스트) 만 존재, `btn_more` 없음. 선택모드 진입은 long-press only.
- **증거**: `evidence/bug11_folder_toolbar.png`, `bug11_after_longpress.png`

### #12 휴지통 - 폴더 휴지통 이동 시 토스트는 노출 but 삭제 안됨
- **재현**: test_folder 더보기 → 휴지통으로 이동 → "휴지통으로 이동되었습니다" 토스트 노출, 폴더는 그대로 잔존 (디스크 + UI)
- **증거**: `evidence/bug12_folder_trash_after.png`

### #13 메인화면에서 "여기에" 탭 시 이동 완료 (잘못된 동작)
- **재현**: Download 의 long_filename.txt 다음으로 이동 → 홈 (미니파일 메인) 으로 이동 → paste FAB 그대로 노출 → 탭 → "작업이 완료되었습니다" 토스트, 파일이 `/sdcard/` 루트로 이동됨
- **증거**: `evidence/bug13_home_paste_fab.png`, `bug13_after_paste_on_home.png`

### #14 "여기에 붙여 넣기" 텍스트 짤림
- **재현**: long_filename.txt 이동/복사 시 paste FAB 텍스트가 `this_is_a_very_long_filename_for_testi` 까지만 표시, "여기에 붙여넣기" 접미사 잘림 (ellipsis 없음)
- **증거**: `evidence/bug14_paste_ui_long.png`

### #15 동일 경로 이동/복사 - 충돌 다이얼로그 미노출
- **재현**: conflict_test.txt 다음으로 복사 → 같은 Download 폴더에서 paste → "작업이 완료되었습니다" 토스트, 충돌 다이얼로그 (덮어쓰기/이름변경/취소) 미노출, 파일 변화 없음
- **증거**: `evidence/bug15_same_path_paste.png`

### #16 이름변경 - 파일명 부분 하이라이트 안됨
- **재현**: 이름 바꾸기 다이얼로그 진입 시 EditText `focused=false`, 텍스트 전체/부분 선택 없음, 커서 미노출. (확장자만 분리해 base 부분 highlight 가 정상)
- **증거**: `evidence/bug16_rename_dialog.png`

### #17 이름변경 - 빈 문자열 입력 시
- **재현**: EditText 비운 채 "바꾸기" 탭 → 버튼은 enabled, 에러 미노출, 파일명 변경 없이 다이얼로그 종료, 기존 이름 유지
- **증거**: `evidence/bug17_empty_rename_result.png`

### #18 이름변경 - 'test/file' 입력 시
- **재현**: slash 포함 입력 → 에러 미노출, 다이얼로그 종료, 기존 이름 유지 (slash 무시)
- **증거**: `evidence/bug18_slash_rename.png`

### #19 이름변경 - 동일 파일명 입력 시 (※ 보고된 것보다 더 심각)
- **재현**: conflict_test.txt → minifile_readme.txt 로 변경 (동일 폴더 내 기존 파일과 충돌)
- **결과**: 충돌 다이얼로그 미노출 + **기존 minifile_readme.txt (43B) 가 conflict_test.txt 내용 (8B) 으로 silent 덮어쓰기 됨**
- **데이터 손실**: 보고서 claim 은 "덮어쓰기 발생안됨" 인데, 실제로는 **덮어쓰기 발생** (사용자 모르게 데이터 손실)

### #20 폴더 삭제 안됨
- **재현**: test_folder long-press → 선택모드 → 삭제 → 삭제 확인 다이얼로그 → "삭제" 탭 → 폴더 그대로 (UI + 디스크)
- **증거**: `evidence/bug20_folder_delete_dialog.png`, `bug20_after_delete.png`

### #21 오디오 재생 - 다음/이전 파일 재생 버튼 없음
- **재현**: ViewerActivity 오디오 view 에 `btn_audio_play_pause` + `seekbar_audio` 만 존재. 다음/이전 (skip) 버튼 부재.
- **증거**: `evidence/bug21_audio_viewer.png`

### #22 오디오 재생 - 백그라운드 재생 불가
- **재현**: 15초 wav 재생 시작 → HOME 키 → 10초 후 복귀 → 위치 0:01 정지 (계속 재생됐다면 0:11 근처). `dumpsys audio` 에서 MediaPlayer state=`paused` 확인.

### #25 동영상 컨트롤러 - 전체화면 버튼 없음
- **재현**: 동영상 viewer toolbar 에 전체화면 toggle 부재
- **증거**: `evidence/bug25_26_32_video_controller.png`

### #26 동영상 컨트롤러 - 상단 메뉴바 미숨김
- **재현**: 동영상 재생 화면에서 toolbar (파일명 + 뒤로가기) persistent 노출. 하단 컨트롤러는 아예 부재.
- **증거**: `evidence/bug25_26_32_video_controller.png`

### #27 파일 검색 - 동일 파일명 재검색 시 미노출
- **재현**: "IMG" 입력 → 5건 노출 → 클리어 → "IMG" 재입력 → 0건 (캐시/재쿼리 실패)
- **증거**: `evidence/bug27_retype_search.png`

### #28 파일 검색 - 폴더도 노출
- **재현**: "Music" 검색 → Music 폴더 (yellow folder icon, "3개 항목") 결과로 노출. 검색은 파일만 대상이어야 하나 폴더 포함됨.
- **증거**: `evidence/bug28_search_folder.png`

### #29 파일 검색 - 이미지 칩 단독 선택 시 결과 0건
- **재현**: 이미지 chip 선택 + 검색어 비움 → 디스크에 다수 jpg 존재하나 결과 0건 (chip 가 단독 filter 로 동작 안 함)
- **증거**: `evidence/bug29_image_empty_search.png`

### #30 파일 검색 - 전체 chip + empty: 이미지만 노출
- **재현**: "전체" chip + 검색어 비움 → 결과는 .jpg 만 노출, 다른 타입 (mp4/wav/zip/apk/pdf/txt) 미포함
- **증거**: `evidence/bug30_all_chip_empty.png`, `bug30_all_chip_bottom.png`

### #32 동영상 컨트롤러 - 음소거 버튼 없음
- **재현**: 동영상 viewer 에 mute/unmute toggle 부재
- **증거**: `evidence/bug25_26_32_video_controller.png`

### #35 오디오 - 좌우 스와이프 후 복귀 시 재생 안됨
- **재현**: long_audio_15s.wav 재생 (0:01) → 좌 스와이프 (silent.wav) → 우 스와이프 (long_audio 복귀) → 위치 0:00 리셋, 3초 후에도 0:00 (재생 안 됨)

### #38 파일 용량 표시 - 파일 정보 다이얼로그가 raw bytes
- **재현**: 999999 bytes 파일 (~1MB) 의 파일 정보 다이얼로그 → "크기: 999999 bytes" raw 표시 (KB/MB 단위 변환 없음)
- **증거**: `evidence/bug38_file_info.png`. GB 급 파일이면 "1234567890 bytes" 식 짤림 위험.

### #40 카테고리 다운로드 - 내부저장소 잠시 노출 후 다운로드 노출
- **재현**: 다운로드 카테고리 탭 → 첫 300ms frame 에 "내부 저장소" 헤더 + 루트 폴더 (Alarms/Android/Audiobooks) 노출 → 600ms 후 Download 폴더 내용으로 전환
- **증거**: `evidence/bug40_t1_300ms.png` (300ms), `bug40_t2_600ms.png` (600ms), `bug40_t3_settled.png`

### #41 휴지통 - 휴지통에 있는 파일 재생 안됨
- **재현**: 휴지통 내 파일 (zip) 탭 → MiniFile in-app viewer 가 아닌 **외부 Google Files (com.google.android.apps.nbu.files) TosActivity** 로 라우팅됨
- **체감**: 자체 재생/뷰어 동작 0, 외부 앱 약관 수락 화면 노출

### #44 압축파일 - 압축풀기 안됨
- **재현**: zip 파일 탭 → MiniFile in-app 처리 없음 → 외부 Files by Google 으로 라우팅. 컨텍스트 메뉴 (다음으로 이동/복사/이름 바꾸기/휴지통/파일 정보/다른 앱에서 열기) 에 "압축풀기" 항목 부재.
- **증거**: `evidence/bug44_zip_tap.png`

### #45 (앞서 검증) APK 파일 설치 안됨
- **근본 원인**: `REQUEST_INSTALL_PACKAGES` 권한 미선언
- **logcat**: `E InstallStart: Requesting uid 10266 needs to declare permission android.permission.REQUEST_INSTALL_PACKAGES`
- 경로별 증상 차이: 최근항목 탭=완전 무반응, 카테고리 탭=Chooser→InstallStart→권한 거부→복귀
- **증거**: `evidence/bug45_apk_install_logcat.txt`, `bug45_apk_install_permissions.txt`

---

## NOT_REPRO (보고된 증상 재현되지 않음)

### #9 PDF 파일 공유 - "Files by Google, Drive 만 노출"
- **실측**: PDF share chooser 에 Quick Share / 메시지 / Files by Google / 블루투스 / Drive 등 5+ 옵션 노출. 보고된 "2개만 노출" 증상 미재현.
- **증거**: `evidence/bug09_pdf_share_chooser.png`

### #36 파일 제목 - 실제 파일명과 다름
- **실측**: 이미지 카테고리에서 IMG_*_855.jpg, IMG_*_004.jpg 두 파일 탭 → 둘 다 viewer 상단 title 과 실제 파일 콘텐츠 일치. 미스매치 미발견.
- **증거**: `evidence/bug36_viewer_after_tap.png` (855.jpg), `bug36_viewer_004.png` (004.jpg)
- 추가 검증 필요 가능성: scrolling 깊이 / sort 순서 / 동영상 카테고리 등 다른 조합

### #39 메인 홈 - "No files found" 영문 문구
- **실측**: 빈 폴더 (Alarms 0개 항목) 진입 → "내부 저장소" 헤더만 노출, 중앙에 영문/한글 placeholder 텍스트 일절 없음 (완전 빈 화면). 휴지통도 동일.
- **증거**: `evidence/bug39_empty_folder.png`, `bug_trash_state.png`
- 보고된 영문 문구 미발견. 다른 트리거 조건 (예: 카테고리 grid view, 빈 검색결과) 추가 검증 필요 가능성.

---

## N/T (Not Tested — 환경/장비 의존, 추가 셋업 필요)

| ID | 항목 | N/T 사유 |
|---|---|---|
| #2 | 동영상 avi 재생 | 진짜 AVI 코덱 파일 필요 (mp4 확장자만 변경한 파일은 정상 재생되어 비결정적) |
| #3 | 최근 항목 가로 스크롤 원근감 애니메이션 | 시각적 애니메이션 판단 (TC 없음 명시) |
| #6 | 폴더 500개 이상 시 버벅임 | 500개 폴더 환경 준비 부담, 성능 측정 필요 |
| #7 | SD 카드 저장공간 내부저장소 할당 | SD 카드 미장착 |
| #8 | SD 카드 Progress 바 미반영 | SD 카드 미장착 |
| #23 | 오디오 재생 중 통화 수신 일시정지 | 통화 환경 (수신 발신 페어링) 필요 |
| #24 | 통화 종료 후 오디오 자동 재생 | 통화 환경 필요 |
| #31 | 동영상 재생 중 통화 수신 일시정지 | 통화 환경 필요 |
| #33 | 동영상 회전 시 처음부터 재생 | 회전 트리거 + 재생 위치 비교 필요 (시간 단축 위해 보류) |
| #34 | 1시간 이상 오디오 MM:SS 표기 | 1시간짜리 파일 준비 필요 |
| #37 | 최근 항목 비디오 썸네일 화질 | 시각적 화질 판단 (TC 없음 명시) |
| #42 | 가로모드 인디케이터 UI 위치 | 가로모드 회전 + 시각 검증 필요 (TC X 명시) |
| #43 | 가로모드 네비3버튼 화면 짤림 | 가로모드 + 3버튼 네비 모드 + 시각 검증 (TC X 명시) |

---

## 횡단 패턴 (재발 메커니즘)

### A. 시스템 권한 미선언 → 침묵 실패
- `REQUEST_INSTALL_PACKAGES` 미선언 → APK 설치 무반응 (#45)
- `REQUEST_DELETE_PACKAGES`/`DELETE_PACKAGES` 미선언 → 앱 제거 무반응 (#4)
- 둘 다 시스템 packageinstaller 가 즉시 거부 후 silent 종료. 사용자 토스트/에러 0건.
- **현재 매니페스트 declared permissions** (10건): MANAGE_EXTERNAL_STORAGE, READ_MEDIA_*, USE_BIOMETRIC, USE_FINGERPRINT, PACKAGE_USAGE_STATS, QUERY_ALL_PACKAGES, READ_MEDIA_VISUAL_USER_SELECTED, DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION

### B. 자체 처리 부재 → 외부 Google Files 로 라우팅
- 휴지통 내 파일 탭 (#41), zip 파일 탭 (#44), Movies 의 일부 mp4 (BUG_REPORT NOTE-03) → ChooserActivity 또는 직접 Files by Google 호출
- 자체 압축풀기 / 휴지통 내 미리보기 / 일부 미디어 라우팅 부재

### C. 입력 검증 부재 → 데이터 손실 위험
- 빈 문자열 / slash / 동일 파일명 입력 모두 에러 미노출 (#17, #18, #19)
- #19 는 보고된 것보다 심각: 동일 이름 입력 시 기존 파일을 silent 덮어쓰기 (데이터 손실)

### D. UI 상태 sync 결함
- 검색 결과 캐시/재쿼리 실패 (#27)
- 좌우 스와이프 후 재진입 시 재생 위치 리셋 (#35)
- 다운로드 카테고리 tap 시 일시적 wrong content 노출 (#40)

### E. 컨트롤러/UX 부재 (대량)
- 동영상 viewer: 전체화면/음소거/하단 컨트롤러/seek bar 부재 (#1, #25, #26, #32)
- 오디오 viewer: 다음/이전 / 백그라운드 재생 / 스와이프 복귀 모두 미작동 (#21, #22, #35)
- toolbar 더보기 / 전체선택 부재 (#11, MNF-GAP-04 기존)
- 폴더 삭제 / 휴지통 이동 미작동 (#12, #20)
