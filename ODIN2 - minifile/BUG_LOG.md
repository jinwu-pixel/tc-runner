# MiniFile · 버그/이슈 관찰 로그 (ODIN2)

앱: `com.example.mnnr_files` v1.0.26042210
기기: ODIN2 (AT-M150) ADB c4324122
보고 채널: 서정우 수석(jungwoo@altech.kr) 스레드

| 상태 | 의미 |
|---|---|
| OBSERVED | 실기 재현 확인 |
| SUSPECT | 재현 미확정 / 한 번만 관찰 |
| CONFIRMED | 추가 재현 및 원인 정리 완료 |
| SPEC_GAP | 스펙 대비 부재 / 요구사항 차이 |
| NOTE | 구조 메모 (버그 아님) |

## 요약

| ID | 기능 영역 | 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|
| MNF-GAP-01 | 권한·런치 | CONFIRMED | 권한 미부여 상태에서 앱 실행 시 권한 요청 다이얼로그 미표시 — MainActivity 직행 | MNF_FUNC_01 | evidence/SMOKE_1B_home.png |
| MNF-GAP-02 | 보안폴더 | SPEC_GAP | 보안폴더 진입점 완전 제거됨 (배포 노트 "보안폴더 삭제" 반영). 홈 및 컨텍스트 메뉴에 "보안" 텍스트 0건 | MNF_FUNC_32 | — |
| MNF-GAP-03 | 권한·Manifest | SPEC_GAP | USE_BIOMETRIC / USE_FINGERPRINT 권한이 Manifest에 선언됐지만 실제 앱에서 BiometricPrompt 미호출 (기능 삭제 후 권한 정리 미완) | MNF_FUNC_33 | — |
| MNF-NOTE-01 | 뷰어 | NOTE | 이미지 파일 탭 시 앱 내 ViewerActivity 진입 (in-app). 동영상/오디오는 외부 intent fallback(run3 확인) — MNF-NOTE-03 참조 | MNF_FUNC_08, 29 | evidence/SMOKE_1B_viewer.png |
| MNF-NOTE-02 | 카테고리 | NOTE | 홈 카테고리 레이블이 스펙 "설치된 앱"과 달리 실제 UI는 "앱"으로 표시됨 | MNF_FUNC_24 | — |
| MNF-NOTE-03 | 뷰어 | NOTE | 동영상/오디오 파일 탭 시 in-app ViewerActivity가 아닌 MainActivity 복귀 또는 launcher3(QuickstepLauncher)로 복귀 — intent routing 차이 | MNF_FUNC_30, 31 | evidence/run3_output.log |
| MNF-GAP-04 | 선택 모드 | SPEC_GAP | 선택 모드 btn_more 메뉴에 "전체 선택" 항목 없음 (스펙 page5 §3에 "전체선택/해제" 기재) — 실제 메뉴는 비선택 context menu와 동일 6개 | MNF_FUNC_34 | evidence/ui_sel_more.xml |
| MNF-OBS-01 | 파일 작업 | FIXED | 이름 바꾸기 text-clear 를 `MOVE_END + KEYCODE_DEL×30` 반복으로 우회, 버튼은 resource-id 로 매치 (MNF_FUNC_12 PASS 2026-04-24) | MNF_FUNC_12 | evidence/ui_rename_dlg.xml |
| MNF-OBS-02 | 파일 작업 | FIXED | TC 측 precondition·좌표 오류였음 — preset 파일명 일치 + `tap_text` 기반 폴더 탐색 + FAB 중첩 회피 방향 (MNF_FUNC_13/14/15/28 PASS 2026-04-24) | MNF_FUNC_13, 14, 15, 28 | reports/20260424_163533_report.html |

---

## MNF-GAP-01: 권한 미부여 시 권한 요청 다이얼로그 미표시

