# MIGRATION.md — 기존 자산 이주 체크리스트 (v2, 형제 repo 확정)

목표: tc-runner / thor2j-tc-appium 의 기존 자산을 **형제 repo
`C:\Users\momen\Projects\qa-suite`** 골격(ARCHITECTURE.md §2)으로 단계 이주.
빅뱅 금지 — "신규는 새 위치, 기존은 손댈 때 이주". 현 `tc-runner/qa-suite/` 는
staging 이며 이주 대상이 아니라 **이주 도구·규약의 검증장**이다.

## 1. 분류 기준 (1초 판정)

- 고치는 이유가 "무엇을 검증할지" → analysis/
- 누적·재탐색에 쓰는 데이터·코드 → learning/ (코드=engine, 데이터=catalogs)
- TC 변환·정적검증·산출 → synthesis/
- 고치는 이유가 "어떻게 실행할지" → automation/ (bug-repro | tc-step | appium)
- 단말×앱 검증 운영 문서(BUG_LOG/RESUME/RESULT)·캠페인 계약 → campaigns/
- 사람에게 설명하는 문서 → docs/
- 모르겠음/구버전 → archive/ (삭제 금지)

## 2. 상태 코드

- `[ ]` 미처리   `[I]` 인벤토리 완료(목적지 확정)   `[M]` 이주 완료   `[A]` archive 행
- provenance status 와의 대응 (닫힌 매핑):
  `[ ]`=—, `[I]`=`planned`/`copied`, `[M]`=`verified`/`source-deprecated`, `[A]`=`archived`.
  **`[M]` 은 verified 이후에만** — copied 상태(복사됐으나 동작 미확인)는 [I] 에 머문다.

## 3. Provenance manifest (이주 행 필수 필드)

이주(`[M]`)되는 모든 행은 `campaigns/manifests/provenance.csv` (형제 repo 생성 시
초기화)에 아래 필드를 기록한다. subtree/submodule 미사용 — 이 manifest 가 출처 추적의
단일 수단이다.

| 필드 | 정의 |
|---|---|
| source_repo | tc-runner \| thor2j-tc-appium |
| source_commit | 복사 시점 원본 repo HEAD (full hash) |
| source_path | 원본 상대경로 |
| target_path | qa-suite 상대경로 |
| source_sha256 | 원본 파일 sha256 |
| target_sha256 | 이주본 sha256 (무변환이면 source 와 동일해야 함) |
| transform_note | 무변환 = `verbatim`. 변환 시 내용 명시 (예: `rename tests→modules`, `redaction`, `encoding LF`) |
| status | `planned` / `copied` / `verified` / `source-deprecated` / `archived` (닫힌 집합) |

## 4. 인벤토리

> 스캔: 2026-06-15 (read-only). source HEAD — tc-runner `1bca559`, thor2j-tc-appium `122b275`.
> 폴더 동질 시 폴더 단위 1행, 이질 시 분할 표기. 상태 `[I]`=목적지 확정,
> `[ ]`=불명/분할필요, `[A]`=archive, `[—]`=이주 제외(var·repo meta).
> `var/` 류(reports/logs/output/evidence/raw/keymap)는 이주 대상 아님 — 형제 repo 에서
> 새로 생성, 기존 산출물은 원본 잔류 (규칙 7).

### tc-runner (`C:\Users\momen\Projects\tc-runner`)

