# MiniFile 메뉴 트리 (ODIN2 / AT-M150)

앱: `com.example.mnnr_files` v1.0.26042210 (2026-04-22 빌드)
기기: ODIN2 (AT-M150) 720x1560 @ 320dpi, 3-버튼 내비
**작성 시점**: 2026-04-22 스펙 기반 초기 스켈레톤 (실기 walkthrough 전)
**갱신 책임**: Sonnet — Phase 1B 완료 후 실기 관찰로 교체

범례: `[스펙]` = PDF 스펙, `[관찰]` = 실기 확인, `[갭]` = 스펙-실기 차이.
Sonnet 이 실기 확인하면서 `[스펙]` → `[관찰]` 로 승격, 차이는 `[갭]` + BUG_LOG 등록.

---

## 0. 최초 진입 (앱 데이터 초기 상태)

[스펙] `MANAGE_EXTERNAL_STORAGE` 권한 필요 — 첫 실행 시 시스템 설정 화면(전체 파일 접근) 진입 유도.
[스펙] 런타임 권한: `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_AUDIO`.
[스펙] `PACKAGE_USAGE_STATS` 는 "설치된 앱" 카테고리용.

권한 거부 시 동작 미검증 — Phase 2 `nav/` 에서 분기 TC 작성.

---

## 1. 메인 홈 화면 (MainActivity / Dashboard)

[스펙] 앱 실행 시 최상위 경로(Root) 화면. 단일 Activity 내 구성.

```
홈 (Dashboard)
├─ 상단 검색 바  [스펙]
│  └─ 터치 → SearchActivity 전환
│
├─ 저장공간 카드 (Storage Card)  [스펙]
│  ├─ 전체 / 사용 GB 텍스트
│  ├─ Linear Progress Indicator (사용 비율)
│  ├─ 카드 클릭 → 시스템 내부저장소 설정 (OS 앱 밖)
│  └─ "분석" 버튼 → StorageAnalysisActivity (대용량/중복)
│
├─ 카테고리 모아보기 (6종 그리드)  [스펙]
│  ├─ 이미지       → MediaStore.Images
│  ├─ 동영상       → MediaStore.Video
│  ├─ 오디오       → MediaStore.Audio       (★ 신규 재생 가능)
│  ├─ 문서         → 확장자/Mime 필터
│  ├─ 다운로드     → Download 폴더 바로가기
│  └─ 설치된 앱    → PackageManager (PACKAGE_USAGE_STATS 필요)
│
├─ 특수 폴더 영역  [스펙 vs 갭]
│  ├─ ~~보안 폴더~~   [갭] 2026-04-21 배포 노트: "보안폴더 삭제"
│  │                   USE_BIOMETRIC/FINGERPRINT 권한은 여전히 선언됨
│  │                   → spec_gap/ bucket 확인 대상
│  └─ 휴지통         → Trash 진입
│
└─ 최근 항목 (Recent Files)  [스펙]
   ├─ 가로 스크롤
   └─ 중심 위치 기준 scale/alpha 애니메이션
```

**진입점 명확화**:
- StorageAnalysisActivity 진입점 = 저장공간 카드 내부 "분석" 버튼 (단일 경로)
- 카테고리 진입점 = 홈 그리드 6개 버튼 (단일 경로)
- 보안 폴더 진입점 = **부재 예상** (spec_gap TC 에서 검증)
- 휴지통 진입점 = 홈 특수폴더 영역 → Trash FileBrowser 모드

---

## 2. 파일 탐색 화면 (File Browser)

[스펙] 최상위 이외 일반 폴더 진입 시.

```
File Browser
├─ 상단 타이틀: 현재 폴더명 (동적 변경)  [스펙]
├─ 숨김 처리 (View.GONE):  [스펙]
│  ├─ 상단 카테고리 그리드
│  ├─ 저장공간 카드
│  └─ 최근 항목
├─ 세로 리스트 (폴더 + 파일 페이징)  [스펙]
│  ├─ 폴더 탭   → 하위 경로 진입
│  ├─ 파일 탭   → FileProvider 로 외부 앱 실행
│  └─ 우측 "더보기" 아이콘 → Selection Mode (단일 선택 진입)
└─ 잔상 제거 로직: 진입 시 리스트 즉시 비우고 스크롤 top  [스펙]
```

