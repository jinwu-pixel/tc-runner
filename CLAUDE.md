## 1. Project Vision

tc-runner는 단순 자동화 실행기가 아닌 **누적 학습 루프**다.

### 1.1 무엇을 하는가
1. 신규 앱: 메뉴트리·화면·기능을 빠르게 파악
2. 수정 빌드: 전수 재탐색이 아닌 **delta 중심 재탐색**
3. 탐색·runtime·실패원인·화면·selector 후보를 **카탈로그로 누적**
4. 누적 데이터를 다음 TC 작성·delta 판단에 재사용
5. 데이터가 남지 않는 자동화는 거부

### 1.2 평가 3축
- 데이터가 남는가
- 정확성·재현성을 해치지 않는가
- 다음 작업에 누적되는가

세 축 중 하나라도 부정이면 채택하지 않는다.

### 1.3 본 repo의 정체성
- tc-runner = 학습 루프 · 탐색 · 핀포인트 · 사용자와의 파트너 작업
- 정형 spec compliance / CI/CD / Jira 정형 자동화 = `thor2j-tc-appium` 분기 (§2.5)

### 1.4 개선 훅
본 vision 자체의 작동·해석 변경 발견 시 §8에 기록.

---

## 2. Core Operating Principles

본 섹션은 트랙·앱·단말 무관 횡단 원칙. 충돌 시 본 섹션이 도메인 섹션보다 우선.

### 2.1 작업 승인 게이트

수정·실행 행위는 **사용자 명시 승인 후 진행**. 다음은 승인 없이 즉시 실행 금지:

- 소스 코드 편집 (`src/`, `scripts/`, `tools/`, `*.py`, `*.bat`, `*.yaml`)
- TC 파일 신규/수정 (compiled / stage1 / stage2 / golden)
- 구조 변경 (디렉토리 이동, 파일 rename, 모듈 분리)
- 의존성 변경 (requirements, venv)
- 외부 시스템 호출 (`adb push/install/uninstall`, 단말 reboot, 설정 변경)
- 커밋 / push (글로벌 정책 → §7)

승인 없이 가능 (관찰·검증·정적):
- 파일 read / glob / grep
- `git status --short` · `git diff` · `git log` (read-only)
- `validate_tc.py` 정적 검증
- 비파괴 단말 관찰 (`dumpsys`, `uiautomator dump`, `logcat -d`)

"별도 티켓" 합의된 구조 수정은 **범위 결정(A/B) 먼저 확정**. 임의 통합 금지.

### 2.2 보고 어휘

**PASS 4종 — 단독 `PASS` 표기 영구 금지**:

| 어휘 | 의미 |
|---|---|
| `validate PASS` | `validate_tc.py` 정적 검증 통과 |
| `runtime PASS` | `cli run` 실 단말 step 전부 PASS |
| `manual evidence observed` | adb / 스크린샷 / uiautomator dump 실기 관찰 |
| `BUG-GAP observed` | 실기에서 버그 또는 스펙 갭 |

`validate PASS`는 `runtime PASS`를 의미하지 않는다.

**FAIL 컨텍스트 부착**: `step verify_text FAIL`, `load_tc rejection`, `runtime precondition FAIL` 식.

**모호 어휘 금지**:
- "수정 완료" (편집 없는 확인 작업) → "상태 확인 + 다음 단계"
- "검증 완료" 단독 → PASS 4종 중 하나로 한정
- "잘 됨" / "문제 없음" → 측정값·관찰값 동반
- "거의 다 됨" → 잔여 항목 명시 목록

**Silent 동작**:
- 메모리 저장은 silent (명시 지시 없으면 보고 생략)
- 직전 turn에 이미 있는 표·요약 recap 금지
- 없는 정보는 `—` 한 칸

### 2.3 Source-of-truth Policy

신규 action·schema·catalog 항목 추가는 **정의(스키마/문서) → 코드 → 테스트 정렬**을 **같은 PR 안에서** 맞춘다.

