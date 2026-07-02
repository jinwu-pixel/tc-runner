# BUG_LOG — ODIN2 WCDMA Reject (BTS-17126)

## 요약표

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| BTS-17126 | WCDMA Debug Screen / MM·GMM·SM Reject cause 표시 | OBSERVED | IN_PROGRESS | 이전 라운드 SM Reject cause27→0 FAIL, 본 라운드 0527 빌드에서 fix 검증 | TC-17126-01~10 | `doc/17126*.pdf`, 0x713A / 0x1544 OTA, Debug screen 캡처 (수집 예정) |

---

## BTS-17126

- **기능 영역**: ODIN2 WCDMA Debug Screen — MM / GMM / SM Reject cause 표시 및 retain 동작
- **진단 상태**: OBSERVED — SM Reject 표시 누락 1회 이상 관찰 (이전 라운드 Sh hwang 측), root cause 미확정
- **이슈 상태**: IN_PROGRESS — 0527 빌드 검증 사이클 진행 중
- **단말**: ODIN2 (AT-M150)
- **앱**: Settings → Debug Screen info
- **요약**: WCDMA 환경에서 MM·GMM·SM 각 도메인 reject 발생 시 Debug Screen 표시값이 OTA·QMI ground truth와 일치하고, USIM/Airplane 동작 이전까지 retain 되어야 함
- **기대 결과**:
  - CS Reject → MM Cause = OTA `rej_cause_val` 값
  - PS Reject → GMM Cause = OTA `gmm_cause_val` 값
  - SM Reject → SM Cause = OTA `sm_cause_val` 값 (3GPP TS 24.008 Table 10.5.157)
  - cause 값은 USIM 제거 또는 Airplane ON 까지 유지, 정상 등록 후 clear
  - NAS_CIRCUIT_AND_PACKET_SWITCHED reject 수신 시 GMM cause 우선 apply
- **실제 결과** (직전 라운드 — `test_AT-M150Z0409U_DAILY_DEV_GMS_774_without_persist.zip`):
  - CS / PS / Combined Reject 표시 OK (Sh hwang + 자체 TC-A/B 일치)
  - SM Reject 표시 FAIL — OTA `sm_cause_val=27` / QMI `verbose.call_end_reason=27` 일치하나 Debug screen `SM Cause: 0` (cause27→0 누락, 프레임워크 표시 라우팅 회귀 의심)
- **재현 절차** (요약 — 상세는 `TC_SUITE.md`):
  1. KT 미인증 USIM 삽입, WCDMA 캠프 강제 (`adb shell cmd phone set-allowed-network-types-for-users -s 0 17284`)
  2. Settings → APN 에 잘못된 APN (`test.com` 등) 추가 후 default 선택
  3. Data 연결 시도 → PDP Context Activation 트리거
  4. QXDM 0x713A 로 `SM_ACTIVATE_PDP_CONTEXT_REJECT` `sm_cause_val=27` 확인
  5. QMI 0x1544 `wds_start_network_interface` 응답 `verbose.call_end_reason=27` 확인
  6. Settings → Debug Screen info 진입, `SM Cause` 필드 값 확인 → PASS 기준 `27`
- **증거**:
  - `doc/17126 [ODIN2][WCDMA][DEBUG] MMGMMSM Reject cause.pdf` (1차 원본)
  - `doc/17126 [ODIN2][WCDMA][DEBUG] MMGMMSM Reject cause.pdf_02.pdf` (2026-04-13 Sh hwang→YanLijie 결과 + SM Reject FAIL 캡처)
  - 본 라운드 OTA / QMI / Debug Screen 스크린샷 = 수집 예정 (RESULT_*.md 부착)
- **관련 TC**: TC-17126-01 ~ TC-17126-10 (`TC_SUITE.md`)
- **정정 이력**:
  - 2026-04-13 — Z0409U 빌드 1차 검증: CS / PS PASS, Combined Sh hwang 별도 OK, SM Reject FAIL 신규 발견 → 수정 빌드 대기
  - 2026-05-28 — 본 RESULT 시리즈 진입 (Phase 0 skeleton). 검증 빌드 = 2026-05-27 이후 Daily (정확 ID는 사용자 측 YanLijie 확인 예정)
  - 2026-05-28 — Phase 1 단말 진입 시도 → adb shell hang (QXDM DIAG 점유 의심) + 사용자 부재로 offline 분석 사이클로 전환. `EVIDENCE_MATRIX.md` / `COLLECTION_COMMANDS.md` / `CHECKLIST_NEXT_SESSION.md` / `OPEN_QUESTIONS.md` 추가. 다음 세션 Phase 1 실기 진입 예정.

---

## 세션 결과

(본 BUG 사이클 진행되며 `RESULT_YYYY-MM-DD.md` 발행. 본문 BUG-LOG 항목은 현재 상태만 유지하고, 사이클별 결과는 RESULT 시리즈에서 누적.)

- `RESULT_2026-05-28.md` — Phase 0 skeleton (단말 조작 전, 검증 사이클 시작 전 상태 고정)
