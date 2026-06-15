# qa-suite 모노리포 — 아키텍처 (v2, 2026-06-12 형제 repo 확정)

> **개정 이력**
> - 2026-06-15 (v2.1, staging): 인벤토리 결정 반영 — contracts/ 정의를 "트랙 간 입력·결과·증거
>   인터페이스"로 확장(+ tc-step/appium/repo-policy 서브) · `tools/` 신규 최상위(repo-ops) ·
>   `synthesis/examples/` 신설. 근거 = MIGRATION.md §4.3 결정 로그. 파일이동·코드수정 없음.

## 0. 배치 (확정)

- 최종 위치 = **별도 형제 repo `C:\Users\momen\Projects\qa-suite`**.
- 현재 `tc-runner/qa-suite/` 는 **설계·검증용 staging** — 문서 개정과 프레임워크
  검증(selftest)만 수행. 자산 이주·신규 자산 추가 금지.
  예외: **사용자 승인된 실단말 framework smoke** 는 허용 (결과는 FRAMEWORK_SMOKE_ONLY
  로 기록, BUG 판정 증거 사용 금지 — 산출물은 ignored 영역에만).
- 이주 완료 전까지 원본 SoT 는 tc-runner / thor2j-tc-appium 에 유지.
- 출처 보존: subtree/submodule 없이 **provenance manifest** (MIGRATION.md §3).
- staging 한정 장치인 `qa-suite/conftest.py` (tc-runner 루트 tests 패키지와의
  pytest 수집 충돌 격리)는 형제 repo 생성 시 필요성 재평가.

## 1. 한 줄 요약

분석(무엇을)·학습(누적)·합성(TC 변환)·실행(어떻게)을 한 repo 에 영역 규약으로
분리하고, 실행 트랙별 입력 SoT 를 명시한다. 데이터가 남지 않는 자동화는 도입하지 않는다.

## 2. 책임 구조 (목표 — 형제 repo 기준)

```text
qa-suite/
  contracts/                 # 트랙 간 입력·결과·증거 인터페이스 (2026-06-15 확장):
                             #   결과·증거 = summary schema v1, run bundle(run_id), 어휘 4축, redaction
    tc-step/                 #   입력: tc_step_schema.json (validate_tc·tc_loader 공통 소비 스키마)
    appium/                  #   입력: tc_standard_format.md (FocusRule 트랙 TC 포맷, prose)
    repo-policy/             #   커밋 경로 정책 (redaction 과 같은 커밋표면 계약 — push audit 소비)
                             #   ※ 본문 작성은 후속 (§6)
  analysis/
    bugs/                    # 버그 재현 입력 SoT (TEMPLATE 강제) — bug-repro 트랙 전용
    tc-catalog/              # **정적 TC 파생물** (엑셀 기원 파서·분류 산출물, v1 유지)
                             #   ↔ learning/catalogs 는 **단말 관측 데이터** — 경계 상이
    sources/                 # 원천자료 읽기전용 (v1 유지)
  learning/
    engine/                  # explorer / menu_anchor / catalog_delta 코드
    catalogs/                # append-only 커밋 데이터 — <단말명 - 앱명>/ 단위
  synthesis/
    stage1/                  # STAGE1_NORMALIZE 지시문 + 정규화 산출
    stage2/                  # STAGE2_COMPILE·OPERATIONAL_RULES 지시문 + 프로파일 + 컴파일
    validators/              # validate_tc 등 GATE 2 정적 검증 도구
    export/                  # 실행 TC 산출 세트
    golden/                  # 골든 reference TC set (권위 — 검증된 기준)
    examples/                # 비권위 샘플 TC (folder/kids nav 등 — golden 아님) [2026-06-15]
  automation/
    bug-repro/               # BaseTest + bash 하니스 래퍼 (패키지명 modules/ — §5)
    tc-step/                 # tc-runner step executor (src/ 계열 + reporter)
    appium/                  # thor2j 단말 검증 캠페인 코드
  campaigns/                 # ※ campaigns/** 의 **모든 커밋 후보**는 residual-scan PASS
                             #   필수 (BUG_LOG·RESULT 도 단말 식별자 포함 가능).
                             #   게이트 도구 구현 전 실행 결과 = local carry only
    <단말명 - 앱명>/          # BUG_LOG / MENU_TREE / RESUME / RESULT 시리즈
                             #   — 세션 재개 운영 단위는 한 폴더 유지 (catalog 만 분리)
    manifests/               # 캠페인 계약 (TWO_RUN_GREEN / DEVICE_FIT_SKIP / INFRA_FAILURE 등)
    results/                 # redacted 결과만 커밋
  var/                       # local-only: logs / report / raw / keymap — 커밋 영구 금지
  tools/                     # repo-ops 도구 (push audit 등 — QA 도메인 아닌 repo 관리) [2026-06-15]
  docs/                      # 지침/보고서/사내 통합 자료 (v1 동일)
  archive/                   # 격리 보관 (삭제 금지, v1 동일)
  _inbox/                    # 미분류 유입물 (주 1회 트리아지, v1 동일)
```