| 상태 | 원경로 | 유형 | 목적지 | 비고 |
|---|---|---|---|---|
| [I] | src/ | 코드 | automation/tc-step + learning/engine | 혼합: cli·action_runner·tc_loader·ui_parser·adb·preflight·reporter·excel_converter→tc-step / app_explorer·catalog·catalog_delta·menu_anchor→learning/engine. 하드코딩경로 0 |
| [I] | tests/ | 시험 | automation/tc-step (modules/) | tc-step·menu_anchor 테스트 혼재. 이주 시 `tests`→`modules` 개명(규칙6) |
| [I] | scripts/ | 코드 | automation/bug-repro | apn_reboot_loop·data_popup_repro_loop·qc_ap_log_capture·lgu_consent_diag·setup_* repro·셋업 |
| [I] | tools/synthetic_delta_measure.py | 코드 | learning/engine | XML delta 측정 — catalog_delta 계열 (결정 외 — 확신 분류) |
| [I] planned-port | tools/git_safe_push_audit.py (+tests) | 코드 | tools/ | 결정2. 비이주X — 공통 엔진(git query·ahead/behind·staged) + 테스트 보존, FORBIDDEN_* 정책 3상수만 qa-suite 기준 교체(→contracts/repo-policy/). 원본은 신도구 검증 전 유지 |
| [I] | validate_tc.py | 코드 | synthesis/validators | GATE2 정적검증 |
| [I] | gen_excel.py · gen_yaml_tc_report.py · gen_app_tc_report.py · update_tcs.py | 코드 | synthesis/export | 리포트·TC 산출 (gen_excel fail-fast on metadata) |
| [I] | gen_seniorshield_ppt.py · gen_tc_runner_intro_ppt.py | 코드 | docs/internal | PPT 생성기 |
| [A] | _probe_smoke06_*.py (4) | 코드 | archive | 1회성 probe 잔재 (Music SMOKE06) |
| [I] | tc_prompts/ | 지시문 | synthesis/stage1+stage2 | STAGE1/2 지시문·OPERATIONAL_RULES·device_profile·runner_capability |
| [I] | golden_tc_set/ | TC | synthesis/golden | 골든 reference |
| [I] | stage1_output/ | 산출 | synthesis/stage1 | |
| [I] | stage2_output/ | 산출 | synthesis/stage2 | |
| [I] | exported_tc1/ · exported_ss_call/ · tc1_converted/ | TC | synthesis/export | 실행 TC 세트 |
| [I] 파일별 | tc_samples/ | 혼합 | 파일별 분리 | 결정3: TC_1.xlsx(28참조 활성)·ODIN 메뉴트리.xlsx→analysis/sources / folder_basic_nav·kids_basic_nav.yaml→_inbox(provenance·실기근거 검토 후 synthesis/examples 또는 archive) / sample_wifi·simple_smoke.yaml→archive 후보(schema FAIL) / ★sample_call_test.yaml 평문 전화번호(01012345678) — sanitize 전 tracked 이주 금지 |
| [I] | templates/report.html | 템플릿 | automation/tc-step | reporter HTML 템플릿 |
| [I] | tc_step_schema.json | 입력 계약 | contracts/tc-step/ | 결정1: validate_tc(synthesis)+test_tc_loader/test_lint_schema(automation 경계) 공통 소비 스키마. 이주 시 validate_tc.py:20 SCHEMA_PATH + 2 테스트 경로 갱신 |
| [—] | outputs/ (menu_tree_settings_*) | 산출 | var/ (이주제외) | 동일일자 다중 타임스탬프 = 반복 실행 재생성물 |
| [I] | ODIN2 - My gallary/ · ODIN2 - Music/ · ODIN2 - minifile/ · ODIN2 - Settings/ · ODIN2 - DebugScreen BUG18453/ · ODIN2 - DebugScreen BTS18697/ · ODIN2 - LTE DebugScreen BTS18596/ · ODIN2 - WCDMA Reject BTS17126/ · THOR2 - LGU APN BUG25175/ · THOR2_J - Settings/ | 운영문서+카탈로그 | campaigns/<단말-앱>/ (catalog/→learning/catalogs) | 규칙5 분리매핑. BUG_LOG·MENU_TREE·RESUME·RESULT 한 폴더 유지 |
| [I] 활성 | THOR2_K - Settings/ | 운영문서+카탈로그 | campaigns/<>+learning/catalogs | 활성(mtime-14). 캠페인 종료 시 이동(규칙1). seed yaml→learning/engine 입력 |
| [I] 활성 | THOR2 - ALT Basic TC Audit/ | 혼합(캠페인) | campaigns/manifests + analysis/tc-catalog + synthesis/stage1 + learning/catalogs | 진행중. handoff_device_validation→manifests / *_REJUDGE·overlap·anchor_gap CSV→tc-catalog / stage1_*→synthesis/stage1 / catalog/→catalogs. ★thor2j 러너가 본 폴더 manifest 참조 → 통째 이동(규칙1) |
| [I] | docs/ | 문서 | docs/ | superpowers plans/specs·tc_patterns·feedback 메모 포함 |
| [I] 파일별 | doc/ (589) | 혼합·대용량 | 파일군별 분리 | PDF/xlsx→analysis/sources / BUGxxxx 분석 MD→analysis/bugs / 가이드 MD→docs/guides / pptx→docs/internal / apns bat→automation/bug-repro / 로그 서브폴더(01·BUG25796·debuglogger·BUG21838 image·devices_log·VoiceRec·case2·issue·logs_apn)→var(이주제외) / _tmp_·새 폴더·apk·zip→archive. 물리 분할은 이주 단계 |
| [I] | HANDOFF_*.md (6, 루트) | 문서 | docs/internal | 세션 핸드오프 |
| [I] | BUG5426_APN_Monitor.bat · QC_AP_Log_Capture.bat · BUG_DataPopup_Monitor.bat (+ _py) | 도구 | automation/bug-repro | repro bat (CRLF 유지) |
| [—] | reports/ · logs/ · logs_apn/ · output/ | 산출 | var/ (이주제외) | run 번들·로그. 원본 잔류 |
| [—] | test/ (~305M) | 증거 | var/ 또는 archive (이주제외) | BUG-23025 자산 (메모리 참조) |
| [—] | 루트 *.xml (ui_*·probe_dump_*·popup_a·_bts18596_dump*) | UI덤프 | var/ (이주제외) | 1회성 dump |
| [A] | 새 폴더 (2)/ (ls_log) · scratch/ | 잔재 | archive | 정체불명 로그캡처·scratch (삭제금지 격리) |
| [A] | ● 실기 검증 스크립트와 드리프트 감사…txt (루트) | 문서 | archive | BUG-23025 세션 작업계획 메모 (stale) |
| [—] | CLAUDE.md · .gitignore · requirements.txt · conftest.py | repo meta | (이주제외) | 거버넌스·환경 (repo별 유지) |

