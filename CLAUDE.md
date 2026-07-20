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

**Scope 분리 어휘**:

| 어휘 | 의미 |
|---|---|
| `NOTE` | 본 검증 scope 밖 관찰 (carrier 정책 / 외부 환경 / hardware 한계 / 별도 BUG). PASS/FAIL 판정 영향 없음. |

FAIL과 NOTE 분리 — 외부 정책·환경 요인은 NOTE 처리하고 본 BUG 판정과 격리. 적용 원칙 상세: `feedback_scope_note_and_pass_blockers.md`.

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
- Engineer-Mode override의 Way3 반영은 **항목 × carrier × 적용 시점**별로 다르다. 검증된 applicability 매트릭스를 누적·재사용하고, 동일 조합을 재시험마다 처음부터 재판별하지 않는다 (`ODIN2 - Engineer IMS/RUNTIME_PLAYBOOK.md`).

**3-way ground truth 정합 원칙**:
단말 표시값 검증은 **단말 UI / 시스템 dump / 인터페이스 상태** 3 출처 동시 일치를 `runtime PASS` 요건으로 한다. 단일 출처는 layout 누락·stale 표시 등 위양성 가능. 적용 패턴 상세: `feedback_diagnostic_3way_ground_truth.md`.

**핵심 axes vs 보강 axes 분리**:
multi-phase 검증 TC는 **핵심 axes 충족 시 `runtime PASS`**, 보강 axes 미수집은 명시하되 PASS blocker 아님. 보조 분석 자료(예: QXDM hdf)도 PASS 근거 아님 / 후속 분석용 보존. 적용 패턴 상세: `feedback_scope_note_and_pass_blockers.md`.

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
- **BTS18697 IMS IP DebugScreen (2차)** — WCDMA layout 보강 빌드. DebugScreen / dumpsys connectivity / ip -o addr 3-way 일치, RAT 전환 시 IMS IP 새로 할당. KT 미인증 USIM IMS 미할당은 carrier 정책 `NOTE` (단말 fix scope 밖). `BUG-GAP observed` → `runtime PASS` 전환 (2026-05-28)
- **BUG-25175 LGU+ APN MR** — 회귀 매트릭스 17/18 (T-16/17/18 skip), 이전 빌드 18/18과 라인 일치 (`runtime PASS`)
- **ODIN2 Engineer IMS SIP 검증** — AP logcat reg-state·callProfile(`audioCodecAttribute=null`)은 IMS 등록/코덱 비권위. ground truth = 모뎀 `.qmdl` SIP(`0x156E`) REGISTER↔resp Call-ID 매칭. TC1 bare Domain `sktelecom2`→req-URI `sip:sktelecom2`→`404`×3 등록실패 관찰. 복합시험=필드격리 아닌 기능 시나리오 (`BUG-GAP observed`)

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
| `altbasic_tcid_collision_check.py` | tc_id cross-batch 충돌 + sheet 내 dup 감사 (합성 prep 선행 게이트, P-1) |
| `ledger_recompute.py` | 판정 CSV 단일 원장 재집계 (수기 집계 드리프트 방지·judge_method auto/human 분리, P-3) |
| `manifest_result_reconcile.py` | manifest×구현×결과 tc_id 조인 reconcile (커버리지 갭 가시화·4종 불일치, P-4) |
| `qcat_fast_extract.ps1` (PowerShell) | 대용량 qmdl QCAT 파싱 단축 (filter-first + ISF 캐시 ~740× + 단일 포그라운드 COM). 상세 `docs/qcat_parsing.md` |
| `ims_sip_digest.py` | QCAT 0x156E IMS SIP 텍스트 → override 검증용 KB digest (KST 타임스탬프) |
| `eng_mode_runner.py` + `eng_mode_profiles.py` | 동일한 gate→tab→flat-list UI 구조의 Engineer-Mode 앱 런너 (preflight wrong-device 가드·caseset 앱-1회 batch·capture 상태-게이트·adb 0 `plan`; selector/라벨/좌표 프로파일 외부화). host-TDD/dry-run 완료, 범용 경로 device smoke pending |

### 5.4 운영 도구 (`tools/`)

| 파일 | 용도 |
|---|---|
| `git_safe_push_audit.py` | master push 전 ahead·파일 audit (§7) |
| `synthetic_delta_measure.py` | synthetic delta 측정 (PR 7) |
| `untracked_contamination_scan.py` | 워크플로 agent untracked 오염(phantom) 스캔 (§5.7, P-2) |

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
| `reports/<run_id>/{report.html, screenshots/, summary.json}` | runtime bundle (lint·preflight 외 HTML / 스크린샷 / machine-readable 요약). `cli run` 1회 = 1 run_id = 1 bundle. run_id 포맷 `YYYYMMDDTHHMMSSZ` UTC (`preflight._now_run_id` 재사용), `--run-id` override 가능 |
| `reports/*_report.html` | runtime HTML 리포트 (legacy — Reporter 미주입 run_id 호출 시) |
| `reports/screenshots/` | runtime 스크린샷 (legacy flat) |
| `reports/lint/<run_id>.json` | lint 결과 |
| `reports/preflight/<run_id>/` | preflight 결과 (manual seed 포함) |
| `reports/catalog_delta/` | catalog delta 산출물 |
| `<단말명> - <앱명>/catalog/` | 화면·selector·실패원인 카탈로그 (앱별 진행) |
| `output/` | bat 도구 1회성 산출물 |
| `output/QC_AP log/` | AP 로그 |
| `logs/`, `logs_apn/` | 도구별 누적 로그 |