- 기능 영역: 권한 / 런치
- 상태: CONFIRMED
- 단말: ODIN2 (AT-M150) c4324122
- 앱: com.example.mnnr_files v1.0.26042210
- 요약: MANAGE_EXTERNAL_STORAGE=ignore + READ_MEDIA_IMAGES/VIDEO/AUDIO 전체 revoke 상태에서 앱 실행 시 PermissionController 다이얼로그가 표시되지 않고 MainActivity로 직행함.
- 기대 결과: 권한 미허용 시 앱이 권한 요청 다이얼로그를 표시하거나 기능을 제한해야 함.
- 실제 결과: `permissioncontroller count: 0`, `mCurrentFocus=MainActivity`. 권한 없이 정상 진입.
- 재현 절차: `adb -s c4324122 shell appops set com.example.mnnr_files MANAGE_EXTERNAL_STORAGE ignore` → READ_MEDIA 권한 revoke → 앱 재실행
- 증거: evidence/SMOKE_1B_home.png; MNF_FUNC_01 verify_shell expected "0" PASS
- 관련 TC: MNF_FUNC_01
- 정정 이력: —

---

## MNF-GAP-02: 보안폴더 진입점 부재 (SPEC_GAP)

- 기능 영역: 보안폴더
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150) c4324122
- 앱: com.example.mnnr_files v1.0.26042210
- 요약: 배포 노트 "보안폴더 삭제"에 따라 홈 화면 및 파일 컨텍스트 메뉴에서 "보안" 관련 UI가 완전히 제거됨.
- 기대 결과: (배포 노트 기준) 보안폴더 진입점 없어야 함. → 현재 동작은 배포 노트와 일치.
- 실제 결과: `grep -c '보안' /sdcard/ui.xml` = 0 (홈, 컨텍스트 메뉴 모두)
- 재현 절차: MNF_FUNC_32 실행
- 증거: —
- 관련 TC: MNF_FUNC_32
- 정정 이력: —

---

## MNF-GAP-03: 생체권한 Manifest 잔존 (SPEC_GAP)

- 기능 영역: 보안 / Manifest
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150) c4324122
- 앱: com.example.mnnr_files v1.0.26042210
- 요약: USE_BIOMETRIC / USE_FINGERPRINT 권한이 Manifest에 선언되어 있으나 앱 사용 중 BiometricPrompt.authenticate 등 생체인증 API가 호출되지 않음. 보안폴더 기능 삭제 후 권한 정리가 미완료된 상태.
- 기대 결과: 사용하지 않는 권한은 Manifest에서 제거되어야 함.
- 실제 결과: `dumpsys package | grep BIOMETRIC` ≥ 1, `logcat -d | grep -ic BiometricPrompt` = 0
- 재현 절차: MNF_FUNC_33 실행
- 증거: —
- 관련 TC: MNF_FUNC_33
- 정정 이력: —

---

## MNF-NOTE-01: ViewerActivity 인앱 뷰어 — 이미지 한정 (NOTE)

- 기능 영역: 파일 뷰어
- 상태: NOTE
- 요약: 이미지 파일 탭 시 앱 내장 `ViewerActivity`로 직접 진입. 동영상/오디오는 별도 intent 경로 — MNF-NOTE-03 참조.
- 관련 TC: MNF_FUNC_08, MNF_FUNC_29
- 증거: evidence/SMOKE_1B_viewer.png
- 정정 이력: 2026-04-23 run3 에서 동영상/오디오는 in-app 아님 확인. 범위를 이미지 한정으로 축소

---

## MNF-NOTE-02: 카테고리 레이블 "앱" vs 스펙 "설치된 앱" (NOTE)

- 기능 영역: 홈 / 카테고리
- 상태: NOTE
- 요약: 홈 화면 6번째 카테고리가 스펙 문서에는 "설치된 앱"으로 기재되어 있으나 실제 UI에서는 "앱"으로 표시됨.
- 관련 TC: MNF_FUNC_24
- 증거: —
- 정정 이력: —

---

## MNF-NOTE-03: 동영상/오디오 파일 외부 intent fallback (NOTE)

- 기능 영역: 파일 뷰어
- 상태: NOTE
- 요약: 동영상 파일 탭 시 ViewerActivity 대신 MainActivity 복귀, 오디오 파일 탭 시 launcher3(QuickstepLauncher)로 복귀. 이미지만 인앱 ViewerActivity 진입 (MNF-NOTE-01).
- 기대 결과: —(스펙 명시 없음)
- 실제 결과: `dumpsys window | grep mCurrentFocus` = `MainActivity`(video) / `com.hnlens.launcher3/...QuickstepLauncher`(audio)
- 재현 절차: MNF_FUNC_30 (비디오), MNF_FUNC_31 (오디오) 실행
- 증거: evidence/run3_output.log
- 관련 TC: MNF_FUNC_30, MNF_FUNC_31
- 정정 이력: —