### thor2j-tc-appium (`C:\Users\momen\Projects\thor2j-tc-appium`)

| 상태 | 원경로 | 유형 | 목적지 | 비고 |
|---|---|---|---|---|
| [I] 활성 | runner/ | 코드 | automation/appium | appium_runner·session·smoke_executor·safe_fixture*·fail_parser·focus_snapshot·result_writer·excel_tc_loader. ★altbasic_validation_batch1~5 가 tc-runner manifest(CSV) read-only 참조 → 규칙1 |
| [I] 활성 | tests/ | 시험 | automation/appium | test_appium_*·anchor_*·figma_pipeline·mmi_pipeline·observe·fixtures. tc-step tests/ 와 이름충돌 주의(규칙6) |
| [I] 활성 | tools/ | 코드 | automation/appium + docs/internal | 혼합: probe_*·anchor_fact_sweep·tc100_*·build_fullauto_batches→appium / build_*_deck·build_overview_ppt→docs(ppt). ★build_overview_ppt·build_weekly_ai_deck_v2 하드코딩경로 |
| [I] 활성 | docs/ | 문서 | docs/ | research·superpowers·lessons_learned·tc_source_quality_gate 포함 |
| [I] | references/ | 원천 | analysis/sources | HARDKEY_MAP·MENU_TREE snapshot·source_manifest.yaml |
| [I] 파일별 | file/ (25) | 혼합 | 파일군별 분리 | MiveFiles·ALT Basic xlsx→analysis/sources / ALT_QA_Studio.exe→archive / *.skill→docs / exports·scratch xlsx·tcq002_findings.json·VoiceRec→var 또는 archive. 물리 분할은 이주 단계 |
| [I] | testcases/focusrule/ | TC데이터 | analysis/tc-catalog | focusrule_tc_catalog.yaml |
| [I] | specs/tc_standard_format.md | 입력 계약 | contracts/appium/ | 결정1: FocusRule 트랙 TC 포맷 계약(prose). tc-step 스키마와 트랙별 분리 |
| [I] | jira/README.md | 문서 | docs (또는 _inbox) | |
| [I] | generated_tc/ | TC | synthesis/export | FocusRule TC xlsx |
| [I] | THOR2J_*.pptx (4, 루트) | 문서 | docs/internal | 사내 deck (§8.2 deck 기준 사례) |
| [I] | mmi_pipeline/cli/test_audit.py 외 | 시험 | automation/appium | ★하드코딩경로 (tests/ 행에 포함, 별도 표기) |
| [—] | reports/ (4232) · evidence/ (838) | 산출/증거 | var/ (이주제외) | run·raw evidence. 원본 잔류 |
| [—] | README.md · pyproject.toml · .env.example · .gitignore · CLAUDE.md | repo meta | (이주제외) | repo별 유지 |