**Planned (구현 시 본 항목 갱신)**: (현재 없음)

planned 항목을 implemented 인 척 보고하지 않는다 (§2.4).

**runtime bundle 구현 메모 (2026-05-26)**:
구현 파일 = `src/reporter.py` (`Reporter(run_id=...)` + `bundle_dir` / `screenshot_dir` property + `write_summary_json`), `src/cli.py` (`cli run --run-id` override, `cmd_run` 에서 run_id 주입), `tests/test_reporter.py`, `tests/test_cli.py`. `summary.json` 스키마 = `schema_version=1` / `tool_version="runtime-report-v1"` / `device` / `summary` / `results[].steps[]` (필드: `index, action, passed, duration_s, message, execution_mode, manual_action, skip_reason, paused, screenshot_path` — bundle 상대경로). pytest reporter/cli 16 passed. 단말 runtime smoke 미수행 (다음 단말 작업 사이클에서 실 cli run 으로 sanity 예정).

### 5.7 Workflow·합성 agent 운영 규칙

합성·이해 워크플로에 dispatch 하는 agent는 **read-only / return-only**.
근거 = §8.2 2026-06-16 (batch11 합성 중 agent가 구조화 반환 대신 yaml 4개를
batch10 dir 직접 기록 = phantom side-effect + 슬라이스 over-read 53/29). taxonomy C7.

- **파일 side-effect 금지**: agent 산출물은 **구조화 반환**으로만 전달. 디스크
  쓰기(yaml/json/dump 생성·수정) 금지 — 오케스트레이터가 반환값을 받아 기록한다.
- **슬라이스 경계 준수**: 요청 범위 밖 over-read 금지. 반환 항목 수 = 요청 항목 수
  검증(29 요청 → 29 반환, 53 반환은 오염 신호).
- **실행 후 오염 스캔 필수**: 워크플로 종료 후 보호 디렉토리에 예상 외 untracked
  파일이 생겼는지 `tools/untracked_contamination_scan.py`로 스캔. phantom 발견 시
  git 추적 여부로 확정(untracked·해당 커밋 미포함) → 격리/삭제·정정 후 진행.
- phantom은 git 미추적이라 **커밋 audit(§7.2)로 잡히지 않음** → 별도 스캔이 안전망.