- 스키마·문서·loader·runner·테스트 중 일부만 갱신 = **drift**
- drift 감지 시 동작 변경 시도 전 정렬 PR 우선
- 임시 예외 필요 시 drift risk와 후속 정리 티켓을 보고서에 명시
- 근거 사례: PR 0 `verify_gone` drift

### 2.4 Evidence Accumulation (원칙)

자동화 산출물은 휘발하지 않고 **디스크에 누적**되어야 한다.

- 누적 데이터는 다음 TC 작성·delta 판단의 입력으로 재사용
- 데이터가 남지 않는 자동화는 도입하지 않는다 (단기 속도 개선이 정확성·재현성을 훼손하면 채택 X)
- planned 항목을 implemented 인 척 보고하지 않는다 (planned는 그대로 표기)
- **구체 경로 enumeration은 §5.6 참조** (본 섹션은 원칙만)

### 2.5 Branch Policy

| repo | 역할 |
|---|---|
| **tc-runner** (본 repo) | 학습 루프 · 탐색 · 핀포인트 검증 · 사용자 파트너 작업 |
| **thor2j-tc-appium** (`C:\Users\momen\Projects\thor2j-tc-appium`) | 사내 AI 자동화 pilot baseline · 정형 spec compliance · CI/CD · Jira 정형 자동화 |

새 요청이 정형 자동화·CI/CD 영역이면 분기로 안내. 학습 루프·탐색이면 본 repo. **cross-commit 금지**.

### 2.6 개선 훅
본 섹션 5개 소항목은 운영 frame source. 작동 부정합·예외 누적 발견 시 §8 기록 → batch 개정.

---

## 3. TC Pipeline

TC 작성·수정·실행은 **STAGE 변환 → 게이트 체인** 두 축. 본 섹션은 보편 원칙만, 단말·viewport·SIM 등 **구체 패턴은 `docs/tc_patterns.md`** 분리.

### 3.1 STAGE 변환

| 단계 | 입력 | 출력 | 지시문 |
|---|---|---|---|
| **STAGE 1** | 원본 TC | CTF 정규화 YAML | `tc_prompts/STAGE1_NORMALIZE.md` |
| **STAGE 2** | CTF YAML + 단말·러너 프로파일 | 실행 TC | `tc_prompts/STAGE2_COMPILE.md` |
| **공통** | (양 단계) | — | `tc_prompts/OPERATIONAL_RULES.md` |

- 입력 프로파일: `tc_prompts/device_profile.yaml`, `tc_prompts/runner_capability.yaml`
- 골든 reference: `golden_tc_set/`
- 변환 규칙의 단일 source = 위 4개 파일 (CLAUDE.md는 호출만)

### 3.2 GATE 1~4 체인

```
GATE 1 작성/수정 → GATE 2 validate → GATE 3 PASS 확인 → GATE 4 리포트
```

각 게이트는 이전 게이트 PASS 전제. 중간 FAIL 시 다음 게이트 **진행 금지**.

**GATE 1 — 작성/수정**
- compiled TC metadata에 `execution_type`, `manual_detail` **필수**
- 두 필드는 임의 값 X — step-level 정보에서 **파생 계산** (§3.3)
- 파생 규칙 source = `tc_prompts/STAGE2_COMPILE.md` Step 4

**GATE 2 — validate**
```
venv/Scripts/python.exe validate_tc.py <파일 또는 --dir 디렉토리>
```
- placeholder FAIL(`UNRESOLVED_PARAMS`) 허용
- `execution_type` / `manual_detail` 관련 FAIL 불허

**GATE 3 — PASS 확인**
- FAIL 시 다음 게이트 진행 금지
- 원인 수정 → GATE 2 재실행 → PASS 후 진행

**GATE 4 — 리포트**
```
venv/Scripts/python.exe gen_excel.py
```
- `gen_excel.py`는 `execution_type` / `manual_detail` 누락 시 fail-fast
- 누적 경로는 §5.6

### 3.3 execution_type / manual_detail 파생 원칙
- 사람이 임의 채우는 값 아님 — step 정보에서 결정
- `manual` step이 1개라도 있으면 TC는 manual 표기
- 파생 알고리즘 변경 = STAGE2 + validate + gen_excel 동기 갱신 (§2.3 source-of-truth)

