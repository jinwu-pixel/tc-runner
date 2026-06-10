# thor2j-tc-appium 실기 검증 handoff — ALT Basic validation batch 1 (2026-06-10)

**발신**: tc-runner (정적 후보 생성·handoff 담당. 실행 코드 작성·단말 호출은 본 repo 범위 밖)
**수신**: thor2j-tc-appium 에이전트 (`C:\Users\momen\Projects\thor2j-tc-appium`)
**경계**: cross-commit 금지 — thor2j는 본 manifest를 **read-only 참조**. tc-runner 파일 수정 금지, 결과는 thor2j 측 산출물로 기록 후 tc-runner가 회수.

## 입력 (절대 경로)

- 실행 manifest (20건, run_order 포함): `C:\Users\momen\Projects\tc-runner\THOR2 - ALT Basic TC Audit\handoff_device_validation\VALIDATION_MANIFEST_BATCH1_2026-06-10.csv`
- TC 상세 (CTF YAML, manifest의 `yaml_abs_path` 컬럼): batch01/03/04 폴더 분산, manifest가 절대 경로 보유
- handoff 계약 (entry/verifier/cleanup/risk/precondition): `HANDOFF_PACKAGE{,_BATCH03,_BATCH04}_2026-06-10.csv` 동일 폴더

## 단말 제약 (위반 = 즉시 중단)

- **F0 `B06201249E0002F0`만 사용** — 모든 ADB/Appium `-s` 고정
- **B27 `B2700125BW000083` 미접촉** (thor2j 기본 단말이지만 본 batch는 ko ALT corpus → F0)
- **선결 승인 항목**: F0는 현재 무설치 read-only probe 단말 — Appium uiautomator2 구동은 helper APK 설치를 동반하므로 **단말 호출 승인 시 "F0 Appium 서버 설치 허용"을 명시 확인** 후 진행
- 단말 호출 자체가 별도 명시 승인 후에만 가능

## 실행 계약

1. **Run 1** = 20건 전체, manifest `run_order` 순서대로
2. **Run 2** = Run 1 PASS **이며 cleanup 성공**한 건만
3. TC 간 HOME/reset/cleanup 수행 (manifest `cleanup` 컬럼 절차)
4. mutation·외부효과 징후 발견 시 해당 TC 즉시 `RISK_BLOCKED` — 계속 진행 금지
5. `precondition` 미충족 = skip (FAIL 아님)
6. verifier: expected_texts는 paraphrase 후보 — **1차 관찰에서 on-screen literal 확정 후 고정**, paraphrase 그대로 PASS 단정 금지
7. entry `launcher_tap_unresolved_package`: launcher에서 앱 이름 tap. 패키지 확정은 read-only `resolve-activity`/dumpsys로만 (설치/변경 0)

## 결과 taxonomy (필수 — 이 어휘로만 기록)

| 코드 | 의미 |
|---|---|
| `TWO_RUN_GREEN` | Run1+Run2 모두 PASS — **이것만 RUNNABLE_NOW evidence** |
| `SINGLE_RUN_PASS` | Run1 PASS, Run2 미수행/실패 — 재실행 대기 |
| `ENTRY_FAILED` | 진입 실패 (화면 미도달) |
| `VERIFIER_FAILED` | 진입 성공, 기대 텍스트/상태 불일치 |
| `CLEANUP_FAILED` | 검증 후 원상복귀 실패 |
| `DEVICE_FIT_SKIP` | carrier/SIM/환경 불일치 — **FAIL 아님** |
| `RISK_BLOCKED` | mutation/외부효과 발견으로 차단 |
| `INFRA_FAILURE` | Appium/USB/드라이버 등 — **TC 실패율 분모에서 제외** |

## 회수 계약 (tc-runner 측 Phase 4)

- 결과는 source TC 기준(`tc_id` + `source` 컬럼)으로 본 handoff와 재연결
- `TWO_RUN_GREEN`만 RUNNABLE_NOW evidence로 기록 — 정적 등급 승격은 실행 결과 없이는 0
- FocusRule 등 타 corpus 결과 전이 금지
- 실패는 entry/verifier/cleanup/device-fit 4축으로 분리 보고

## 선정 요약

DVR_CANDIDATE 75 중 20 선정. 제외: carrier UNCONFIRMED 11 / redaction REQUIRED·CHECK 5 / 외부 pkg 가능(Google leaf) 3 / INPUT_REQUIRED 6 / 기타 분산 조정. Camera 1건(CAM_002)은 최초 실행 권한 팝업 1회 전제 — 사전 수동 동의 후 실행.
