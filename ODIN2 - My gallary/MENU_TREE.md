# 마이 갤러리 메뉴 트리 (ODIN2 / AT-M150)

앱: `com.example.mygalleryapp` v1.0.26042114 (2026-04-21 빌드)
기기: ODIN2 (AT-M150) 720x1560 @ 320dpi, 3-버튼 내비
검증 시점: 2026-04-21 실기 walkthrough

---

## 0. 최초 진입 (앱 데이터 초기 상태)

첫 실행 시 **미디어 액세스 권한 다이얼로그** 노출:
- `제한된 액세스 허용`
- `모두 허용`
- `허용 안함`

권한 거부 시 동작은 미검증 (TC 작성 시 조건부 분기 필요).

---

## 1. 메인 (3탭)

하단 내비 `bottomNavigation`: **사진 · 앨범 · 휴지통**

### 1-A. 사진 탭 (`nav_photos`, default active)
```
사진 탭
├─ 상단바 `toolbar`
│  └─ ivTitleIcon + tvTitle "마이 갤러리"  (중앙 정렬)
├─ RecyclerView `recyclerView`  (3열 그리드)
│  └─ 날짜 그룹 헤더 `tvDate`  (예: "2026년 04월 21일")
│     └─ 미디어 아이템 `root_layout`
│        ├─ content-desc: "사진: {파일명}, 전체 N개 중 M번째"
│        │                "동영상: {파일명}, 재생시간 mm:ss, 전체 N개 중 M번째"
│        ├─ imageView (썸네일)
│        └─ videoInfoLayout (동영상만)  —  iconPlay + tvDuration
└─ [인터랙션]
   ├─ 탭            → 2. 상세 보기 (사진) / 3. 동영상 재생
   └─ 롱프레스      → 4. 다중 선택 모드
```

### 1-B. 앨범 탭 (`nav_folders`)
```
앨범 탭
├─ 상단바 "앨범" (중앙)
├─ `layoutSort` 정렬 드롭다운 `tvSortLabel` ("최신순" 기본)
│  ├─ 최신순       (default)
│  ├─ 수정 날짜순
│  ├─ 이름순 (ㄱ-ㅎ)
│  ├─ 이름순 (ㅎ-ㄱ)
│  └─ 크기순
└─ 2열 앨범 그리드  (폴더 단위 자동 생성)
   ├─ `ivAlbumThumb` + `tvAlbumName` + `tvAlbumCount` ("N개")
   ├─ content-desc: "앨범: {이름}, N개 항목"
   └─ 탭 → 5. 앨범 내부
```

### 1-C. 휴지통 탭 (`nav_trash`)
```
휴지통 탭
├─ 상단바 "휴지통" · ⋮(보관 기간 설정 / 휴지통 비우기)
├─ 비어 있으면: "미디어가 없습니다."
├─ 삭제된 미디어 목록
├─ [롱프레스] 선택 모드 하단바: 선택 해제 / 전체 복원 / 휴지통 비우기(=영구 삭제)
└─ [아이템 탭] 휴지통 상세뷰
    └─ 상단바: ← / 공유 / ⋮(상세 정보 1개) — 복원 없음 (GAL-BUG-004)
```

---

## 2. 사진 상세 보기 (단일 사진 뷰)

```
사진 상세
├─ 상단바 (반투명 오버레이, 탭 시 토글 표시/숨김)
│  ├─ `btnBack` ← 뒤로가기
│  ├─ `btnShare` 공유
│  ├─ `btnEdit` 편집             → 6. 미디어 편집
│  ├─ `btnFavorite` 즐겨찾기      (토글: "즐겨찾기 추가" / 해제)
│  └─ `btnMore` 더보기            → 2-A. 오버플로우 메뉴
├─ 본문: `viewPager` (좌우 스와이프로 이전/다음)
│  ├─ 제스처: 핀치 줌 인/아웃
│  ├─ 제스처: 단일 탭 → 상단바 토글
│  └─ 제스처: 더블 탭 → 줌 (미검증)
└─ [나가기] BACK → 1-A. 사진 탭 복귀
```