### 3.4 구체 패턴 link
단말 viewport · double-swipe · DebugScreen 진입 · SIM 인증 · PCAT · USB persist 등 앱·단말별 구체 패턴은 **`docs/tc_patterns.md`** 참조. 갱신 빈도 높음 → 분리.

### 3.5 SMOKE TC 연속 진행 규칙
동일 패턴 SMOKE에서 다음 조건 만족 시 validate → runtime **무중단 진행** 허용:
- 같은 단말×앱·같은 SMOKE 시리즈 안
- 직전 case가 runtime PASS
- 본 case가 validate PASS

단, **commit / push는 항상 명시 승인** (§7).

### 3.6 개선 훅
게이트 추가·파생 규칙 변경·SMOKE 무중단 조건 변경 발견 시 §8 기록.

---

## 4. Diagnosis & Repro

본 섹션은 **버그 분석·재현 계획·root cause 확정**의 보편 방법론. 단순 "재현됨/안 됨" 보고는 root cause 결론으로 인정하지 않는다.

### 4.1 가설 분리
실험 시작 전 가설을 **명시 열거** (한 사이클이 두 가설을 동시에 흔들지 않도록 변수 1개씩 고정):

- 단말 가설 (펌웨어 / baseband / layout)
- 호스트 환경 가설 (USB driver, AutoConfig, antivirus 등)
- carrier 가설 (SKT / KT / LGU+ 차이)
- 빌드 가설 (Z0xxxU / Y라인 등)

### 4.2 매트릭스 충분성

| 결론 | 최소 요구 |
|---|---|
| `OBSERVED` | 1회 이상 관찰 + 로그/덤프 증거 |
| `CONFIRMED` | 최소 2 carrier × 2 조건 매트릭스 + 정/역 재현 |
| `SPEC_GAP` | 단말 결함 아님 입증 + 외부 환경/스펙 근거 |

- 단일 carrier·단일 조건 PASS = 일반화 금지
- 정/역 재현 예: WWAN on → trigger / off → no trigger (양방향)

### 4.3 정량 측정
- 발생률 분자/분모 명시 (`20/21 = 95%` 식)
- 결정론 timer는 σ까지 (`130.66s σ=0.13s, n=10`)
- 단순 "발생/미발생" 외에 시간·주기·조건별 비율 측정

### 4.4 진단 결론 어휘

| 어휘 | 의미 |
|---|---|
| `SUSPECT` | 가설 단계 |
| `OBSERVED` | 1회 이상 관찰, root cause 미확정 |
| `CONFIRMED` | 매트릭스 충족 + 정량 측정 + 정/역 재현 |
| `SPEC_GAP` | 단말 결함 아님, 스펙·외부 환경 |

**Axis 관계**:
- 본 어휘는 **§2.2 PASS 4종 중 `BUG-GAP observed`의 세부 진단 분류**
- `validate PASS` / `runtime PASS` / `manual evidence observed`는 본 어휘로 분류하지 않음
- **§6.3 이슈 lifecycle 어휘와 axis 다름** — 본 어휘는 결론, §6.3은 트래킹

### 4.5 Repro 도구 지연 단축 정책
repro 스크립트의 step 간 지연 단축은 **모두 충족 시에만 허용**:

1. self-verify 단계 추가 (의도 상태 도달 확인)
2. fallback 분기 (확인 실패 시 기존 지연 복귀)
3. 실험 모드 flag로 gate (default off)
4. 지연 단축 전후 trigger rate / FAIL rate **정량 비교**

tap 타이밍 = 재현 충실도. 신뢰성 무손실 입증 없는 단축은 거부.

### 4.6 대표 사례 (1줄)
- **BUG-25796 ODIN2 DataPopup race** — 단말 vs 호스트 가설 분리 → 34 사이클·6조건 매트릭스 → WWAN on/off 정/역 재현 → 130.66s σ=0.13s 정량 → root cause = 호스트 Windows WWAN AutoConfig (`CONFIRMED` + `SPEC_GAP`)
- **BTS18697 IMS IP DebugScreen** — LTE PASS / WCDMA layout 자체 누락. WCDMA에서도 IMS PDN·P-CSCF·MMTEL은 별도 명령으로 활성 확인 → 단말 결함 아님 입증 후 layout 추가 요청 (`BUG-GAP observed`)
- **BUG-25175 LGU+ APN MR** — 회귀 매트릭스 17/18 (T-16/17/18 skip), 이전 빌드 18/18과 라인 일치 (`runtime PASS`)