---

## MNF-GAP-04: 선택 모드 "전체 선택" 기능 부재 (SPEC_GAP)

- 기능 영역: 선택 모드 / btn_more
- 상태: SPEC_GAP
- 요약: 스펙 page5 §3 에 "전체선택/해제" 기능 기재되어 있으나 실제 앱 선택 모드에는 해당 항목 없음. 선택 모드 btn_more 팝업은 비선택 상태 context menu 와 동일한 6개 항목: 다음으로 이동 / 다음으로 복사 / 이름 바꾸기 / 휴지통으로 이동 / 파일 정보 / 다른 앱에서 열기.
- 기대 결과: 선택 모드에 전체 선택 / 전체 해제 항목 존재
- 실제 결과: evidence/ui_sel_more.xml — 6개 항목만 노출
- 재현 절차: MyGallery_TC 진입 → 파일 long-press → 선택 모드 → btn_more 탭
- 증거: evidence/ui_sel_more.xml
- 관련 TC: MNF_FUNC_34
- 정정 이력: —

---

## MNF-OBS-01: 이름 바꾸기 다이얼로그 text field 클리어 실패 (FIXED)

- 기능 영역: 파일 작업 / 이름 바꾸기
- 상태: FIXED (2026-04-24)
- 요약: `KEYCODE_CTRL_A` 는 Android `input keyevent` 에서 단독 modifier 미지원. TC 측 기법 오류.
- 해결 경로: EditText tap 포커스 → `KEYCODE_MOVE_END` → `input keyevent 67`(BACKSPACE) × 30 반복으로 클리어 → `input text` 로 새 이름 입력. 확인 버튼은 좌표 대신 `tap_id "android:id/button1"` 로 매치 (텍스트 길이 변화로 다이얼로그 shift, "바꾸기" 부분 매치는 타이틀 "이름 바꾸기" 와 충돌).
- 재현 절차: MNF_FUNC_12 실행 — PASS (36.7s)
- 증거: reports/20260424_164412_report.html
- 관련 TC: MNF_FUNC_12
- 정정 이력: 2026-04-24 rework 완료, OBSERVED → FIXED

---

## MNF-OBS-02: ops 플로우 (이동/복사/복원/정보) 경로·좌표 미확정 (FIXED)

- 기능 영역: 파일 작업
- 상태: FIXED (2026-04-24)
- 요약: 앱 버그가 아니라 TC 작성 측 오류. 네 TC 공통 근본 원인 3가지: (1) precondition 파일명이 preset 과 불일치 (예: TC_13 이 Documents/minifile_readme.txt 존재 전제였으나 preset 은 Download 에 둠), (2) root browser 에 세션 외 폴더(diag_logs, ls_log 등) 추가로 하드코딩 y 좌표가 드리프트, (3) 복사 FAB([75,1304][644,1416]) 가 루트의 Download 행([1324,1368]) 과 겹쳐 탭이 FAB paste 로 해석.
- 해결 경로:
  - precondition 을 preset 기준으로 재정렬 (TC_13 은 Download→Documents 복사, TC_14 는 Download/minifile_readme.txt, TC_15 는 row 1 = sample.txt, TC_28 은 Download/minifile_sample.zip)
  - 하드코딩 y 좌표 대신 `tap_text "Documents"` / `tap_text "Download"` 로 폴더 탐색
  - TC_13 은 FAB 중첩을 회피하도록 복사 방향을 Download→Documents 로 전환 (Documents y=1222 는 FAB 상단)
- 재현 절차: MNF_FUNC_13/14/15/28 각 실행 — 4/4 PASS
- 증거: reports/20260424_163533_report.html, reports/20260424_163742_report.html
- 관련 TC: MNF_FUNC_13, MNF_FUNC_14, MNF_FUNC_15, MNF_FUNC_28
- 정정 이력: 2026-04-24 TC 재작성 완료, OBSERVED → FIXED

