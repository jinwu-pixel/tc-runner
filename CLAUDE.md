## Project Purpose

tc-runner는 단순 자동화 실행기가 아닌 누적 학습 루프다.

1. 신규 앱을 빠르고 정확하게 메뉴트리·화면·기능 파악
2. 수정 버전 출시 시 전수 재탐색이 아닌 delta 중심 재탐색
3. 탐색·runtime·실패원인·화면·selector 후보를 누적 데이터로 보존
4. 누적 데이터를 다음 TC 작성과 delta 판단에 재사용
5. 데이터가 남지 않는 자동화는 거부

모든 PR/개선안은 다음 3축으로 평가한다.

- 데이터가 남는가
- 정확성·재현성을 해치지 않는가
- 다음 작업에 누적되는가

---

# TC 변환 규칙

TC 변환 요청 시 반드시 아래 파일을 읽고 따를 것:

## 1단계 (원본 → CTF 정규화)
- `tc_prompts/STAGE1_NORMALIZE.md` 를 읽고 지시를 따를 것
- `tc_prompts/OPERATIONAL_RULES.md` 를 항상 함께 적용할 것

## 2단계 (CTF → 실행 TC 컴파일)
- `tc_prompts/STAGE2_COMPILE.md` 를 읽고 지시를 따를 것
- `tc_prompts/device_profile.yaml` 과 `tc_prompts/runner_capability.yaml` 을 입력으로 사용할 것
- `tc_prompts/OPERATIONAL_RULES.md` 를 항상 함께 적용할 것

## 검증
- 출력 완료 후 `python validate_tc.py <출력파일>` 실행하여 통과 확인
- 골든 TC 참조: `golden_tc_set/` 디렉토리의 형식을 따를 것

---

# TC 작성/수정 절차 게이트

TC를 새로 작성하거나 기존 TC를 수정할 때, 아래 게이트 체인을 **순서대로** 따른다.
각 단계는 이전 단계의 통과를 전제 조건으로 한다.

```
GATE 1 → GATE 2 → GATE 3 → GATE 4
```

### GATE 1. 작성/수정

- 모든 compiled TC의 metadata에 `execution_type`, `manual_detail` 을 **반드시** 포함할 것
- 두 필드는 사람이 임의로 채우는 값이 아니라, step-level 정보에서 **파생 계산**하는 값이다
- 파생 계산 규칙은 `tc_prompts/STAGE2_COMPILE.md` Step 4를 참조할 것 (이 파일이 source of truth)

### GATE 2. 검증 실행

- 작성/수정 완료 후 반드시 실행:
  ```
  venv/Scripts/python.exe validate_tc.py <출력파일 또는 --dir 디렉토리>
  ```
- placeholder FAIL(UNRESOLVED_PARAMS)은 허용하되, **execution_type/manual_detail 관련 FAIL은 허용하지 않는다**
- **Reporting Vocabulary Rule**: `PASS` 단독 표기 금지. 항상 한정사를 붙여 아래 4종으로 구분한다.
  - **validate PASS**: `validate_tc.py` 정적 검증 통과
  - **runtime PASS**: `cli run`으로 실 단말에서 step 전부 PASS
  - **manual evidence observed**: 수동 adb/스크린샷/uiautomator dump로 실기 관찰
  - **BUG-GAP observed**: 실기에서 버그 또는 스펙 갭 발견

  `validate PASS`는 `runtime PASS`를 의미하지 않는다.
  FAIL도 가능한 한 컨텍스트를 붙인다.
  예: `step verify_text FAIL`, `load_tc rejection`, `runtime precondition FAIL`
- **Source-of-truth Policy**: 신규 action·schema·catalog 항목 추가는 정의(스키마/문서) → 코드 → 테스트 정렬을 같은 PR 안에서 맞춘다. 스키마·문서·loader·runner·테스트 중 일부만 갱신된 상태는 drift로 간주한다. 임시 예외가 필요하면 drift risk와 후속 정리 티켓을 보고서에 명시한다.

### GATE 3. 검증 통과 확인

- GATE 2에서 FAIL이 발생하면 **다음 단계 진행을 금지**한다
- 원인을 수정하고 GATE 2를 재실행하여 PASS를 확인한 후에만 진행할 것

### GATE 4. 리포트 생성

- 검증 통과 후에만 실행:
  ```
  venv/Scripts/python.exe gen_excel.py
  ```
- gen_excel.py는 execution_type/manual_detail 누락 시 즉시 중단된다 (fail-fast)
- **Evidence Accumulation Rule**: TC 작성/실행/실패 산출물은 휘발 출력에 그치지 않고 누적 자료로 남긴다.
  - validate/lint 결과 → `reports/lint/<run_id>.json` (planned from PR 1)
  - runtime 실행 결과 → 현재 `reports/*_report.html`, 향후 구조화 시 `reports/<run_id>/`
  - runtime preflight 결과 → `reports/preflight/<run_id>/` (planned from PR 2)
  - 화면/selector/실패원인 catalog → `<app>/catalog/` (planned from PR 3)

  세션 로그·메모리만에 의존하는 자동화는 거부한다.
  아직 구현되지 않은 누적 경로는 planned 항목으로만 취급하며, 실제 구현은 각 PR에서 별도로 수행한다.

---

# 이슈 기록 포맷 (단말×앱 프로젝트)

폴더명: `<단말명> - <앱명>/`
기본 파일: BUG_LOG.md / MENU_TREE.md / RESUME.md

## BUG_LOG.md
- 요약표 열: ID | 기능 영역 | 상태 | 요약 | 관련 TC | 증거
- 항목 필드(통일): 기능 영역 / 상태 / 단말 / 앱 / 요약 / 기대 결과 / 실제 결과 / 재현 절차 / 증거 / 관련 TC / 정정 이력
- 본문은 현재 상태만, 과거 변경은 `정정 이력`에 한 줄
- Regression PASS는 본문에 섞지 말고 하단 `## 세션 결과`로 분리

## 세션 결과 블록
- 실행일 / 단말 / 앱 / 범위 / PASS / 신규 발견 / 변경·정정 / 다음 확인 항목

## 상태 어휘
SUSPECT / OBSERVED / CONFIRMED / SPEC_GAP / NOTE / FIXED / WONTFIX

## 원칙
- 추가보다 삭제 우선
- 취소선·장문 주석·중복 서술 금지
- 없는 정보는 "—"로 표기, 추론 금지
- 단순 포맷 통일은 정정 이력에 기록하지 않음 (내용·상태·범위 변경만)