### 4.7 개선 훅
매트릭스 기준·정량 단위·결론 어휘 변경 시 §8 기록. 새 root cause 패턴은 §4.6에 1줄 추가.

---

## 5. Tools & Evidence Paths

### 5.1 코어 스크립트 (repo root)

| 파일 | 역할 | 게이트 |
|---|---|---|
| `validate_tc.py` | TC 정적 검증 | GATE 2 |
| `gen_excel.py` | TC excel 리포트 (fail-fast on metadata 누락) | GATE 4 |
| `gen_yaml_tc_report.py` | yaml→excel 변환 | — |
| `gen_app_tc_report.py` | 앱별 TC 리포트 | — |
| `update_tcs.py` | TC 일괄 갱신 | — |

### 5.2 Runner 모듈 (`src/`)
- 엔트리: `cli.py` (`cli run`)
- 로딩·파싱: `tc_loader.py`, `ui_parser.py`
- 실행: `action_runner.py`, `adb.py`
- 사전 점검: `preflight.py`
- 리포트: `reporter.py`, `excel_converter.py`
- 카탈로그: `catalog.py`, `catalog_delta.py`
- 탐색: `app_explorer.py`

### 5.3 실험·repro 스크립트 (`scripts/`)

| 파일 | 용도 |
|---|---|
| `apn_reboot_loop.py` | APN 증가 모니터링 (BUG-5426) |
| `data_popup_repro_loop.py` | DataPopup race repro (BUG-25796) |
| `qc_ap_log_capture.py` | 재부팅 무손실 AP 로그 (`boot_id` 기반) |
| `setup_preset.py` | 단말 테스트 preset |
| `lgu_consent_diag.py` | LGU+ consent 진단 |
| `setup_gallery_media.py` / `reset_gallery_media.py` / `gen_gallery_photos.py` | Gallery 앱 테스트 미디어 |

### 5.4 운영 도구 (`tools/`)

| 파일 | 용도 |
|---|---|
| `git_safe_push_audit.py` | master push 전 ahead·파일 audit (§7) |
| `synthetic_delta_measure.py` | synthetic delta 측정 (PR 7) |

### 5.5 Bat + 환경 함정

**Bat 도구**:
- `BUG5426_APN_Monitor.bat` / `_py.bat`
- `QC_AP_Log_Capture.bat`
- `BUG_DataPopup_Monitor.bat`
- `doc/apply_apns_conf.bat` / `doc/verify_apns_conf.bat` / `doc/rollback_apns_conf.bat`

**환경 함정 (영구 주의)**:
- `chcp 65001` 이후 한글 표시 desync 가능 — UTF-8 + CP949 fallback 명시
- Git Bash가 Windows 명령(`find`, `sort` 등) shadow → 절대 경로 or `where.exe` 사용
- bat 블록 내 `()` parenthesis는 escape 필요
- bat 파일은 CRLF 유지 (LF 저장 시 일부 환경 실패)
- bash CWD 잔존 — `cd` 후 상대경로 mkdir/Write 금지, **절대경로 우선**

### 5.6 누적 경로 (status)

원칙은 §2.4. 본 항목은 경로 enumeration + status.

**구현됨**:
| 경로 | 용도 |
|---|---|
| `reports/*_report.html` | runtime HTML 리포트 |
| `reports/lint/<run_id>.json` | lint 결과 |
| `reports/preflight/<run_id>/` | preflight 결과 (manual seed 포함) |
| `reports/screenshots/` | runtime 스크린샷 |
| `reports/catalog_delta/` | catalog delta 산출물 |
| `<단말명> - <앱명>/catalog/` | 화면·selector·실패원인 카탈로그 (앱별 진행) |
| `output/` | bat 도구 1회성 산출물 |
| `output/QC_AP log/` | AP 로그 |
| `logs/`, `logs_apn/` | 도구별 누적 로그 |

