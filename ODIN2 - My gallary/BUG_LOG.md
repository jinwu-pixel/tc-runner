# 마이 갤러리 · 버그/이슈 관찰 로그 (ODIN2)

앱: `com.example.mygalleryapp` v1.0.26042114
기기: ODIN2 (AT-M150)
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
| GAL-BUG-001 | 사진 상세 | SPEC_GAP | 상세 정보에 EXIF Model 미노출 | GAL_FUNC_06/07 | evidence/12_detail_info.png |
| GAL-BUG-002 | 사진 다중선택 | OBSERVED | 선택 카운터/타이틀 미갱신 | GAL_FUNC_03 | evidence/31_longpress_select.png |
| GAL-BUG-003 | 네비 | OBSERVED | 탭 왕복 후 사진 탭 빈 렌더 | - | evidence/bug003_repro.png |
| GAL-BUG-004 | 휴지통 | OBSERVED | 개별 선택 복원·상세뷰 복원 UX 부재 | GAL_FUNC_05 | evidence/trash_after_longpress.png |
| GAL-BUG-005 | 편집 | OBSERVED | 편집 미저장 BACK 확인 다이얼로그 부재 | GAL_FUNC_09 | evidence/ui_gal_edit_cancel.xml |
| GAL-BUG-006 | 편집 | SPEC_GAP | 저장 시 덮어쓰기 없음 (항상 사본) | GAL_FUNC_12 | evidence/ui_post_save.xml |
| GAL-BUG-007 | 동영상 상세 | SPEC_GAP | ⋮에 '배경화면으로 설정' 부재 | - | evidence/ui_vid_detail_menu.xml |
| GAL-BUG-008 | 동영상 상세 | SPEC_GAP | 상세 정보에 duration 부재 | - | evidence/ui_vid_detail_info.xml |
| GAL-BUG-009 | 동영상 편집 | NOTE | 편집 = Trim 전용 | - | evidence/ui_vid_edit.xml |

---

## GAL-BUG-001

- 기능 영역: 사진 상세
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 상세 정보 패널에 EXIF Model 필드 미노출
- 기대 결과: 스펙 "촬영 데이터 추출 — 기기 모델명(Exif 정보)" 에 따라 Model 필드 노출
- 실제 결과: 날짜 / 파일명 / 경로 / 크기 / 해상도 / 위치(GPS) 만 노출 (preset EXIF는 Make=ALTech, Model=AT-M150 주입됨)
- 재현 절차:
  1. 사진 탭
  2. IMG 22 탭 → 상세뷰
  3. ⋮ → 상세 정보
- 증거: evidence/12_detail_info.png, evidence/12b_detail_info_gps.png
- 관련 TC: GAL_FUNC_06, GAL_FUNC_07
- 정정 이력: —

## GAL-BUG-002

- 기능 영역: 사진 다중선택
- 상태: OBSERVED
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 선택 모드 진입 시 타이틀 미변경, 선택 개수 카운터 부재
- 기대 결과: 타이틀 "N개 선택" 형태로 변경
- 실제 결과: 타이틀 "마이 갤러리" 유지. 선택 여부 단서는 체크박스 + 하단 플로팅바 뿐
- 재현 절차:
  1. 사진 탭
  2. 임의 아이템 롱프레스
- 증거: evidence/31_longpress_select.png
- 관련 TC: GAL_FUNC_03
- 정정 이력: —

## GAL-BUG-003

- 기능 영역: 네비
- 상태: OBSERVED
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 앨범→MyGallery_TC→휴지통→사진 경로 후 사진 탭 본문이 비어 있음
- 기대 결과: 탭 전환 후 항상 동일 목록 렌더
- 실제 결과: 사진 탭 active, tvDate 0, root_layout 0. force-stop 후 재실행 시 복구
- 재현 절차:
  1. 사진 상세뷰에서 BACK → 사진 탭
  2. 하단 '앨범' 탭
  3. MyGallery_TC 앨범 진입
  4. BACK → 앨범 탭
  5. 하단 '휴지통' 탭
  6. 하단 '사진' 탭 → 빈 본문 확인
- 증거: evidence/bug003_repro.png, evidence/ui_bug003_photos_after.xml
- 관련 TC: —
- 정정 이력:
  - 2026-04-22: SUSPECT → OBSERVED, 최소 재현 절차 확정

## GAL-BUG-004

- 기능 영역: 휴지통
- 상태: OBSERVED
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 휴지통에서 개별 선택 복원 및 상세뷰 복원 진입점 부재
- 기대 결과: 선택된 항목만 복원하거나, 상세뷰에서 복원 액션 제공
- 실제 결과:
  - 선택 모드 하단바: 선택 해제 / 전체 복원 / 휴지통 비우기(=영구 삭제)
  - 상세뷰 상단바: ← / 공유 / ⋮ (⋮ = 상세 정보 1개)
  - 복원은 '전체 복원' 경로로만 가능
- 재현 절차:
  1. 사진 탭 임의 항목 삭제 → 휴지통 이동
  2. 휴지통 탭 → 항목 롱프레스 → 하단바 확인
  3. 항목 탭 → 상세뷰 상단 ⋮ 확인
