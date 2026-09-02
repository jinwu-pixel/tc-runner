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
- write 위치는 고정 역할표가 아닌 **자산별 권위 원장**으로 결정 (§2.5)

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

**exact-bytes 실행 캡슐 (RUNBOOK 템플릿 v2)**: 사용자가 승인한 exact-bytes 캡슐 실행도 본 승인 게이트 틀 안에서만 유효하다. `scripts/evidence_verifier.py` **exit 0** 인 Tier 0 작업은 검토를 **attestation + spot-check 로 축소** 가능. **multi-task 자동연속은 미승격** — 실 Tier-0 다중-task 증거 축적 전까지 개별 승인 유지 (§8.2 2026-07-23). Tier 1/2 · device · commit / push 는 항상 별도 명시 승인.

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
- **과거 baseline 참조는 immutable 결박**: 검증기·테스트가 참조하는 과거 시점 baseline은 이동 ref(`HEAD` 등)가 아닌 **immutable object(OID) + content hash 이중 pin** 으로 고정. 부재·불일치 = fail-closed, 이동 ref fallback 금지 (근거: `6b7213b` verifier 자기무효화 → `099c0db` 보정, §8.2 2026-08-27)
- 근거 사례: PR 0 `verify_gone` drift

### 2.4 Evidence Accumulation (원칙)

자동화 산출물은 휘발하지 않고 **디스크에 누적**되어야 한다.

- 누적 데이터는 다음 TC 작성·delta 판단의 입력으로 재사용
- 데이터가 남지 않는 자동화는 도입하지 않는다 (단기 속도 개선이 정확성·재현성을 훼손하면 채택 X)
- planned 항목을 implemented 인 척 보고하지 않는다 (planned는 그대로 표기)
- **파생로그 provenance 예외**: 원본 캡처(qmdl / dump / 스크린샷)는 보존. 재생성 가능한 대용량 파생로그는 source hash · 도구/필터 버전 · digest · 재생성 경로를 남길 때만 **digest-only 보존** 허용 (§8.2 2026-06-01)
- **구체 경로 enumeration은 §5.6 참조** (본 섹션은 원칙만)

### 2.5 Branch Policy — qa-suite 권위 원장 routing

통합 목적지 = 형제 repo `C:\Users\momen\Projects\qa-suite` (설계 SoT: qa-suite `ARCHITECTURE.md` · `MIGRATION.md`). 이주 프로그램은 개시됐으나 **"통합 완료" 일반화 금지** — canonical `MIGRATION.md` §4.4 원장 기준 cutover `[O]` = 거버넌스 문서 4행뿐이고, 코드·데이터 `[V]` 자산의 **writer 는 여전히 원본 repo** 다.

- write 위치 결정 = 고정 tc-runner↔thor2j 역할표가 아닌 **자산별 `[O]`/`[V]` 권위 원장** (`qa-suite/MIGRATION.md` §4.4)
- `[V]` 자산 수정 = 원본 repo 에 write (qa-suite 본 = 검증 스냅샷, 드리프트는 refresh 규칙으로 봉합)
- `[O]` 자산 수정 = qa-suite 에 write (원본 = deprecated)
- **cross-commit 금지 유지** — 한 변경을 두 repo 에 동시 커밋하지 않는다
- tc-runner 내 staging `qa-suite/` 디렉토리 = **deprecated 사본** (write 금지)

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

**모뎀 산출물 판정 경계**:
모뎀 산출물의 권위는 판정 축에 따라 다르다 — IMS 등록/코덱처럼 모뎀이 ground truth 인 축이 있는 반면(§4.6 IMS SIP), **정상경로 PASS 판정을 모뎀 산출물 단독으로 내리지 않는다** (모뎀 분석 = failure discriminator, 정상경로 판정 병행). 단말 특이성 여부는 **REF 단말 negative-control** 로 가른다. (§8.2 2026-06-01)