## 3. 커밋 분류 (불변 원칙)

| 분류 | 대상 | 정책 |
|---|---|---|
| tracked code | learning/engine, synthesis, automation, tools | 일반 |
| tracked data (append-only) | learning/catalogs | **재생성물 아님** — audit 류 도구가 generated 로 오분류 금지 (tc-runner §8.2 2026-05-22 교훈) |
| tracked docs | contracts, analysis, docs | 일반 |
| tracked docs (redaction 게이트) | campaigns/** 전체 | 모든 커밋 후보 residual-scan PASS 필수 — 게이트 구현 전 = local carry only |
| local-only | var/ 전체, config.local.yaml, raw/keymap | 커밋 영구 금지 (redaction 정책 lock — tracked archive/ 경유 우회도 금지) |

## 4. 입력 SoT — 트랙별

1. **`bugs/*.md 유일 입력` 규칙은 automation/bug-repro 에만 적용** — 문서 미비 시 구현 금지.
2. synthesis 입력 = 원본 TC + 단말·러너 프로파일 + golden (STAGE 변환 → GATE 체인).
3. learning 입력 = 단말 탐색 관찰 — catalog 누적이 산출이자 다음 작업의 입력 (delta 판단).
4. 판정은 프로세스/디스플레이 귀속 필수, 광역 grep 금지 (v1 원칙 유지).
5. user 빌드 제약은 1급 정보 / 검증된 하니스는 래핑·재작성 금지 (v1 원칙 유지).

## 5. 실행 프레임워크 3개 — 병존 경계

| 트랙 | 실행기 | 입력 SoT | 결과 계약 |
|---|---|---|---|
| bug-repro | runner.py + BaseTest/하니스 래퍼 | analysis/bugs | summary.json schema v1 (adapter, 비중복 집계 의미) |
| tc-step | cli run (action_runner) | synthesis/export | run bundle summary.json schema v1 (원 계약) |
| appium | thor2j 캠페인 러너 | campaigns/manifests | 캠페인 계약 어휘 — schema v1 정렬은 후속 |

- 결속은 **contracts/ 의 결과 스키마 수준에서만**. 공통 orchestrator 는 cross-runner
  집계의 실수요 발생 전 구현 금지.
- 단말 점유 작업은 동시 1개 (v1 규칙 유지).
- 이주 시 bug-repro 의 `tests` 패키지는 **`modules/` 로 개명** — tc-step 의 시험
  스위트(tests/)와 repo 내부 이름 충돌 방지 (MIGRATION 규칙 6).

## 6. 후속 (이번 개정 범위 밖 — 각각 별도 티켓)

- contracts/ 본문 작성: 어휘 4축 계약 / redaction 정책 이식 / run bundle 명세 /
  입력 포맷(tc-step/tc_step_schema.json · appium/tc_standard_format.md) / repo-policy(경로 게이트)
- appium 결과의 schema v1 정렬
- campaigns/** 의 residual-scan 게이트 도구 구현 (구현 전 = local carry only)
- tools/ git_safe_push_audit planned-port: 엔진·테스트 보존 + 정책 → contracts/repo-policy/ 교체 (MIGRATION §4.3-2)
- 형제 repo 생성·git init·이주 개시 (사용자 명시 승인 게이트)