### 5.8 개선 훅
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
| `RESULT_YYYY-MM-DD.md` | 검증 결과 보고서. 재검증 시 신규 RESULT 추가 (날짜 시리즈), 정정 이력으로 cross-link. 절차 상세: `reference_result_series_revalidation_cycle.md` |

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
- 다회 검증 사이클(1차 BUG-GAP → 개발자 fix → 2차 runtime PASS 등)은 RESULT 시리즈로 운영 — 본문 갱신 X / 신규 RESULT 추가 + 정정 이력 cross-link

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
| 2026-05-28 | diagnostic verification | BTS18697 2차 검증에서 DebugScreen/dumpsys/ip 3-way 정합, scope NOTE, RESULT 시리즈 운영을 일반 패턴으로 승격 | §2.2/§4/§6 + memory | applied |
| 2026-06-01 | diagnostic / QXDM | BUG-25796 추가검증: QXDM offline diag workflow(reference memory 신규) + REF negative-control(단말특이성) + 모뎀분석은 실패 discriminator + 정상경로 병행 판정 + 대용량 파생로그 digest-only | §4/§2.4 후보 (2차 사례 시 본문 승격) | proposed |
| 2026-06-12 | §2.5 통합 | tc-runner×thor2j-tc-appium 통합 qa-suite 확정: staging(`qa-suite/` — Track A/B-1 fail-closed 러너 selftest 111) + 설계 v2(형제 repo `C:\Users\momen\Projects\qa-suite`, learning/synthesis/contracts/campaigns 책임 구조, provenance manifest, bugs 유일입력 bug-repro 한정). 이주 개시 시 §2.5 cross-commit 분기 정책 supersede 필요 | §2.5 (supersede 예정) · qa-suite/ARCHITECTURE.md v2 | proposed |
| 2026-06-16 | workflow agent 안전 | ALT batch11 합성 중 워크플로 agent가 구조화 반환 대신 yaml 4개를 batch10 dir 직접 기록(file side-effect) + 슬라이스 over-read(53/29 반환). git 추적 검증으로 phantom(untracked·`fc56cf8` 미포함) 확정·삭제·정정. → 합성 agent read-only/return-only 제약 + 실행 후 untracked 오염 스캔 필요 | §5.7·§5.4 (workflow 운영규칙+오염 스캔 도구) | applied |
| 2026-06-16 | tc_id 무결성 | tc_id `ALTBASIC_<PREFIX>_<excel_row3>` 비단사 + Excel 4 sheet(Safety/Launcher/Call/Camera) 중복 TC ID 83건 = **잠재(latent) 구조 위험**(실발현 0). batch11 실충돌 4건(CALC_027/028·SST_010/011)의 실제 원인 = 워크플로 phantom side-effect(위 row — batch11분을 batch10 dir 오기록)이지 Excel dup 아님(근거 3중: 충돌 row_key가 KEEP_CONFIRMED 271에 부재·충돌 sheet가 dup 4 sheet 미포함·phantom 삭제 후 gate 충돌 0). gate 포착·최종 실충돌 0/29. 도구화 `scratch/altbasic_tcid_collision_check.py`(cross-batch + Excel dup 감사, prep 선행 게이트). 정정 근거: FAILURE_TAXONOMY_2026-07-03 C7 FM1 | §5.3 (collision_check 도구 등록)·§8.2 인과정정(31a1d64) | applied |
| 2026-06-16 | diagnostic / IMS 검증 | ODIN2 Engineer IMS 복합 기능 TC 검증: AP logcat reg-state·callProfile(`audioCodecAttribute=null`)은 IMS 등록/코덱 **비권위** — 모뎀 `.qmdl` SIP(log `0x156E`) REGISTER↔resp **Call-ID 매칭**이 ground truth. TC1 임의값(bare Domain `sktelecom2`→req-URI `sip:sktelecom2`)→`404`×3 등록실패 관찰(누락 신호 0). + "복합 시험" = 필드격리 아닌 기능 시나리오(임의값 동시→실호/재등록→신호 반영) | §4.6 대표 사례 + memory([[reference_ims_sip_qcat_verification]]·[[feedback_combined_test_functional_scenario]]) | applied |
| 2026-06-17 | 단말 런타임 효율·정확도 | Engineer IMS 8케이스 실기가 과다 소요 — 항목별 앱 cold 재기동·불필요 reboot(둘이 최대급 손실; reboot는 호 파라미터 환원까지)·조기 qmdl pull·단말정체 미확인(self-call·USIM 교체)·Way1·2≠Way3 매번 재판별. 도구화(런너 caseset/preflight+wrong-device 가드/capture 상태-게이트) + 카탈로그 RUNTIME_PLAYBOOK Override Applicability Matrix + feedback 메모리 | §5.3 (`eng_mode_runner.py`+profile, host-TDD/dry-run) + §4.2(applicability 재사용) + `RUNTIME_PLAYBOOK.md`; 범용 경로 device smoke pending | applied |
| 2026-06-17 | QCAT 파싱 단축 도구 | 대용량 qmdl(155M/131만p) QCAT 파싱 병목 = OpenLog 전수 인덱싱(~148s, 86%가 불요 0x1FEB debug). 단축법 정립·실측: filter-first(SaveAsText 전 SetAll(false)+Set+Commit, 564MB→KB) + ISF 캐시(SaveAsISF 1회→재오픈 0.2s, ~740×, 무손실) + 단일 포그라운드 세션(0x80080005 진짜 원인=QCAT 첫기동 DirectPlay 모달 launch 블록, 백그라운드 금지). `scripts/qcat_fast_extract.ps1` 승격 + BTS15068·40M 양 캡처 검증. 0xB193=RSRP/RSRQ per-antenna ground truth | §5.3 (qcat_fast_extract.ps1·ims_sip_digest.py)·docs/qcat_parsing.md·memory([[reference_qcat_fast_extraction]]·[[project_bts15068_antbar]]) | applied |
| 2026-07-02 | TalkBack×하드키 검증 방법론 | THOR2_J×LINE 이슈 2건 규명(SPEC_GAP)에서 앱 무관 방법론 정립: 포커스 2축(입력≠a11y, non-speaking 컨테이너 무피드백 구간)·FocusFinder shadowing(전폭 컨테이너가 자식 가림·ViewPager 수평키 소비)·adb 함정 3종(uiautomator dump=TalkBack 일시 억제→키 시퀀스 중 dump 금지 / input tap·swipe=터치탐색 우회 즉시클릭→탐색 발화는 keyevent로 대체 / MSYS·PS5.1 깨짐)·발화 정량(TTS Synthesis+오디오포커스 세션+대조군 2종)·레이어 분리 절차·단말측 3rd-party a11y 수정 경로 부재(트리=앱 소유·RRO 무력·TalkBack=Google/Play·bare D-PAD 키맵 없음, 리서치 확정). 정적 스크리닝 S1~S8 도구화는 승인 대기 | docs/talkback_dpad_verification.md(신설 완료)·memory([[reference_talkback_hardkey_verification]]·[[project_thor2j_line_talkback]]) 반영, §4/§5 본문 등록은 갱신 대기 | proposed |

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
