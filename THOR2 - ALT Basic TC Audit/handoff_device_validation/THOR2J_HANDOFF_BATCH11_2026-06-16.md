# THOR2J HANDOFF — ALT Basic validation batch11 (2026-06-16)

**무단말 작성 (정적). 실 F0 실행은 별도 승인 후.** commit/push/단말 호출 금지 상태에서 작성된 계약.

- **manifest (read-only)**: `VALIDATION_MANIFEST_BATCH11_2026-06-16.csv` (**64건**)
  - **batch11 29**: REVIEW device-free 구제 합성 (`stage1_s2_salvage_batch11/`)
  - **batch10_warn35 35**: batch10 WARN focus-state verifier 강화분 (`stage1_review_mapping_batch10/`, S1)
- **runner**: thor2j-tc-appium `runner/altbasic_validation_batch11.py` (b1/b3/b4 helper 재사용, **device 세션 승인 시 작성**)
- **핵심 신규**: 본 배치는 **focus_state(48) + element_presence(10) + verify_text/popup(6)** 중심 — 텍스트 literal이 없는 focus/presence verifier가 다수. **selector는 전부 PENDING_F0** → run1 dump로 확정.
- **KPI**: 본 배치 TWO_RUN_GREEN만 RUNNABLE_NOW 증가. STAGE1_DRAFT(480)·DVR 미가산.

## 1. 단말 / 실행 규약

| 항목 | 계약 |
|---|---|
| 단말 | **F0 `B06201249E0002F0` 고정** (build RY07260600S, ko-KR). **B27 `B2700125BW000083` 미접촉** |
| run | 모든 TC **run1 / run2 독립 실행** (`--run 1` 전수 → `--run 2` 전수). 상호 상태 비공유 |
| 승격 | **TWO_RUN_GREEN(run1=SINGLE_RUN_PASS ∧ run2=RUN2_PASS)만 RUNNABLE_NOW**. 단일 run PASS = 미승격 |
| 결과 어휘 | `SINGLE_RUN_PASS`/`RUN2_PASS` · `ENTRY_FAILED` · `VERIFIER_FAILED` · **`CLEANUP_FAILED`(잔존/복귀 실패 — 즉시 보고)** · `DEVICE_FIT_SKIP`(pre/빌드 부적합, FAIL 아님) · `RISK_BLOCKED` · `INFRA_FAILURE` |
| skip ≠ fail | DEVICE_FIT_SKIP은 KPI 분모 제외. FAIL(ENTRY/VERIFIER/CLEANUP)과 분리 집계 |
| run 순서 | manifest **risk_rank 오름차순**(focus nav R1 → observe R2 → selection R3 → transient_input R4 → popup_cancel R5). 저위험 먼저 |

## 2. focus_state verifier 캡처 절차 (핵심 — 48건)

텍스트 assert 불가. **`focused=true` 요소를 dump해 assert 종류별로 대조**. run1에서 selector(resource-id·text·bounds) 확정 → `verifier_contract.device_value` 채움(현 PENDING_F0).

| assert | 캡처 절차 | PASS 조건 |
|---|---|---|
| focus_move | 키 입력 전/후 `focused=true` 요소 채록 | 입력 후 요소가 변경(이동) |
| focus_invariant | 입력 전/후 채록 | 동일 요소 유지(불변) |
| focus_boundary_stop | 연속 입력 중 추적 | 이동 후 끝단에서 불변(비루프) |
| focus_created | 입력 전 focused 부재 확인 | 입력 후 focused 요소 출현 |
| focus_retained | 팝업/드롭박스 전 채록 | 취소/back/OK 후 동일 요소 focused |
| focus_position | — | focused 요소가 대상 입력 필드(id/class) |
| focus_absent | 진입 직후 | focused 요소 부재 |

- dump = `uiautomator dump` 또는 Appium source. **`focused="true"` 속성 노드의 resource-id·text·bounds** 추출.
- run1에서 selector 미확정 시 `VERIFIER_FAILED` 정직 기록 후 보정 사이클 (발명 금지).

## 3. element_presence (7건)

