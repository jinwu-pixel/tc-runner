# CLAUDE.md — analysis/ 영역 규약 (분석·자산)

> ⚠️ **DEPRECATED (2026-06-15)** — 형제 repo 로 이주 완료. SoT = `qa-suite/analysis/CLAUDE.md`
> (`C:\Users\momen\Projects\qa-suite`). 본 staging 본 편집 금지 (provenance: source-deprecated).

루트 CLAUDE.md 를 먼저 따른다. 이 영역은 "무엇을 검증할지"를 다룬다.

## 버그 분석 (bugs/)
- bugs/*.md 는 **automation/bug-repro 트랙의 유일 입력 SoT** 다 (다른 트랙에는
  유일 입력 규칙을 적용하지 않음 — 루트 §2).
- 새 분석은 bugs/TEMPLATE.md 를 복사해 BUG-XXXXX.md 로 작성.
- 필수 기재: 판정 시그니처(프로세스 귀속 방법 포함), 알려진 오탐,
  user 빌드 권한 제약, 합격 기준. 못 채우는 항목은 "미해결 질문"에.
- 트래커 분석(Claude in Chrome 등) 결과를 옮길 때 추정과 사실을 구분해
  기술한다. 단정 톤 지양.

## TC 카탈로그 (tc-catalog/)
- 원본 엑셀은 sources/ 에 두고, 파생물(YAML, 분류 결과)만 여기에.
- AUTO/MANUAL 휴리스틱 분류 산출물은 사람 검증 전/후를 파일명 또는
  메타데이터로 구분한다 (예: *_unverified.yaml / *_verified.yaml).
- 파서·스크립트 수정 시 샘플 입력으로 회귀 확인 후 전달.

## 원천자료 (sources/)
- 읽기 전용 취급. 가공은 tc-catalog/ 나 docs/ 에서.
- 대용량 바이너리(PDF, xlsx)는 필요한 것만. 중복 버전은 archive/ 로.