- 증거: evidence/trash_after_longpress.png, evidence/trash_detail_overflow_menu.png
- 관련 TC: GAL_FUNC_05
- 정정 이력:
  - 2026-04-21: 최초 기록 "복원 기능 자체 없음" (CONFIRMED)
  - 2026-04-22: 전체 복원 존재 재검증. 쟁점을 개별 선택 복원 / 상세 복원 UX 갭으로 재정의

## GAL-BUG-005

- 기능 영역: 편집
- 상태: OBSERVED
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 편집 변경 후 BACK 시 확인 다이얼로그 없이 변경 내용 폐기
- 기대 결과: 변경사항 존재 시 저장/저장 안 함/취소 다이얼로그 노출
- 실제 결과: BACK 즉시 상세뷰 복귀, 변경 내용 소실
- 재현 절차:
  1. 사진 상세 → 편집
  2. 회전 적용
  3. BACK 키
- 증거: evidence/ui_gal_edit_cancel.xml
- 관련 TC: GAL_FUNC_09
- 정정 이력: —

## GAL-BUG-006

- 기능 영역: 편집
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 편집 저장이 항상 사본 경로로만 수행됨 (원본 덮어쓰기 옵션 부재)
- 기대 결과: 사본 / 덮어쓰기 선택 팝업 또는 스펙 반영
- 실제 결과:
  - 저장 경로: /sdcard/Pictures/MyGallery/EDIT_COPY_{timestamp}.jpg
  - 원본 /sdcard/DCIM/MyGallery_TC/IMG_*.jpg 의 mtime/size 변경 없음
- 재현 절차:
  1. 사진 상세 → 편집
  2. 회전 적용 → 저장
  3. EDIT_COPY 생성 + 원본 mtime 불변 확인
- 증거: evidence/ui_post_save.xml
- 관련 TC: GAL_FUNC_12
- 정정 이력:
  - 2026-04-22: regression anchor 재확인

## GAL-BUG-007

- 기능 영역: 동영상 상세
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 동영상 상세 ⋮ = 상세 정보 / 삭제 2개. 사진 상세(3개) 대비 '배경화면으로 설정' 부재
- 기대 결과: 스펙 확인 대상 (사진과 동일 3개 노출 여부)
- 실제 결과: 상세 정보 / 삭제 2개만 노출
- 재현 절차:
  1. 사진 탭 VID_20s 탭 → 상세뷰
  2. 상단 ⋮
- 증거: evidence/ui_vid_detail_menu.xml
- 관련 TC: —
- 정정 이력: —

## GAL-BUG-008

- 기능 영역: 동영상 상세
- 상태: SPEC_GAP
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 동영상 상세 정보 패널에 재생시간(duration) 필드 부재
- 기대 결과: 동영상 메타데이터로서 duration 노출
- 실제 결과: 날짜 / 파일명 / 경로 / 크기 / 해상도 5필드 (썸네일 라벨엔 duration 표기됨)
- 재현 절차:
  1. 동영상 상세 → ⋮ → 상세 정보
- 증거: evidence/ui_vid_detail_info.xml
- 관련 TC: —
- 정정 이력: —

## GAL-BUG-009

- 기능 영역: 동영상 편집
- 상태: NOTE
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 요약: 동영상 편집은 Trim 전용 (videoRangeSlider + tvTrimDuration). 사진 편집(회전/자르기/필터)과 별개 UI
- 기대 결과: —
- 실제 결과:
  - 상단: btnBack / tvEditTitle / btnSave
  - 본문: videoPreview
  - 하단: videoEditToolbar / tvTrimDuration / videoRangeSlider
- 재현 절차:
  1. 동영상 상세 → 상단 편집
- 증거: evidence/ui_vid_edit.xml
- 관련 TC: —
- 정정 이력: —

---

## 세션 결과

- 실행일: 2026-04-22
- 단말: ODIN2 (AT-M150)
- 앱: com.example.mygalleryapp v1.0.26042114
- 범위: P2(동영상 상세 ⋮ / 즐겨찾기 / 편집) + P1(편집 overwrite 재확인 · 휴지통 즉시 삭제 · 휴지통 비우기) + P3(BUG-003 재현)
- PASS:
  - 동영상 즐겨찾기 토글
  - 편집 저장 사본 생성 + 원본 mtime 불변 (GAL-BUG-006 regression anchor)
  - 휴지통 즉시 삭제 (선택 → 하단 '휴지통 비우기' → 시스템 영구삭제 다이얼로그 허용)
  - 휴지통 비우기 (상단 ⋮ → '휴지통 비우기' → 동일 다이얼로그)
- 신규 발견: GAL-BUG-007, GAL-BUG-008, GAL-BUG-009
- 변경/정정:
  - GAL-BUG-003 SUSPECT → OBSERVED
  - GAL-BUG-004 범위 재정의 (전체 복원 존재 확인, 쟁점 축소)
  - 휴지통 상세뷰 ⋮ 기재 오류 수정 (이전 "즉시 삭제" → 실제 "상세 정보")
- 다음 확인 항목:
  - 개별 선택 복원 가능 여부
  - 동영상 상세의 '배경화면으로 설정'이 스펙인지 미지원인지