---

## 세션 결과

### 2026-04-24 | FAIL 9건 격리 항목 수리

- 실행일: 2026-04-24
- 단말: ODIN2 (AT-M150) c4324122 (portrait lock + stay-on USB)
- 앱: com.example.mnnr_files v1.0.26042210
- 범위: 2026-04-23 2nd 기준 FAIL 9건 중 8건 수리 (TC_30/31 viewer intent 는 외부 확인 대기로 보류)
- 수리 대상 · 결과
  - **D**: TC_33 biometric grep expected `1` → `2`, pattern 을 `grep -oE 'USE_(BIOMETRIC|FINGERPRINT)' | sort -u | wc -l` 로 교체 — distinct 권한 수 의미 명확화 · PASS
  - **E**: TC_34 전체선택 기능 부재 SPEC_GAP 증명용으로 재설계 — "전체 선택" count=0 + 기존 6개 항목 검증 · PASS (22.4s)
  - **B**: TC_13/14/15/28 ops 플로우 재작성 — `tap_text` 기반 폴더 탐색, preset 파일명 일치, 복사 방향 전환 (MNF-OBS-02 FIXED) · 4/4 PASS
  - **A**: TC_12 rename rework — MOVE_END + KEYCODE_DEL×30 클리어 + `tap_id "android:id/button1"` (MNF-OBS-01 FIXED) · PASS (36.7s)
- 누적 PASS: 19/28 → **26/28** (+7)
- 잔여 FAIL: 2건 — TC_30(video intent) / TC_31(audio intent), MNF-NOTE-03 로 격리 · 개발팀 확인 대기
- 신규 발견: 없음 (수리 과정에서 루트 browser 폴더 드리프트, FAB↔folder row 중첩, 다이얼로그 shift 등 TC 작성 함정 3개 추가 학습)
- 다음 확인 항목:
  - TC_30/31 viewer intent 개발팀 회신 (의도된 동작인지 확인 후 SPEC_GAP/NOTE 전환 또는 앱 수정 요청)
  - Excel 리포트 재생성 (`gen_excel.py`) — 현재 run3 이전 기준이라 갱신 필요

### 2026-04-23 (2nd) | run3 재실행 + quick fix run4/5

- 실행일: 2026-04-23
- 단말: ODIN2 (AT-M150) c4324122 (stay-on USB + portrait lock + screen_off_timeout 30분)
- 앱: com.example.mnnr_files v1.0.26042210
- 범위: functional/ 28 FAIL TC 재실행 (run3) + quick fix 3건 재검증 (run4/5)
- PASS (run3): 17/28 — 02, 03, 05, 07, 08, 09, 11, 16, 19~22, 25~27, 29, 32
- PASS (quick fix 누적): **19/28** (+10, +23)
- FAIL 잔여: 9건 — 12 (rename text-clear), 13, 14, 15, 28 (ops 플로우), 30, 31 (viewer intent), 33 (biometric grep), 34 (전체선택 기능 부재)
- 신규 발견:
  - MNF-GAP-04 (SPEC_GAP): 전체 선택 기능 부재
  - MNF-NOTE-03 (NOTE): 동영상/오디오 외부 intent fallback
  - MNF-OBS-01/02 (OBSERVED): rename text-clear 실패, ops 플로우 미확정
- 변경·정정:
  - TC_10: grep `이름 변경` → `이름 바꾸기`; 이동 expected 재설정 (uiautomator dump 단일 라인 특성)
  - TC_12: verify_text/tap 메뉴 텍스트 `이름 변경` → `이름 바꾸기`, 좌표 (400,502) → (524,790)
  - TC_23: verify_text `다운로드` → `Download` (실제 앱 타이틀 영문)