### 4.1 요약 (2026-06-15 스캔 · 결정 반영)

- **행 수**: tc-runner 29행 · thor2j 14행 (tc-runner tools/ 분할로 +1).
- **상태**: 불명 `[ ]` **0건** — 결정 1/2/3으로 전부 해소. 잔여는 "파일별 물리 분할 실행"(doc·file·tc_samples)·"_inbox 검토"(folder/kids yaml)로 **목적지는 확정**, 이주 단계 작업.
- **목적지 분포(대략)**: synthesis 7 · automation 6 · campaigns 3그룹 · analysis 4 · learning 4 · docs 4 · contracts 2(tc-step·appium) · tools 1 · archive 3 · var(이주제외) 7 · 파일별분리 3.
- **활성 자산(이주 보류 — 캠페인 단위)**: tc-runner `THOR2 - ALT Basic TC Audit/`·`THOR2_K - Settings/` / thor2j `runner/`·`tests/`·`tools/`·`docs/`. ALT Basic 캠페인 양 repo 결합 → 함께 이동.
- **이주 시 참조 수정 필요**:
  - thor2j 하드코딩 절대경로: `tools/build_overview_ppt.py` · `tools/build_weekly_ai_deck_v2.py` · `tests/mmi_pipeline/cli/test_audit.py`
  - 크로스 repo: thor2j `runner/altbasic_validation_batch1~5.py` → tc-runner ALT Basic manifest CSV (read-only). 캠페인 통째 이동 시 갱신.
  - `tc_step_schema.json` 이주 시: `validate_tc.py:20` SCHEMA_PATH + `tests/test_tc_loader.py`·`tests/test_lint_schema.py` 경로 갱신.
  - tc-runner 코드(src/scripts) 하드코딩 절대경로 0.

### 4.2 잔여 확인 (이주 단계 작업 — 목적지는 확정)

1. `folder_basic_nav.yaml`·`kids_basic_nav.yaml` — schema PASS이나 untracked·FULL_AUTO/runnable=true 실기 근거 불명. `_inbox/` 검토 후 synthesis/examples 또는 archive 확정.
2. ★`sample_call_test.yaml` — 평문 전화번호(`01012345678`). sanitize(redaction) 전 **tracked 이주 금지** — 원본 repo 잔류 또는 PII 제거 후 archive (규칙 7 redaction lock 정합).
3. `doc/`(589)·thor2j `file/`(25)·`tc_samples/` — 목적지 확정, 파일군별 **물리 분할은 이주 단계** 실행.
4. contracts/ 정의 확장(입력 계약 포함)·`tools/` 신규 최상위 — ARCHITECTURE.md §2 반영(본 라운드). tc-runner 본문 §8.2 동기 갱신은 batch 시점.