### 2-A. 오버플로우 (⋮) — 사진 vs 동영상

| 항목 | 사진 상세 | 동영상 상세 |
|---|---|---|
| 상세 정보 | O | O |
| 삭제 | O | O |
| 배경화면으로 설정 | O | X (GAL-BUG-007) |

### 2-B. 상세 정보 패널 (하단에서 슬라이드 업)
```
상세 정보 [X 닫기]
├─ 날짜: YYYY-MM-DD HH:MM:SS
├─ 파일명: {파일명}
├─ 경로: /storage/emulated/0/...
├─ 크기: X.XX MB
├─ 해상도: WxH
└─ 위치: lat, lon  (GPS EXIF 있는 경우만, 파란 핀 아이콘)
```
**관찰 사항**: EXIF의 기기 모델(`Model`)은 미노출. 스펙의 "촬영 데이터 추출: ... 기기 모델명(Exif 정보)" 미구현.

---

## 3. 동영상 재생

```
동영상 플레이어 (자동 가로 전환)
├─ 상단바: btnBack / btnShare / btnEdit / btnFavorite / btnMore
│  └─ ⋮ 메뉴: 상세 정보 / 삭제 (GAL-BUG-007)
├─ 상세 정보 필드: 날짜 / 파일명 / 경로 / 크기 / 해상도 (duration 부재 — GAL-BUG-008)
├─ 본문: 비디오 서피스 (단일 탭 → 컨트롤 토글)
└─ 하단 컨트롤
   ├─ 좌: 현재 시간 (hh:mm:ss)
   ├─ 중: seek bar
   ├─ 우: 전체 시간 (hh:mm:ss)
   └─ 버튼: ⏪ 5초 되감기 | ⏯ 재생/정지 | ⏩ 5초 빨리감기
```
**관찰 사항**:
- 시간 표기는 항상 `hh:mm:ss` (플레이어 내부)
- 썸네일 레이블은 `mm:ss` 또는 `hh:mm:ss` (1시간+ 구분 — 4/6 픽스 대상)
- 재생 중엔 `uiautomator dump` idle 얻기 어려움 (연속 프레임 갱신)

---

## 4. 다중 선택 모드 (사진 탭 롱프레스 진입)

```
사진 탭 · 다중 선택
├─ 상단바: 변경 없음 (타이틀 "마이 갤러리" 유지 — 타 앱 대비 아쉬움)
├─ 각 아이템 좌상단 체크박스  (선택됨 = 파란 체크)
└─ 하단 플로팅 액션 바
   ├─ 전체 선택 (O 아이콘) — 토글
   ├─ 공유         → 시스템 공유 시트
   └─ 삭제         → 확인 팝업 → 휴지통 이동
```
**관찰 사항**:
- 선택 개수 카운터 없음
- 선택 모드에서 즐겨찾기/편집 액션 부재 (상세에서만 가능)
- [나가기] BACK 키

---

## 5. 앨범 내부

```
앨범 내부 ({앨범명})
├─ 상단바: ← "앨범명" + "항목 N개 · X.XMB"
├─ 더보기(⋮) 없음  — 앨범 레벨 삭제/이름변경 미지원
├─ 정렬 드롭다운 없음
├─ 본문: RecyclerView (사진 탭과 동일 구조 — 날짜 그룹 + 3열 그리드)
└─ 인터랙션: 사진 탭과 동일 (탭 → 상세, 롱프레스 → 다중 선택)
```

---

## 6. 미디어 편집

| 대상 | 편집 UI |
|---|---|
| 사진 | 회전 / 자르기 / 필터 |
| 동영상 | Trim 전용 (videoRangeSlider, GAL-BUG-009) |