- 대상 element를 **resource-id/text presence**로 판정 (PENDING_F0 → run1 확정).
- 화면 전환/메뉴 진입 후 대상 노드 존재만 assert. 내용/값 비단정.

## 4. popup_cancel 안전 게이트 (8건 — R5, 최고위험)

OK 입력이 **실 시스템 확인 다이얼로그**를 트리거 (화면 터치 잠금·데이터 절약·화면 녹화·화면 전송 등).

| 규칙 | 내용 |
|---|---|
| 관찰 | 다이얼로그 **고정 literal presence만** 판정 (예: "화면 터치 잠금 켜기"·"데이터 절약 모드를 사용 설정 하시겠습니까?"·"녹화를 시작 하겠습니까?"·"기기로 화면 전송") |
| 이탈 | **반드시 '취소'/back** — 확정 0 |
| 확정 금지 (denylist) | `켜기`·`사용 설정`·`시작`·`전송`·`연결`·`확인`(영속) tap **절대 금지** = 잠금/절약/녹화/전송 미적용 |
| 위반 시 | 확정 tap 발생 = 실 mutation → `CLEANUP_FAILED` + **즉시 보고**(임의 원복 금지) |

## 5. transient_input 안전 (11건 — R4)

- 하드키/숫자 입력은 **가역**(계산기 AC/clear, 다이얼러 입력 후 clear/back). **저장·연산 확정·통화 발신 금지**.
- 입력 후 display/field text 또는 focus 관찰만. 입력 문자열은 known digit 사용(연락처/실데이터 비의존).
- dialer 계열(CAL): 번호 입력 후 **발신(call) 절대 금지**, clear/back으로 입력칸 비우고 이탈.

## 6. helper 생명주기 (mutation 0 입증)

- 실행 전/후: `adb -s F0 shell pm list packages | sort > evidence/altbasic_batch11_20260616_pkg_{pre,post}.txt`
- 종료 시: Appium uiautomator2 helper(`io.appium.*`) **uninstall**. **pre==post diff 0 필수**.
- 잔존 0 추가 확인: 알람/연락처/대화/녹음/사진/시스템토글(잠금·절약·녹화·전송) — **전부 생성·변경 0** (본 배치 mutation 설계 없음).

## 7. 금지 사항 (denylist — 항구)

- fixture·계정·알람·연락처·대화·사진·녹음 **생성 0**.
- 위험 tap denylist: 시스템 확인 다이얼로그 `켜기`/`사용 설정`/`시작`/`전송`/`연결`/`확인`(영속) · `저장` · `전송`/`발송`/`보내기` · `허용`(권한) · `삭제` · 다이얼러 발신 · `am start` 컴포넌트 직접 기동(런처 경유만).
- ⓔ 연락처 기본 계정 / ⓑ 알람 fixture = 계속 보류 (본 배치 미포함).

## 8. redaction (CHECK 14건)

- Call/Contacts/Message sheet 14건 = dump이 **기존 연락처/통화/메시지 PII 부수 채록 가능**. redaction gate 적용 후 sidecar만 커밋, raw/png **local-only**.
- focus/presence verifier는 **요소 id/bounds만 필요** — PII 텍스트 불요. dump에서 focused 노드 외 PII는 토큰화.

## 9. 산출 / 보고

- evidence: `thor2j-tc-appium/evidence/altbasic_batch11_20260616/run{1,2}/{tc_id}/` (xml+png, **local-only**)
- 결과 CSV: `evidence/.../results_run{1,2}.csv`
- 회수 리포트: thor2j `reports/ALTBASIC_BATCH11_RESULT_2026-06-16.md` + tc-runner `RESULT_RECOVERY_BATCH11_*.md`
- 카탈로그: 신규 focus selector/literal 발견 시 `catalog/f0_literal_catalog.csv` append (build RY07260600S).
- **verifier_contract.device_value 확정분**은 run1 후 STAGE1 yaml에 환류(별도 무단말 보정 — PENDING_F0 → 실 selector).

## 10. 정적 검증 (실행 전 통과)

runner syntax · manifest TC ID **64** 정합 · 위험 tap denylist 0 · focus/presence 캡처 절차 완비 · reports/evidence local-only · **commit/push/단말 호출 금지**.