---

## 3. 선택 모드 (Selection Mode)

[스펙] long-press 또는 우측 더보기 아이콘 클릭 시 활성.

```
Selection Mode
├─ 상단 툴바 전환 (기본 헤더 숨김)  [스펙]
│  ├─ 좌측: 선택 개수 카운트 (e.g. "3개 선택")
│  └─ 우측 퀵 액션:
│     ├─ 공유       → 외부 앱 전송
│     ├─ 삭제       → 휴지통 이동
│     └─ X (닫기)   → 선택 모드 해제
│
└─ 더보기 (오버플로우) 메뉴  [스펙]
   ├─ 전체 선택 / 전체 해제
   ├─ 이동          → 클립보드 저장 + 하단 FAB "여기에 붙여넣기" 활성
   ├─ 복사          → 동일 FAB 활성
   ├─ 이름 변경     [단일 선택 전용]
   ├─ 정보 보기     [단일 선택 전용]
   └─ ~~보안 폴더로 이동~~  [갭] 보안폴더 삭제됨 → 메뉴 부재 예상
```

---

## 4. 상태 및 피드백

[스펙]

```
피드백
├─ 붙여넣기(이동/복사) 진행 다이얼로그
│  ├─ 전체 화면 터치 잠금
│  └─ 현재 N / 전체 M 실시간 카운트
│
└─ 로딩 인디케이터 (ProgressBar)
   ├─ IO 작업(데이터 로드/삭제/복원) 시 화면 중앙
   └─ 백그라운드 리스트 INVISIBLE
```

---

## 5. 휴지통 (Trash)

[스펙]

```
Trash (File Browser 모드 + 제한된 액션)
├─ 타이틀: "휴지통"  [스펙]
├─ 선택 모드 메뉴 제한:  [스펙]
│  ├─ 복원 (Restore)       → 원래 경로로 이동
│  └─ 완전 삭제             → 경고 다이얼로그 → 저장소 영구 삭제
└─ 빈 상태: [스펙 미지정] → 실기 확인 필요
```

---

## 6. 미디어 뷰어 (★ 2026-04-21 빌드 신규)

[스펙 page 1 배포 노트]

```
Viewer
├─ 이미지: FileProvider 외부 앱   [스펙]
├─ 동영상 재생 + 컨트롤러         [스펙·신규]
│  └─ 컨트롤러 세부 (재생/일시정지/seek/닫기) 미지정 → 실기 확인
└─ 오디오 재생                    [스펙·신규]
   └─ 플레이어 UI 미지정 → 실기 확인
```

**오디오 포맷 커버리지**: 현재 preset 은 WAV. MiniFile 이 `audio/mpeg` 한정이면 오디오 카테고리 미노출 → spec_gap 후보.

---

## 7. SearchActivity

[스펙] 홈 상단 검색바 탭 시 전환.

세부 UI 미지정 — Sonnet 이 실기 캡처로 채움.

---

## 8. StorageAnalysisActivity

[스펙] "대용량/중복 파일 탐지 화면" — 세부 미지정.

Sonnet 이 실기 캡처로 채움.

---

## 진입점 요약 (TC 작성 참조)

| 기능 | 진입점 | 예상 TC bucket |
|---|---|---|
| 검색 | 홈 상단 검색바 | `search/` |
| 저장공간 분석 | 홈 저장공간 카드 → "분석" | `storage_analysis/` |
| 이미지/동영상/오디오/문서/다운로드/설치된앱 | 홈 카테고리 그리드 | `categories/` |
| 휴지통 | 홈 특수 폴더 영역 | `trash/` |
| 보안 폴더 | **없음** (삭제됨) | `spec_gap/` |
| FileProvider 외부 열기 | File Browser → 파일 탭 | `browse/` + `viewer/` |
| 선택 모드 | long-press 또는 우측 더보기 | `selection/` |
| 이동/복사/이름변경/정보 | 선택 모드 → 더보기 | `ops/` |