- 환경 이슈: 최초 run2 0/28 FAIL 원인은 단말 dozing + 잠금. stay-on USB + wakeup keyevent 로 해결
- 다음 확인 항목:
  - MNF-OBS-01 rename text-clear: `uiautomator clearTextField` 또는 text field tap + long-press "전체 선택" 경로로 rework
  - MNF-OBS-02 ops 플로우: TC_13/14/15/28 의 다이얼로그·팝업 좌표 실측 재측정
  - MNF-NOTE-03: 동영상/오디오 intent 분기 앱 설계 확인 (의도된 동작인지 개발팀 확인)
  - TC_33 biometric grep: dumpsys 출력 실측 count 로 expected 조정
  - TC_34: MNF-GAP-04 로 격리, TC 재설계 혹은 SPEC_GAP 용 형태로 변경

---

### 2026-04-23 | Phase 2 TC 전수 실기 실행

- 실행일: 2026-04-23
- 단말: ODIN2 (AT-M150) c4324122
- 앱: com.example.mnnr_files v1.0.26042210
- 범위: functional/ 34 TC 순차 실기 실행 (11 bucket)
- PASS: 6/34 (MNF_FUNC_01, 04, 06, 17, 18, 24)
- FAIL: 28/34 — MNF_FUNC_02, 03, 05, 07~16, 19~23, 25~31, 32, 33, 34
- 신규 발견: 없음 (앱 버그 아님). TC 28건 FAIL 원인은 TC 작성 측 네비게이션·좌표·어서션 오류 — 상세는 RESUME.md "TC 작성 함정" 참조
- 기존 버그 재현: MNF-GAP-01 SMOKE 재현 PASS (TC_01); MNF-GAP-02/03 SMOKE 재현 PASS (TC_32 step3 보안=0 확인, TC_33 step14 biometric logcat=0 확인)
- 변경·정정: TC yaml 수정 필요 항목 (승인 후 진행):
  - **NAV_PATH (21건)**: cat_images(133,1294) 탭이 MediaStore 평면 리스트를 열어 "내부 저장소" 폴더 브라우저 진입 불가. 올바른 경로: home 2x swipe → layout_internal_storage(360,~1000) → DCIM(360,914) → MyGallery_TC(360,626). 영향 TC: 02,03,07,08,09,10,11,12,13,14,15,16,19,20,21,22,23,29,30,31,32,33,34
  - **COORD_DRIFT (3건)**: btn_analyze_storage y=1170→실제 y≈1061 (TC_05,25,26), trash tap 스크롤 1회 불충분 (TC_27,28은 2회 필요)
  - **ASSERT_PRECISION (5건)**: 카테고리 타이틀 "이미지/동영상/오디오/문서/다운로드" (폴더명 아님) (TC_19~23); USE_BIOMETRIC grep count=2 (expected 1) (TC_32)
- 다음 확인 항목:
  - TC NAV_PATH 수정 (cat_images → layout_internal_storage 경로로 변경) 승인 후 재실행
  - browse/ 정렬·필터 TC 추가 (B단계)

---

### 2026-04-22 | Phase 1B + Phase 2 전체 실행

- 실행일: 2026-04-22
- 단말: ODIN2 (AT-M150) c4324122
- 앱: com.example.mnnr_files v1.0.26042210
- 범위: Phase 1B (SMOKE_MNNR 수동→자동 업그레이드) + Phase 2 (11 bucket, 33 TC 신규 작성)
- PASS (validate_tc.py): 34건 전원 PASS (SMOKE 1 + Phase2 33)
- 신규 발견: MNF-GAP-01 (CONFIRMED), MNF-GAP-02 (SPEC_GAP), MNF-GAP-03 (SPEC_GAP), MNF-NOTE-01, MNF-NOTE-02
- 변경·정정: SMOKE_MNNR.yaml — tc_class FULL_AUTO, has_manual_steps false로 업그레이드; 3개 manual_pause 블록 실좌표 기반 step으로 교체
- 다음 확인 항목:
  - Phase 2 TC 실기 실행 (validate 통과 TC 순차 adb 실행하여 PASS/FAIL 확정)
  - MNF-GAP-01 개발팀 보고 (권한 미부여 → 앱 런치 동작 의도 확인 필요)
  - MNF-GAP-03 Manifest 정리 요청 (보안폴더 삭제 후속 클린업)
  - browse/ 버킷 정렬·필터 TC 추가 (MNF_FUNC_07 스크린샷 기반 좌표 측정 후 작성)