### 4.3 결정 로그 (2026-06-15)

| # | 결정 | 근거 (실측) |
|---|---|---|
| 1 | TC 포맷 스키마/표준을 `contracts/{tc-step,appium}/` 로 분리. contracts 정의를 **"트랙 간 입력·결과·증거 인터페이스"**로 확장. 생산자·검증기·실행 코드는 synthesis/automation 잔류 | `tc_step_schema.json` 을 `validate_tc.py`(synthesis)·`test_tc_loader`/`test_lint_schema`(automation 경계 테스트)가 공통 소비 → 한 트랙 내부 규격 아닌 경계 인터페이스. 한쪽에 묻으면 타 트랙이 내부 침범. |
| 2 | `git_safe_push_audit.py` 비이주 아님. `tools/`(repo-ops 영역) **planned-port** — 공통 엔진+테스트 보존, `FORBIDDEN_*` 정책 3상수만 qa-suite 기준 교체(→`contracts/repo-policy/`). 원본 검증 전 유지 | 정책이 `FORBIDDEN_BASENAME_PATTERNS`/`DIRECTORY_PREFIXES`/`NAMES` 3상수로 이미 분리·`matches_forbidden()` 소비. 2026-05-22 catalog 오분류 fix가 코드에 박혀 있어 재작성 시 회귀 위험. |
| 3 | `tc_samples` 파일별 분리. `golden/` 에는 미투입 | `TC_1.xlsx` 28참조 활성(→sources) / legacy yaml 3건 schema FAIL(→archive 후보) / `sample_call` 평문 PII(→sanitize 전 이주 금지) / folder·kids(→_inbox). |

## 5. 이주 규칙

1. 진행 중 캠페인 자산(Appium·alt-basic handoff 등)은 캠페인 종료 시점에 통째로 이동.
2. 이동은 복사→동작확인→provenance 기록(`copied`→`verified`)→원본 DEPRECATED 표기
   (`source-deprecated`)→다음 정리 때 삭제.
3. 경로 참조 스크립트는 이동 전 grep 으로 역참조 확인:
   `git grep -n "<파일명>"` 으로 참조처 갱신 목록 작성.
4. 주 1회 _inbox/ 트리아지: 비우거나 목적지 확정.
5. **단말×앱 폴더 분리-매핑**: `<단말명 - 앱명>/` 폴더는 BUG_LOG·MENU_TREE·RESUME·
   RESULT 시리즈를 `campaigns/<단말명 - 앱명>/` 으로 **한 폴더 유지** 이주하고,
   `catalog/` 하위만 `learning/catalogs/<단말명 - 앱명>/` 으로 분리한다
   (커밋 정책이 다름 — append-only tracked data). RESUME 의 세션 재개 운영성을 깨지 않는다.
6. **패키지 개명 규칙**: staging `automation/tests/` 패키지는 이주 시
   `automation/bug-repro/modules/` 로 개명한다 (import `tests.` → `modules.`).
   tc-step 이주 시 들어올 시험 스위트(tests/)와의 repo 내부 이름 충돌 방지.
   staging 에서는 무이동 — 개명은 형제 repo 복사 시점에 수행.
7. raw / keymap / 원본 로그 / report 류는 이주 대상이 아니다 — var/ (local-only) 에서
   새로 생성된다. 기존 산출물은 원본 repo 의 **ignored 영역 잔류** 또는 **repo 밖
   외부 local archive** 만 허용 — **tracked `archive/` 유입 금지** (redaction lock:
   raw/keymap commit 금지는 archive 경유로도 우회 불가).

## 6. 인벤토리 지시문

`docs/guides/inventory_prompt.md` 사용 (실경로·신규 목적지 enum 반영 v2).