```
미디어 편집 (사진)
├─ 상단바: ← | "미디어 편집" | 저장
├─ 본문: 편집 프리뷰 (회전/필터 적용 상태)
├─ 도구 버튼 행: [회전] [자르기]   → 6-A. 자르기 서브스크린
└─ 필터 스트립 (좌우 스와이프)
   ├─ 원본 (default)
   ├─ 흑백
   ├─ 세피아
   ├─ 자동 보정
   ├─ 빈티지
   └─ 폴라로이드
```

### 6-A. 자르기 서브스크린
```
자르기 [X 취소 | "자르기" | ✓ 확인]
├─ 본문: 자르기 가이드 격자 3x3 오버레이
├─ 중앙 비율 선택 스트립
│  ├─ 1:1
│  ├─ 3:4
│  ├─ 원본 (default)
│  ├─ 3:2
│  └─ 16:9
└─ 하단 모드 전환 (3 탭)
   ├─ state_aspect_ratio  "Crop"      (활성)
   ├─ state_rotate        (↻ 회전)
   └─ state_scale         (반전/스케일)
```

### 6-B. 회전 버튼 (편집 홈에서 직접)
- 1회 탭 → 시계방향 90° 회전 프리뷰
- 저장 전까지 원본 유지

---

## 7. 확인/동의 팝업 (각 지점)

- 삭제 팝업 ("휴지통으로 이동?")
- 편집 저장 결과 저장 팝업 (사본? 덮어쓰기? 미검증)
- 휴지통 복원/비우기 팝업 (휴지통 비어 있어 미검증)

---

## 주요 ID 요약 (TC 셀렉터용)

| ID | 용도 |
|---|---|
| `com.example.mygalleryapp:id/nav_photos/nav_folders/nav_trash` | 하단 탭 |
| `com.example.mygalleryapp:id/tvTitle` | 상단 타이틀 |
| `com.example.mygalleryapp:id/recyclerView` | 미디어 그리드 |
| `com.example.mygalleryapp:id/tvDate` | 날짜 그룹 헤더 |
| `com.example.mygalleryapp:id/root_layout` | 미디어 아이템 (content-desc 풍부) |
| `com.example.mygalleryapp:id/videoInfoLayout` | 동영상 오버레이 |
| `com.example.mygalleryapp:id/tvDuration` | 동영상 시간 표시 |
| `com.example.mygalleryapp:id/btnBack/btnShare/btnEdit/btnFavorite/btnMore` | 상세 상단바 |
| `com.example.mygalleryapp:id/viewPager` | 사진 상세 좌우 스와이프 |
| `com.example.mygalleryapp:id/tvSortLabel` | 앨범 정렬 드롭다운 |
| `com.example.mygalleryapp:id/state_aspect_ratio/state_rotate/state_scale` | 자르기 하단 모드 |

---

## TC Skeleton 대비 누락/추가 항목

**추가 필요** (원래 skeleton에 없었음):
- 권한 플로우 (최초 실행) — `GAL_FUNC_00_first_launch_permission`
- 앨범 정렬 5종 전환 — 앨범 TC에 포함
- 편집 회전 누적 동작 (90° 반복 시 360°)
- 상세 정보 패널 닫기(X) 동작

**검증 시 주의**:
- 선택 모드 진입 시 타이틀 변경 없음 (검증 텍스트로 모드 판정 불가 → 체크박스 존재 여부나 하단 플로팅바로 판정)
- 동영상 재생 중 uiautomator idle 문제 → `screenshot` + `tap_xy` 조합 우선
- 사진 탭 ↔ 앨범 탭 전환 시 사진 탭 그리드가 빈 렌더로 재진입하는 현상 관찰됨 (앱 버그 후보)
- 자동 회전 제어 필수 (동영상 재생이 가로 강제 전환)

**미구현/스펙 불일치**:
- 상세 정보에 기기 모델(Model EXIF) 미노출 — 스펙 `촬영 데이터 추출: 기기 모델명(Exif 정보)`과 다름
- 다중 선택 카운터 부재

**비어 있어 미검증**: 휴지통 내부 (복원/비우기/완전 삭제)
