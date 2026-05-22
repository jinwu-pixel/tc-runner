# MiniFile 버그 리포트 (2026-04-23)

**대상 앱**: `com.example.mnnr_files` v1.0.26042210 (2026-04-22 배포 `minifiles_1.0.26042210.apk`)
**검증 단말**: ODIN2 (AT-M150) Android 14, 720x1560 @ 320dpi, ADB serial `c4324122`
**리포터**: jinwu@altech.kr
**수신**: 서정우 수석 (jungwoo@altech.kr)
**근거 테스트**: Phase 2 전수 TC 34건 실기 (run3 17/28 PASS + quick fix run4/5 → 19/28 PASS)
**본 리포트 범위**: 앱 수정을 요구하는 4건만. TC 작성 측 이슈 및 문서(스펙) 측 이슈는 내부 BUG_LOG 에서 별도 추적.

---

## 요약

| ID | 심각도 | 영역 | 상태 | 요약 |
|---|---|---|---|---|
| MNF-GAP-01 | **높음** | 권한·런치 | CONFIRMED | 권한 미부여 상태에서 앱 실행 시 권한 요청 다이얼로그 미표시, MainActivity 직행 |
| MNF-GAP-03 | 중간 | 권한·Manifest | SPEC_GAP | USE_BIOMETRIC / USE_FINGERPRINT 권한 Manifest 잔존 but 호출 경로 없음 (불필요 권한) |
| MNF-GAP-04 | 중간 | 선택 모드 | SPEC_GAP | 선택 모드에 "전체 선택" 기능 부재 (스펙 page5 §3 명시) |
| MNF-NOTE-03 | 낮음 | 파일 뷰어 | NOTE | 오디오 파일 탭 시 launcher3(QuickstepLauncher)로 포커스 이탈 |

---

## MNF-GAP-01 · 권한 미부여 시 권한 요청 다이얼로그 미표시 (심각도: 높음)