**레이어 분리·대조군 판정 (a11y/TalkBack 류)**:
관찰 도구가 피관찰 상태를 교란하는 영역(TalkBack×하드키 등)은 입력 포커스≠a11y 포커스 분리, 키 시퀀스 중 dump 금지, tap/swipe 의 터치탐색 우회를 전제로 절차를 짜고, 발화·포커스 판정은 **정상 앱/유휴 대조군** 동반 시에만 결론화한다. 상세 SoT = `docs/talkback_dpad_verification.md`. (§8.2 2026-07-02)

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
| `evidence_verifier.py` | runbook 증거 검증기 (capture-baseline/verify 2모드, C0~C5 fail-closed·exit `0/1/2/3`, git hash-object·JUnit·결정론 bundle, baseline 바이트 결박). runbook Tier 0 검토를 attestation+spot-check로 축소. Tier-1 검증·T0-CHAR 파일럿 GREEN (2026-07-23) |
| `gen_provenance_manifest.py` | frozen shell-RC campaign evidence JSON → tracked provenance manifest 결정론 seed (mapping/selector/binding `12/14/15`·workbook raw SHA pin·타임스탬프/난수/절대경로 0, 동일 입력 byte-identical) |
| `tests/test_provenance_manifest.py` (pytest gate) | shell-RC provenance G1~G5 fail-closed 게이트 (manifest schema·기수, workbook pin·production loader row hash, curated `tc_name`·step projection, campaign evidence baseline) |
| `canonical_shell_rc_remediation_check.py` + `canonical_shell_rc_remediation_manifest_v1.json` | curated shell-RC 18개 blocker의 baseline/transformation manifest와 host-only fail-closed 검증 gate (P2 current projection `12/14/15`, 비대상 의미론·index·capsule scope 결박, 결정론 evidence 발행) |
| `appwidget_stale_provider_repro.py` + `appwidget_stale_provider_*.py` | BUG27084 전용 phase harness. exact device/profile/APK gate, read-only capture, bind/arm/trigger/verify/restore/reset-fixture, sealed evidence와 RCBD lineage를 제공한다. host 구현·known-bad 실기 완료, exact fixed-build 검증 pending |
| `appwidget_stale_provider_provenance.py` | runtime harness exact-set을 repo-relative bytes로 계산하고 `harness_commit + source_digest_sha256`을 일반 phase 호환성 기준으로 강제한다. legacy/mismatch bundle은 restore-only이며 `preserve_armed_state`는 금지 |

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
- TalkBack 검증 중 adb 함정 3종: `uiautomator dump` = TalkBack 일시 억제(키 시퀀스 중 dump 금지) / `input tap·swipe` = 터치탐색 우회 즉시클릭 / MSYS `/sdcard` 인자 변환 + PowerShell 5.1 바이너리 리다이렉트 UTF-16 오염 — 상세 `docs/talkback_dpad_verification.md`

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

**Post-commit 재검증**: git 상태(`HEAD` blob·커밋 이력)를 읽는 검증은 **pre-commit GREEN 으로 완결 주장 불가** — commit 후 재실행해야 유효. push 게이트의 전체 회귀 실행이 이 계층의 안전망이다 (근거: §8.2 2026-08-27, pre-commit GREEN → post-commit 3 FAIL 발현).

**위임 commit/push relay (명시 승인 후)**:
1. 승인된 exact path를 각각 `git add -- <path>`로 개별 stage한다 (broad add 금지).
2. commit 전에 `tools/git_safe_push_audit.py --expected-path <path>...`로 staged path의 missing/unexpected가 0인지 확인한다.
3. exact staged-set PASS와 사용자 commit 승인을 확인한 뒤 commit한다.
4. `git fetch origin`으로 remote 기준을 갱신한다.
5. `ahead=1`, `behind=0` 및 `origin/master..HEAD` committed path exact-set을 감사한다.
6. force 옵션 없이 fast-forward push한다.
7. push 후 remote/`HEAD`/`origin/master` 일치, `ahead=0`·`behind=0`, tracked/staged clean을 확인한다.