**Planned (구현 시 본 항목 갱신)**:
| 경로 | 용도 |
|---|---|
| `reports/<run_id>/` | runtime 전체 묶음 구조화 (lint·preflight 외) |

planned 항목을 implemented 인 척 보고하지 않는다 (§2.4).

### 5.7 개선 훅
신규 도구·기존 경로 status 변경·환경 함정 신규 발견 시 §8 기록.

---

## 6. 단말×앱 폴더·문서 컨벤션

### 6.1 폴더 규칙
- **위치**: tc-runner 루트 (`exported_tc1/` 하위 아님)
- **이름**: `<단말명> - <앱명>/` (예: `ODIN2 - My gallary/`, `THOR2 - LGU APN BUG25175/`)
- **단말명**: 사용자 호칭 그대로 (스타일폴더 2 = `AT-M140`, "Galaxy Folder 2"로 부르지 말 것 — 사용자 명시 호칭 유지)

### 6.2 기본 파일

| 파일 | 내용 |
|---|---|
| `BUG_LOG.md` | 이슈 누적 |
| `MENU_TREE.md` | 메뉴·화면 구조 |
| `RESUME.md` | 세션 재개용 상태 |

### 6.3 이슈 lifecycle 어휘

**§4.4 진단 결론 어휘와 axis 다름** — 본 어휘는 트래킹.

| 어휘 | 의미 |
|---|---|
| `OPEN` | 등록됨, 미진행 |
| `IN_PROGRESS` | 진행 중 (재현·분석·수정) |
| `RESOLVED` | 수정 적용 |
| `WONTFIX` | 수정 안 함 결정 |
| `NOTE` | 정보 기록 (이슈 아님) |

**BUG_LOG.md 필드 분리**:
- `진단 상태` (§4.4 어휘): SUSPECT / OBSERVED / CONFIRMED / SPEC_GAP
- `이슈 상태` (본 어휘): OPEN / IN_PROGRESS / RESOLVED / WONTFIX / NOTE

현행 단일 SUSPECT~WONTFIX 어휘 사용은 **deprecated** (혼용 금지).

### 6.4 BUG_LOG.md 구조

**요약표 열**: ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거

**항목 필드**: 기능 영역 / 진단 상태 / 이슈 상태 / 단말 / 앱 / 요약 / 기대 결과 / 실제 결과 / 재현 절차 / 증거 / 관련 TC / 정정 이력

**원칙**:
- 본문 = **현재 상태만**
- 과거 변경 = `정정 이력` 한 줄
- Regression PASS는 본문에 섞지 말고 하단 `## 세션 결과`로 분리
- 추가보다 **삭제 우선**
- 취소선·장문 주석·중복 서술 금지
- 없는 정보 = `—`
- 단순 포맷 통일은 정정 이력 기록 X

### 6.5 세션 결과 블록
`실행일 / 단말 / 앱 / 범위 / PASS / 신규 발견 / 변경·정정 / 다음 확인 항목`

### 6.6 개선 훅
폴더 명명·필드 추가·어휘 추가 시 §8 기록.

---

## 7. Git / Commit Policy

### 7.1 글로벌 정책 reference
본 repo의 commit / push 기본 규칙은 **글로벌 정책에 종속**.

**Source**: `~/.claude/CLAUDE.md` Global Commit Policy (2026-05-08 lock)

핵심 (요지만 — 상세는 source 참조):
- 작업 중 commit / push 금지
- 하루 1회 batch commit (또는 다음날 시작 전 정리)
- 사용자 명시 "commit now" 또는 5 예외 발동 시만 즉시 commit
- broad add 영구 금지 (`git add .` / `-A` / 디렉토리 broad 모두)
- 명시 path stage만 허용

### 7.2 본 repo 특화

**Master push 가드**:
- master push 전 **ahead · 파일 audit 필수**
- fast-forward만 허용
- force / force-with-lease 금지
- 도구: `tools/git_safe_push_audit.py`