- **기능 영역**: 권한 / 앱 런치
- **상태**: CONFIRMED
- **요약**: `MANAGE_EXTERNAL_STORAGE` ignore + `READ_MEDIA_*` 전체 revoke 상태에서 앱 실행 시 PermissionController 다이얼로그가 표시되지 않고 MainActivity 로 직행함. 권한 없이 정상 UI 진입.
- **기대 결과**: 권한 미허용 시 앱이 권한 요청 다이얼로그 표시 또는 기능 제한 화면 노출
- **실제 결과**: `dumpsys window | grep mCurrentFocus` = `MainActivity`, `permissioncontroller` 표시 0건
- **재현 절차**:
  ```
  adb -s c4324122 shell appops set com.example.mnnr_files MANAGE_EXTERNAL_STORAGE ignore
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
- **요약**: `android.permission.USE_BIOMETRIC` / `android.permission.USE_FINGERPRINT` 가 AndroidManifest.xml 에 선언되어 있으나, 앱 사용 중 `BiometricPrompt.authenticate` 또는 `FingerprintManager` 호출이 로그에 나타나지 않음. 보안폴더 기능 삭제(MNF-GAP-02) 후속 정리 미완료 추정.
- **기대 결과**: 사용하지 않는 권한은 Manifest 에서 제거 (Play Store 정책 및 최소 권한 원칙)
- **실제 결과**:
  - `dumpsys package com.example.mnnr_files | grep BIOMETRIC` → `USE_BIOMETRIC` 선언 관찰 (count 2 — Manifest + feature 태그)
  - 앱 탐색 + 파일 조작 + 공유 + 이름 바꾸기 전 과정 실행 후 `logcat -d | grep -iE 'BiometricPrompt|FingerprintManager|authenticate|biometric'` → 0건
- **재현 절차**:
  ```
  adb -s c4324122 shell logcat -c
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # 홈 → 파일 브라우저 → 파일 열기 → 뒤로가기 등 기본 플로우 실행
  adb -s c4324122 shell logcat -d | grep -iE "BiometricPrompt|FingerprintManager|biometric"
  # → 0건
  adb -s c4324122 shell dumpsys package com.example.mnnr_files | grep -c BIOMETRIC
  # → 2
  ```
- **증거**: —
- **권고**: AndroidManifest.xml 에서 `USE_BIOMETRIC` / `USE_FINGERPRINT` 선언 제거 (보안폴더 기능 부재 전제)

---

## MNF-GAP-04 · 선택 모드 "전체 선택" 기능 부재 (심각도: 중간) · 신규

- **기능 영역**: 파일 선택 모드
- **상태**: SPEC_GAP
- **요약**: 스펙 page5 §3 "파일 선택 및 조작" 에 "전체선택/해제" 기능 기재되어 있으나 실제 앱 선택 모드에는 해당 항목 없음. 선택 모드 btn_more 팝업은 비선택 상태 context menu 와 동일한 6개 항목만 노출.
- **기대 결과**: 선택 모드 진입 후 toolbar 또는 btn_more 메뉴에 "전체 선택 / 전체 해제" 항목 존재
- **실제 결과**: 선택 모드 btn_more 메뉴 6개 항목 = `다음으로 이동 / 다음으로 복사 / 이름 바꾸기 / 휴지통으로 이동 / 파일 정보 / 다른 앱에서 열기` (비선택 context menu 와 동일)
- **재현 절차**:
  ```
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # 홈 → 2회 스크롤 → 내부 저장소(360,1000) → DCIM(360,934) → MyGallery_TC(360,626) 진입
  # 첫 파일 long-press → 선택 모드 진입 확인
  # 파일 행 btn_more (x≈608, y=499) 탭 → 팝업 메뉴 확인
  # → "전체 선택" 항목 없음
  ```
- **증거**: `evidence/ui_sel_more.xml` (uiautomator dump)
- **권고**: 선택 모드 toolbar 우측 또는 btn_more 팝업 첫 항목에 "전체 선택 / 전체 해제" 추가. 선택 상태에서 토글 형태로 노출 권장.

---

## MNF-NOTE-03 · 오디오 파일 탭 시 launcher3 포커스 이탈 (심각도: 낮음) · 신규

- **기능 영역**: 파일 뷰어 / Intent 라우팅
- **상태**: NOTE
- **요약**: 파일 브라우저에서 **이미지** 파일 탭 → 앱 내장 `ViewerActivity` 진입 (정상). 반면 **동영상** 파일 탭 → MainActivity 로 복귀, **오디오** 파일 탭 → 외부 런처(`com.hnlens.launcher3/.uioverrides.QuickstepLauncher`) 로 포커스 이탈. 파일 유형별로 뷰어 처리 경로 불일치.
- **기대 결과**: 모든 지원 파일 유형이 일관된 뷰어 경로 사용 — 인앱 `ViewerActivity` 또는 ACTION_VIEW chooser 중 택일
- **실제 결과** (`dumpsys window | grep mCurrentFocus` 기준):
  - 이미지(`IMG_20260419_000.jpg`) 탭 → `com.example.mnnr_files/.ViewerActivity`
  - 동영상(.mp4) 탭 → `com.example.mnnr_files/.MainActivity` (뷰어 미진입)
  - 오디오(.wav) 탭 → `com.hnlens.launcher3/.uioverrides.QuickstepLauncher` (런처 복귀)
- **재현 절차**:
  ```
  adb -s c4324122 shell am force-stop com.example.mnnr_files
  adb -s c4324122 shell monkey -p com.example.mnnr_files -c android.intent.category.LAUNCHER 1
  # 내부 저장소 → Movies/ 폴더 진입 → .mp4 파일 탭
  adb -s c4324122 shell dumpsys window | grep mCurrentFocus
  # → MainActivity (ViewerActivity 아님)
  # 뒤로가기 → Music/ 진입 → .wav 파일 탭
  adb -s c4324122 shell dumpsys window | grep mCurrentFocus
  # → com.hnlens.launcher3/...QuickstepLauncher
  ```
- **증거**: `evidence/run3_output.log` (MNF_FUNC_30, MNF_FUNC_31 단계별 결과)
- **권고**: 의도된 동작(이미지만 인앱 뷰어)인지 확인 필요. 의도된 경우 오디오 탭 시 외부 chooser(ACTION_VIEW) 노출로 변경 권장 — 현재 런처 복귀는 사용자가 작업 실패로 오인 가능. 의도되지 않았다면 동영상/오디오 인앱 뷰어 구현 필요.

---

## 참고

- **내부 이슈 추적**: `BUG_LOG.md` (본 리포트 대상 4건 외에 TC 작성 측 이슈 MNF-OBS-01/02, 정보성 NOTE, 문서 정정 대상 MNF-GAP-02 포함)
- **실행 로그**: `evidence/run3_output.log` (run3 베이스라인 17/28 PASS), `evidence/run4_quickfix.log` + `evidence/run5_quickfix2.log` (TC 측 수정 검증)
- **UI 덤프**: `evidence/ui_*.xml` (btn_more 메뉴, 선택모드 메뉴, rename 다이얼로그, 홈 스크롤 후 레이아웃 등)
- **질문/재현 지원**: jinwu@altech.kr
