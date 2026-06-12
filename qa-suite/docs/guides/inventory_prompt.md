# 인벤토리 지시문 — Claude Code 에 그대로 붙여넣기 (v2, 형제 repo 목적지 반영)

> 사용법: 두 원본 repo 가 보이는 환경에서 Claude Code 세션을 열고 아래 블록을
> 붙여넣는다. 한 repo 씩 두 번 수행해도 된다.

---

다음 작업을 수행해줘. 목적은 기존 프로젝트 폴더의 전수 인벤토리를 만들어
qa-suite 모노리포의 MIGRATION.md 체크리스트를 채우는 것이다.
**파일을 이동/수정/삭제하지 말 것 — 읽기와 표 작성만.**

## 대상

- `C:\Users\momen\Projects\tc-runner`
- `C:\Users\momen\Projects\thor2j-tc-appium`
- 단, `tc-runner/qa-suite/` 는 staging 이므로 인벤토리 대상에서 제외한다.

## 절차

1. 각 리포에서 전체 파일 목록을 수집한다
   (숨김/.git/node_modules/__pycache__/가상환경 제외):
   `find . -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/qa-suite/*"`
2. 파일 수가 많으면 폴더 단위로 먼저 훑고, 폴더 안 파일들이 동질적이면
   폴더 단위 행으로 묶어 기록한다 (예: `appium_tc_ledger/` 전체 → 1행).
   이질적이면 파일 단위로 쪼갠다.
3. 각 행에 대해 아래를 판정한다. 내용을 열어봐야 알 수 있으면
   머리 부분만 읽어 판단한다 (대용량 바이너리는 파일명/확장자로).

## 분류 (목적지 — ARCHITECTURE.md §2 책임 구조)

- contracts/                  : 결과·증거 계약 문서 (summary schema, 어휘, redaction)
- analysis/bugs               : 버그 분석/재현조건 문서
- analysis/tc-catalog         : TC 엑셀 파생물, 파서, 분류 산출물
- analysis/sources            : 원천자료 (Figma 추출물, 스펙 PDF, 엑셀 원본)
- learning/engine             : 탐색·anchor·catalog-delta 코드
- learning/catalogs           : 화면·selector·실패원인 카탈로그 (append-only 데이터)
- synthesis/stage1|stage2     : STAGE 지시문·프로파일·정규화/컴파일 산출
- synthesis/validators        : 정적 검증 도구 (validate_tc 등)
- synthesis/export            : 실행 TC 세트
- synthesis/golden            : 골든 reference TC
- automation/bug-repro        : ADB 재현 하니스·BaseTest 모듈 (bash/python)
- automation/tc-step          : step executor (src/ 계열, reporter 포함)
- automation/appium           : Appium 캠페인 코드/설정
- campaigns/<단말 - 앱>       : BUG_LOG/MENU_TREE/RESUME/RESULT (운영 단위 유지,
                                catalog/ 하위만 learning/catalogs 로 분리 — MIGRATION 규칙 5)
- campaigns/manifests         : 캠페인 계약·handoff 문서 (TWO_RUN_GREEN 등)
- campaigns/results           : redacted 검증 결과
- docs/guides|reports|internal: 지침서/보고서/사내 통합 자료
- archive                     : 구버전/용도불명/실험 잔재
- (이주 제외)                 : logs/report/raw/keymap 류 실행 산출물 — var/ 는
                                새로 생성, 기존 산출물은 원본 잔류 또는 archive (MIGRATION 규칙 7)
- 불명                        : 판단 불가 — 반드시 "불명 사유" 기재

## 판정 기준

- 고치는 이유가 "무엇을 검증할지" → analysis
- 누적·재탐색 데이터/코드 → learning (코드=engine, 데이터=catalogs)
- TC 변환·검증·산출 → synthesis
- 고치는 이유가 "어떻게 실행할지" → automation (트랙까지 지정)
- 단말×앱 검증 운영 문서·캠페인 계약 → campaigns
- 사람에게 설명하는 문서 → docs
- **구버전임이 근거로 확인될 때만** archive (대체본 존재·DEPRECATED 표기 등 근거를
  비고에 기재). 사용 예상 기간 추측("6개월 미사용 예상" 류 휴리스틱) 금지.
- **근거가 불충분하면 불명(unknown)으로 둔다. 추측으로 분류하지 말 것.**

## 추가 조사 (이주 위험 평가)

- 스크립트/코드 행에는 하드코딩 경로·상호참조 여부를 표기:
  `grep -rn "C:\\\\|/mnt/|\\.\\./" <대상>` 등으로 절대경로/상대참조를 찾고,
  이동 시 깨질 참조가 있으면 비고에 "참조: <어디서>" 로 기록.
- 진행 중 작업(최근 2주 내 수정: `find -mtime -14`)은 비고에 "활성" 표기
  — 활성 자산은 이주 보류 대상 (캠페인 단위 이동 — MIGRATION 규칙 1).

## 출력

1. qa-suite/MIGRATION.md §4 의 두 인벤토리 표를 채운 마크다운
   (상태는 모두 [I], 불명은 [ ] 유지). 표 열: 상태|원경로|유형|목적지|비고.
2. 요약: 총 행 수, 목적지별 분포, 불명 목록(사유 포함), 활성 자산 목록,
   이동 시 참조 수정이 필요한 파일 목록.
3. 마지막에 "사람 확인 필요" 섹션: 불명 + 판단 근거가 약했던 행 top 10.

표만 정확하면 된다. 분류를 부풀리거나 불명을 줄이려고 추측하지 말 것.
