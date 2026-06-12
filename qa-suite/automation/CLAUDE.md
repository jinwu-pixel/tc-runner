# CLAUDE.md — automation/ 영역 규약 (실행)

루트 CLAUDE.md 를 먼저 따른다. 이 영역은 "어떻게 실행할지"를 다룬다.

> **목표 구조 매핑**: 본 영역(staging `automation/`)은 형제 repo 의
> `automation/bug-repro` 에 해당한다. tc-step(step executor)·appium(캠페인)은
> 별도 하위 트랙으로 병존하며 경계는 ARCHITECTURE.md §5. 이주 시 `tests/`
> 패키지는 `modules/` 로 개명한다 (MIGRATION 규칙 6 — staging 에서는 무이동).

## 모듈 구현 (tests/)
- 입력은 ../analysis/bugs/BUG-XXXXX.md 가 유일. 문서 미비 시 구현 금지.
- tests/base_test.py 의 BaseTest 상속. run_once 반환은 닫힌 enum 한정:
  "PASS"|"SKIP" 또는 (status, reason), status ∈ PASS/WARN/FAIL/SKIP/INFRA_FAILURE.
  미등록 문자열·형식 오류는 INFRA_FAILURE 로 집계된다 (PASS 계산 금지).
- 판정 경로의 adb 실패(timeout·불통·실행 파일 부재)는 InfraFailure 전파 (fail-closed).
  adb 호출은 argv 기반 CommandResult — 실패를 빈 문자열로 바꾸지 않는다.
- 판정은 문서의 시그니처만. 광역 grep 금지, 알려진 오탐을 FAIL 에 넣지 않음.
- 고정 sleep 대신 self.poll_until() 우선. FAIL/WARN 아티팩트는 BaseTest 가
  자동 수집 — 버그 특이 항목만 extra_artifacts() 오버라이드. 수집 실패는
  collection_errors.txt 로 기록 (숨기지 않음).
- 하니스 래퍼는 미실행 PASS 추정 금지 — 총 실행 수·집계의 source of truth 는
  하니스 summary.txt 실집계. summary 부재/모순, 요청 시나리오·count 와의
  불일치(순서·중복 포함 정확 대조, 행 count == 요청 count > 0)는 INFRA_FAILURE.
- 회차 순서는 results.csv 의 (scenario, index) 로 복원 — 누락 index 만 PASS,
  복원 후 summary 와 시나리오별 P/W/F 재대조. results.csv **파일 부재**(summary
  가 all-PASS 여도 거부 — 하니스는 시작 시 헤더를 반드시 생성) / 필수 헤더 누락 /
  미등록 level(WARN·FAIL 외) / 미등록 scenario / index 범위 위반 / 중복 index
  = INFRA_FAILURE. 헤더만 있는 csv + all-PASS summary 는 정상.
- 요청 계약 (하니스 실행 전 차단): 빈 scenario 토큰("basic,,toggle"), 중복
  시나리오 요청, count<=0, extra_args 의 예약 옵션
  (-s/--serial, -S/--scenarios, -n/--count, -o/--out, --menu/--no-menu) = INFRA_FAILURE.

## 검증된 하니스 (harness/)
- 파이썬 재작성 금지. tests/bug_23025_harness.py 패턴으로 subprocess 래핑.
- bash 는 bare "bash" 의존 금지 — resolve_bash() 로 Git Bash 만 허용
  (WSL/System32 bash = INFRA_FAILURE). config.local.yaml 의 bash_path 로 명시
  가능하나 **명시 경로도 Git 경로 검증** — 경로 구성요소 정확 일치 `git` 또는
  `portablegit*` 만 인정 (notgit/GitHub/git-tools/cygwin/msys 거부). resolved
  경로는 run_dir/bash_resolved.txt 에 기록.
- 하니스 수정 시 bash -n 확인. 외부 운용 폴더(C:\adb-tests 등)로 복사가
  필요하면 여기(harness/)를 원본으로 삼아 단방향 복사만 한다.

## 실행 (runner.py)
- 실행 위치는 automation/ (상대경로 기준). `python runner.py`.
- 설정은 config.local.yaml (config.example.yaml 복사 후 작성, git 추적 제외).
  실 단말 serial 등 로컬 식별자는 config.local.yaml 에만 (이식성 보호).
- exit code (CI 게이트): INFRA_FAILURE 존재 3 > FAIL 존재 1 > WARN 존재·전체
  SKIP 2 > PASS(+SKIP) 0. 실행 결과 0건·config 문제·미등록 test·단말 0대/2대+ = 3.
- runner 는 최외곽까지 fail-closed — 예상 밖 예외도 exit 3 으로 닫힌다.
- 결과는 report/<run_id>/summary.json (run_id = UTC YYYYMMDDTHHMMSSZ,
  tc-runner schema_version=1 필드 shape 호환 adapter = report_adapter.py).
  단, summary 집계 의미는 비중복(all-SKIP → skipped, passed=False)으로 legacy
  Reporter 와 다름 — 의미 통합은 트랙 B (report_adapter.py docstring 참조).
- 신규 모듈은 TEST_REGISTRY 등록 + config.example.yaml 주석 한 줄.

## 프레임워크 self-test (selftest/)
- 단말 호출 없는 unit test. 실행: `pytest qa-suite/automation/selftest`
  (tc-runner 루트 tests/ 패키지와 이름 충돌로 혼합 수집 금지 — conftest 가 격리).
- runner/BaseTest/래퍼/adapter 동작 변경 시 selftest 동기 갱신 (RED→GREEN).

## Appium (appium/)
- 진행 중 캠페인 자산은 캠페인 단위로만 이동/개편 (중간 개편 금지).
- TC 레저 형식 변경은 사용자 승인 후.

## 사내 연동 (integration/)
- Jira 등 외부 시스템 쓰기(티켓 생성/코멘트)는 dry-run 모드를 기본으로
  구현하고, 실제 쓰기는 사용자 명시 승인 후 실행.