commit과 push는 각각 사용자 명시 승인 범위 안에서만 수행하며, relay는 그 승인을 대체하지 않는다.

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
| 2026-06-01 | diagnostic evidence 경계 | BUG-25796 QXDM offline 추가검증 뒤 ODIN2 IMS/QCAT 사례까지 재확인: 모뎀 산출물은 failure discriminator·후속 분석 자료이고 정상경로 판정과 분리해야 하며, REF negative-control 로 단말 특이성을 가른다. 원본 캡처는 보존하되 재생성 가능한 대용량 파생로그는 source hash·도구/필터·digest·재생성 경로를 남길 때만 digest-only 허용 | §2.4(파생로그 provenance 예외)·§4.2(모뎀 산출물 단독 정상경로 PASS 금지 + REF negative-control 병행) — 본문 반영 2026-08-27 | applied |
| 2026-06-12 | qa-suite 권위 전환 | 형제 repo `C:\Users\momen\Projects\qa-suite` 이주 프로그램 개시·거버넌스 문서 4건 cutover 완료. 다만 canonical `MIGRATION.md` §4.4 기준 코드·데이터는 아직 `[V]` 이며 원본 repo 가 writer 이므로 “통합 완료” 일반화 금지. 고정 tc-runner↔thor2j 역할표 대신 자산별 `[O]`/`[V]` 권위 원장으로 write 위치를 결정하고 cross-commit 은 계속 금지 | §1.3·§2.5를 qa-suite 권위 원장 routing 으로 교체; staging `qa-suite/` 는 deprecated 사본으로 명시 — 본문 반영 2026-08-27 | applied |
| 2026-06-16 | workflow agent 안전 | ALT batch11 합성 중 워크플로 agent가 구조화 반환 대신 yaml 4개를 batch10 dir 직접 기록(file side-effect) + 슬라이스 over-read(53/29 반환). git 추적 검증으로 phantom(untracked·`fc56cf8` 미포함) 확정·삭제·정정. → 합성 agent read-only/return-only 제약 + 실행 후 untracked 오염 스캔 필요 | §5.7·§5.4 (workflow 운영규칙+오염 스캔 도구) | applied |
| 2026-06-16 | tc_id 무결성 | tc_id `ALTBASIC_<PREFIX>_<excel_row3>` 비단사 + Excel 4 sheet(Safety/Launcher/Call/Camera) 중복 TC ID 83건 = **잠재(latent) 구조 위험**(실발현 0). batch11 실충돌 4건(CALC_027/028·SST_010/011)의 실제 원인 = 워크플로 phantom side-effect(위 row — batch11분을 batch10 dir 오기록)이지 Excel dup 아님(근거 3중: 충돌 row_key가 KEEP_CONFIRMED 271에 부재·충돌 sheet가 dup 4 sheet 미포함·phantom 삭제 후 gate 충돌 0). gate 포착·최종 실충돌 0/29. 도구화 `scratch/altbasic_tcid_collision_check.py`(cross-batch + Excel dup 감사, prep 선행 게이트). 정정 근거: FAILURE_TAXONOMY_2026-07-03 C7 FM1 | §5.3 (collision_check 도구 등록)·§8.2 인과정정(31a1d64) | applied |
| 2026-06-16 | diagnostic / IMS 검증 | ODIN2 Engineer IMS 복합 기능 TC 검증: AP logcat reg-state·callProfile(`audioCodecAttribute=null`)은 IMS 등록/코덱 **비권위** — 모뎀 `.qmdl` SIP(log `0x156E`) REGISTER↔resp **Call-ID 매칭**이 ground truth. TC1 임의값(bare Domain `sktelecom2`→req-URI `sip:sktelecom2`)→`404`×3 등록실패 관찰(누락 신호 0). + "복합 시험" = 필드격리 아닌 기능 시나리오(임의값 동시→실호/재등록→신호 반영) | §4.6 대표 사례 + memory([[reference_ims_sip_qcat_verification]]·[[feedback_combined_test_functional_scenario]]) | applied |
| 2026-06-17 | 단말 런타임 효율·정확도 | Engineer IMS 8케이스 실기가 과다 소요 — 항목별 앱 cold 재기동·불필요 reboot(둘이 최대급 손실; reboot는 호 파라미터 환원까지)·조기 qmdl pull·단말정체 미확인(self-call·USIM 교체)·Way1·2≠Way3 매번 재판별. 도구화(런너 caseset/preflight+wrong-device 가드/capture 상태-게이트) + 카탈로그 RUNTIME_PLAYBOOK Override Applicability Matrix + feedback 메모리 | §5.3 (`eng_mode_runner.py`+profile, host-TDD/dry-run) + §4.2(applicability 재사용) + `RUNTIME_PLAYBOOK.md`; 범용 경로 device smoke pending | applied |
| 2026-06-17 | QCAT 파싱 단축 도구 | 대용량 qmdl(155M/131만p) QCAT 파싱 병목 = OpenLog 전수 인덱싱(~148s, 86%가 불요 0x1FEB debug). 단축법 정립·실측: filter-first(SaveAsText 전 SetAll(false)+Set+Commit, 564MB→KB) + ISF 캐시(SaveAsISF 1회→재오픈 0.2s, ~740×, 무손실) + 단일 포그라운드 세션(0x80080005 진짜 원인=QCAT 첫기동 DirectPlay 모달 launch 블록, 백그라운드 금지). `scripts/qcat_fast_extract.ps1` 승격 + BTS15068·40M 양 캡처 검증. 0xB193=RSRP/RSRQ per-antenna ground truth | §5.3 (qcat_fast_extract.ps1·ims_sip_digest.py)·docs/qcat_parsing.md·memory([[reference_qcat_fast_extraction]]·[[project_bts15068_antbar]]) | applied |
| 2026-07-02 | TalkBack×하드키 검증 방법론 | THOR2_J×LINE 이슈 2건의 SPEC_GAP 규명으로 앱 무관 절차 확립: 입력/a11y 포커스 분리, FocusFinder shadowing·ViewPager 키 소비, 키 시퀀스 중 dump 금지, tap/swipe 의 터치탐색 우회, TTS·오디오포커스 타임라인과 정상 앱/유휴 대조군. 상세 플레이북과 S1~S8 체크리스트는 문서화됐으나 자동 스크리닝 도구는 미구현 | §4.2에 레이어 분리·대조군 판정 원칙, §5.5에 adb/PowerShell 오염 함정 등록; `docs/talkback_dpad_verification.md`를 상세 SoT로 연결. S1~S8 도구화는 별도 승인 유지 — 본문 반영 2026-08-27 | applied |
| 2026-07-23 | exact-bytes 실행 캡슐 | RUNBOOK v2(Tier 0/1/2 + exact-bytes capsule)와 `scripts/evidence_verifier.py`가 T0-CHAR 단일-task 파일럿에서 baseline drift·백슬래시 정규화 버그를 fail-closed로 포착해 mechanism은 증명했다. 다만 multi-task 자동연속은 미실행이므로 일반 정책 승격 근거는 아직 없다. Tier 1/2와 device·commit·push는 계속 별도 명시 승인 | §2.1에 “사용자가 승인한 exact-bytes 캡슐도 명시 승인”과 attestation+spot-check 검토 축소만 등록; §3.x 자동연속 lock은 실 multi-task 증거 전까지 보류(§3.5 SMOKE 규칙과 별개). §5.3 도구 설명은 현행 유지 — 본문 반영 2026-08-27 | applied |
| 2026-09-02 | BUG27084 실행 source 결박 | known-bad campaign은 evidence/schedule/device identity는 봉인했지만 단일 immutable harness revision으로 실행되지 않았다. runtime exact-set의 POSIX 상대경로·byte size·대문자 SHA-256을 canonical UTF-8 JSON으로 digest하고 Git path-scoped commit과 함께 기록한다. 일반 phase/child/reset은 source mismatch·legacy를 fail-closed하고, 단말 안전 restore만 manifest 선검증과 예외 artifact를 남긴 뒤 허용한다 | §5.3 harness/provenance 도구 등록; 상세 계약은 `docs/superpowers/specs/2026-08-29-appwidget-stale-provider-knowledge-pipeline-design.md` amendment와 BUG27084 handoff | applied |
| 2026-07-25 | canonical execution contract cutover | G0~G2-device 및 Cutover 승인 충족: 2026-07-24 THOR2_J Settings legacy↔canonical 4-run 48/48·action/step/passed mismatch 0·canonical shell message rc=0·serial pin 일치. `cli run` argparse default만 canonical로 승격(`78b3ac3`); explicit `--contract-mode legacy`와 library default는 유지. legacy 제거·corpus rewrite·qa-suite cutover·신규 device campaign은 미승인 | `src/cli.py`·`THOR2_J - Settings/RESULT_2026-07-24.md`·canonical design §8.5/§11 | applied |
| 2026-08-12 | shell-RC provenance campaign | 공식 P0/P1 campaign이 mapping 12·selector 14·binding 15의 관계를 복원하고, P1 mismatch를 category-wide target-source gap의 측정 baseline으로 남겼다. mismatch 관찰은 campaign 실패가 아니라 후속 remediation 입력이며 evidence bundle을 보존한다. | `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md`·`reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/PROVENANCE_EVIDENCE.json` | applied |
| 2026-08-12 | P2 provenance manifest | frozen campaign evidence를 tracked manifest로 승격하고 결정론 seed와 G1~G5 게이트를 도입했다. production loader 의미론·workbook pin·curated projection을 fail-closed로 결박하며, provenance YAML은 canonical TC inventory 수집에서 제외한다. 최종 범위는 신규 4 + pre-edit amendment 승인 tracked 3 = 7경로, 전체 회귀 1545 passed. | §5.3·`provenance/ss_call_shell_rc_manifest.yaml`·P2 design §8.1 | applied |
| 2026-08-13 | 위임 scope·승인 감사 | reviewer가 자기 채널에서 승인 이력을 보지 못한 경우 `무승인`으로 단정하지 않고 `승인 이력 확인 필요`로 보고한다. 구현 중 발견 변경은 편집 전 amendment 승인을 받고, commit 전 exact-path staged audit를 강제하며, 과거 기록은 당시 값과 superseded 주석을 함께 보존한다. | §7.2·P2 design §8.1·producer reconcile amendment §9 | applied |
| 2026-08-18 | shell-RC curated remediation | curated YAML을 권위 source로 유지하고 P2 current projection과 분리된 baseline/transformation manifest로 provenance를 보존하면서 shell-RC blocker 18건을 runner/schema/validator 변경 없이 fail-closed `verify_shell`로 전환했다. | §5.3·`canonical_shell_rc_remediation_check.py`·`canonical_shell_rc_remediation_manifest_v1.json` | applied |
| 2026-08-18 | shell-RC safety reclassification | audited `exported_ss_call` corpus의 16 step이 결정론적 rc 포착용 bounded scratch로 `READ_ONLY_SHELL`→`UNKNOWN_UNSAFE`, audit adapter상 `FULL_AUTO`→`MANUAL_REQUIRED`로 재분류됐다. production `execution_contract`/저장 `execution_type`에는 전파되지 않으며 두 계층 연결은 별도 정책 승인이 필요하다. | §3.3·`tests/fixtures/anchor/corpus_audit_baseline.json` | applied |
| 2026-08-18 | capsule v5 evidence ownership | `reports/canonical_shell_rc_remediation/` verifier-owned ignored subtree는 schema-v5 capsule invariant에서 제외하고 generator/consumer가 동일 산식으로 계산한다. 무결박 subtree는 Task 9 전수 보상감사로 통제한다. | `dispatch_capsule.py`·`canonical_shell_rc_remediation_check.py` | applied |
| 2026-08-27 | post-commit baseline identity | shell-RC remediation 커밋 `6b7213b`가 반영된 뒤 verifier/test가 pre-remediation P2를 moving `HEAD`에서 읽어 자기무효화되고, HEAD blob 기반 inventory 기대값도 commit 전에는 새 worktree를 보지 못해 전체 회귀 3건이 뒤늦게 FAIL. `099c0db`에서 immutable full OID `4c484d53…` + raw SHA 이중 pin, object/path/hash 불일치 fail-closed, inventory 정렬과 post-commit 전체 1638 passed로 보정 | §2.3(과거 baseline 참조 immutable object+content hash 이중 pin)·§7.2(post-commit 재검증) — 본문 반영 2026-08-27 | applied |

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