**SMOKE TC runtime 연속 진행** (§3.5 reference):
- validate → runtime 무중단 진행 허용
- 그러나 **commit / push는 항상 명시 승인** (§7.1)

### 7.3 위반 시 처리
(글로벌 정책 source 동일)
1. 즉시 중단 — 추가 commit / push 금지
2. 발생 commit / staging / push 사용자 보고
3. 롤백·정정은 사용자 결정 영역 (자체 `git reset` / `revert` 금지)

### 7.4 개선 훅
본 repo 특화 규칙 추가·도구 변경 시 §8 기록. 글로벌 정책 자체 개정은 source 영역.

---

## 8. Continuous Improvement

본 섹션은 **본 CLAUDE.md 자체의 개정 절차**. 각 섹션 끝 "개선 훅"이 여기를 가리킨다.

### 8.1 개정 trigger

다음 발생 시 §8.2에 1줄 기록:
- 원칙 부정합·예외 누적 발견
- 새 도구·경로·어휘 도입
- 사례에서 도출된 새 패턴 (BUG-NNNNN 등)
- 기존 정책의 실패·우회 시도

### 8.2 누적 교훈 목록

| 날짜 | 영역 | 근거 사례 | 반영 섹션 | 상태 |
|---|---|---|---|---|
| 2026-05-21 | §1~§8 신설 | 보강 후보 10건 통합 | 전 섹션 | applied |
| 2026-05-21 | 분량 가드 | 1차 작성 결과 447 lines · spec 가드 250~350 lines 대비 초과 | §8.4 archive 정책 가동 검토 | applied |
| 2026-05-22 | §2.3/§7.2 drift | push-audit가 catalog(append-only 누적상태)를 generated류 재생성물로 오분류 → staging FAIL ↔ §2.4/§5.6 핵심가치 충돌. catalog 재분류(audit FORBIDDEN 제거 + PR6C drift baseline test 동기) + Music/gallery catalog track (commit `0b817db`) | tools/git_safe_push_audit.py · test baseline (CLAUDE.md 본문 무변경 — §5.6 이미 정합) | applied |

**상태 어휘**: `proposed` / `applied` / `rejected` / `superseded`

### 8.3 개정 절차
1. trigger 발생 → §8.2에 `proposed` 기록 (드래프트만)
2. 사용자 검토·승인
3. 본문 섹션 갱신 + §8.2 상태 `applied`
4. batch commit (§7)

자체 판단 본문 직접 갱신 금지 — **사용자 승인 게이트 필수** (§2.1).

### 8.4 archive 정책

§8.2 row 수가 50을 초과하면 archive 발동 후보. 자동 수행 없음 — Claude는 도달 사실만 보고하고, 사용자 명시 승인 후 발동 (§2.1·§8.3 정합).

**archive 대상**:
- 가장 오래된 completed row (`applied` / `rejected` / `superseded`) 25개
- 동일 날짜 multi-row 시 §8.2 본문 등장 순서 유지 (stable order)
- `proposed` row는 archive 안 함 (본문 잔류)

**예외 — completed row < 25**:
- 자동 partial archive 금지
- Claude는 예외 보고: 사용자가 (a) wait / (b) partial / (c) skip 결정
- partial 승인 시: M rows (M < 25) 이동, event row = `YYYY-MM-DD | archive (partial) | oldest M completed rows moved (partial exception) | §8.4 | applied`

**archive 파일**: `docs/claudemd_section8_archive.md` (단일 누적, 시간 순 append-only, schema는 §8.2와 동일)

**archive 후 §8.2**:
- 해당 25 rows 본문 제거
- archive event 자체를 §8.2의 새 row로 1줄 추가 (`날짜 | archive | oldest 25 rows moved | §8.4 | applied`)
- 별도 안내문·counter 없음

**§2.1·§8.3 정합**: archive는 본문 갱신이므로 사용자 승인 게이트 필수. 자체 판단 archive 금지.

### 8.5 개선 훅 (메타)
본 §8 절차 자체가 무력화·우회 시도 발견 시 사용자에게 직접 보고.
