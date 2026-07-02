# TC_SUITE — ODIN2 WCDMA Reject (BTS-17126)

본 suite 는 댓글 #18, #21, #22, #27, #28, #30 요구사항을 종합한 10개 TC. 사용자 제공 안 기반 + 본 repo 어휘 / NOTE / 3-way ground truth 원칙 반영.

---

## 공통 사전 조건

- **DUT**: ODIN2 / AT-M150, 2026-05-27 이후 Daily 빌드 (정확 ID 미확정 — YanLijie 확인 항목)
  - 비교 baseline: `test_AT-M150Z0409U_DAILY_DEV_GMS_774_without_persist.zip` (이전 라운드)
- **Network**: WCDMA (UMTS) 환경
- **SIM**: KT 미인증 USIM (`reference_wcdma_test_sim.md`)
- **APN**: 정상 (`lte.ktfwing.com` 등) + 비정상 (`test.com`) profile 사전 준비
- **Tool**: QXDM/QCAT (0x713A UE OTA, 0x1544 QMI_MCS_QCSI_PKT), adb logcat
- **경로**: Settings → Debug Screen info (`com.android.phone/.settings.DebugScreen`)

---

## TC-17126-01. CS Reject Cause 표시 (회귀)

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | WCDMA only 모드, CS Reject 유발 환경 |
| Steps | 1) Boot up<br>2) CS Location Update 시도<br>3) OTA `LOCATION_UPDATE_REJECT` 수신 유도<br>4) Debug Screen info 진입 |
| Expected | Reject popup 정상 표시 / MM Cause 필드 = OTA cause 값 (예 cause=2 "IMSI unknown in HLR") / "1" 같은 invalid 아님 |
| PASS 기준 | 3-way 일치: OTA `rej_cause_val=N` / Debug screen MM Cause = N / popup cause 표시 = N → `runtime PASS` |
| FAIL 기준 | MM Cause 비어있음 또는 OTA 값과 불일치 → `step verify_text FAIL` 또는 `BUG-GAP observed` |
| 이전 라운드 | PASS (자체 TC-B, Z0409U 빌드) |
| Reference | 댓글 #27 "1. CS Reject (OK)" |

---

## TC-17126-02. PS Reject Cause 표시 (회귀)

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | WCDMA only 모드, PS Attach 시도 환경 |
| Steps | 1) Boot up<br>2) GPRS/PS Attach 시도<br>3) OTA `GMM_ATTACH_REJECT` 수신 유도 (예 gmm_cause=7 "GPRS services not allowed")<br>4) Debug Screen info 진입 |
| Expected | Reject popup 표시 / GMM Cause = OTA `gmm_cause_val` / QMI `Registration reject reason` (service_domain=Packet switched, reject_cause=7) 일치 |
| PASS 기준 | 3-way: OTA `gmm_cause_val=7` / QMI reject_cause=7 / Debug screen GMM Cause = 7 → `runtime PASS` |
| FAIL 기준 | 위 불일치 또는 GMM Cause 누락 → `BUG-GAP observed` |
| 이전 라운드 | PASS (자체 TC-A, Z0409U 빌드) |
| Reference | 댓글 #27 "2. PS Reject (OK)" |

---

## TC-17126-03. CS+PS Combined Reject Cause 표시 (회귀)

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | Combined Attach 환경 |
| Steps | 1) Boot up<br>2) Combined Attach 시도<br>3) CS=cause=2 / PS=cause=7 동시 수신 유도<br>4) Debug Screen 진입 |
| Expected | MM Cause / GMM Cause 모두 OTA 값 일치 / popup 정상 표시 |
| PASS 기준 | 3-way: OTA CS cause=2 / GMM cause=7 / Debug screen MM Cause=2 + GMM Cause=7 → `runtime PASS` |
| FAIL 기준 | Combined 표시 누락 또는 단일 cause 만 표시 → `BUG-GAP observed` |
| 환경 제약 | KT 미인증 USIM 으로는 PS-only scope 만 트리거됨 → 자체 재현 불가. Sh hwang 별도 결과 (Combined OK) 인용 + `NOTE: environment-limited (KT 미인증 SIM)` |
| Reference | 댓글 #27 "3. CS PS Reject (OK)" |

---

## TC-17126-04. SM Reject Cause 표시 ★ 핵심

| 항목 | 내용 |
|---|---|
| Priority | **Critical / Blocker** |
| Pre | APN 설정에 잘못된 APN (`test.com`) profile 추가 후 default 선택. 참고 link: `https://drive.google.com/file/d/1nsotjoJd2fOyV9ZRxe1QQtZhxM78KB40/view?usp=sharing` (#28) |
| Steps | 1) `test.com` APN default 선택<br>2) Data 연결 시도 → PDP Context Activation 트리거<br>3) OTA `SM_ACTIVATE_PDP_CONTEXT_REJECT` `sm_cause_val=27 (0x1b) Missing or unknown APN` 확인<br>4) QMI `wds_start_network_interface` 응답 `QMI_RESULT_FAILURE` / `QMI_ERR_CALL_FAILED` / `WDS_CER_UNKNOWN_APN` / `verbose.call_end_reason=27` 확인<br>5) Debug Screen info 진입<br>6) Debug Screen 나갔다가 재진입 (resume) |
| Expected | **SM Cause: 27** 정확히 표시 (3GPP TS 24.008 Table 10.5.157 "Missing or unknown APN") / Debug Screen 재진입 시에도 값 유지 / cause text label 함께 표시되면 더 좋음 |
| **PASS 기준 (3-way)** | OTA `sm_cause_val=27` / QMI `verbose.call_end_reason=27` / Debug screen `SM Cause: 27` 3 출처 모두 일치 + Step 6 재진입 후에도 유지 → `runtime PASS` |
| FAIL 기준 | SM Cause 비어있음 또는 0 또는 다른 값 → `BUG-GAP observed` (이전 라운드 동일 회귀로 확인) |
| 이전 라운드 | Sh hwang 측 FAIL (cause27→0, 2026-04-13 캡처). 자체 미수행. 본 라운드 fix 검증 핵심. |
| Reference | 댓글 #21, #27, #28, #30 |

---

## TC-17126-05. MM/GMM/SM Cause Persistence

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | 정상 USIM 제거 또는 unauthorized USIM 사용 |
| Steps | 1) Wrong/Unauthorized USIM 삽입<br>2) Network 등록 시도 → MM/GMM reject 수신 유도<br>3) Debug Screen 진입, cause 값 확인 (T0)<br>4) 시간 경과 (수 초~수 분, framework 후속 indication cause=0 가능 시점 포함)<br>5) Debug Screen 재진입, cause 값 확인 (T1)<br>6) USIM 제거 또는 Airplane ON → Debug Screen 확인 (T2)<br>7) Airplane OFF / 정상 USIM 재삽입 → Debug Screen 확인 (T3) |
| Expected | T0 ≈ T1 (시간 경과해도 cause retain) / T2 = clear 허용 / T3 = 정상 등록 후 clear |
| PASS 기준 | T0 = T1 = (OTA cause 값) / T2 또는 T3 에서 clear → §4.2 정/역 재현 패턴 만족 → `runtime PASS` |
| FAIL 기준 | T1 < T0 (덮어쓰기 발생) → `BUG-GAP observed` |
| Reference | 댓글 #16 (YanLijie 질문) + #18 (Sh hwang 정책 답변: "usim/airplane 제거 시까지 reject cause value 유지 + ap recording 활용") |

---

## TC-17126-06. NAS_CIRCUIT_AND_PACKET_SWITCHED GMM Priority

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | AP 가 QMI 로 `service_domain = NAS_CIRCUIT_AND_PACKET_SWITCHED` + `reject_cause` 수신 환경 |
| Steps | 1) reject cause #3 ("Illegal MS") 유도 환경 구성 — **트리거 방법 불명, 사용자 측 확인 항목**<br>2) Debug Screen 진입<br>3) 표시되는 cause 값 확인 |
| Expected | Debug Screen 에 **GMM reject cause 우선 apply** (MM Reject Cause 아님) / popup 도 GMM 기반 |
| PASS 기준 (트리거 가능 시) | 3-way: OTA cause #3 / QMI 또는 framework cause #3 / Debug screen 표시값 = cause #3 (GMM 슬롯) → `runtime PASS` |
| 환경 제약 | cause #3 유도 가능 여부 본 사이클에서 확인 항목. 불가 시 `NOTE: trigger method unknown / environment-limited` — PASS blocker 아님. |
| Reference | 댓글 #22 Sh hwang Request: "When ap received NAS_CIRCUIT_AND_PACKET_SWITCHED reject cause message via QMI, apply GMM reject cause instead of MM Reject Cause" |

---

## TC-17126-07. Reject 시 Debug Screen UI 렌더링 (회귀)

| 항목 | 내용 |
|---|---|
| Priority | Medium |
| Steps | 1) 임의 reject (MM/GMM/SM 중 하나) 발생 상태로 진입<br>2) Debug Screen info 메뉴 진입 |
| Expected | DLCH/ULCH/BAND/PLMN/Cell/MM State·SubState·Cause/GMM State·SubState·Cause/SM Cause/RRC/RSSI/Tx 모든 정상 필드 표시 / "알 수 없음" 단일 텍스트 아님 |
| PASS 기준 | 모든 필드 정상 표시 (manual evidence observed 가능, 그러나 1차 ground truth = UI dump) → `runtime PASS` |
| FAIL 기준 | "알 수 없음" 단일 표시 또는 필드 누락 → `BUG-GAP observed` |
| Reference | 본문 [Results] 4번 — 1차 Gerrit 해소 회귀 확인 |

---

## TC-17126-08. Reject Popup 표시 (회귀)

| 항목 | 내용 |
|---|---|
| Priority | Medium |
| Steps | 1) Unauthorized USIM 삽입 또는 잘못된 PLMN 환경 구성<br>2) Reject 수신 대기 |
| Expected | "가입자 인증에 실패하였습니다. 휴대폰 전원을 껐다 켠 후에도 문제가 지속되면 고객센터(1599-0011)에 문의해 주세요. (3)" 등 OTA cause 에 맞는 popup / popup 의 cause number 와 Debug Screen MM Cause 일치 |
| PASS 기준 | popup cause = Debug screen MM Cause = OTA cause → `runtime PASS` |
| FAIL 기준 | popup 미표시 또는 cause 불일치 → `BUG-GAP observed` |
| Reference | 본문 [Results] 1번 |

---

## TC-17126-09. Debug Screen Resume / Re-entry Persistence

| 항목 | 내용 |
|---|---|
| Priority | High |
| Pre | TC-04 와 동일 환경 (SM Reject 발생 상태) |
| Steps | 1) SM Reject 발생<br>2) Debug Screen 진입, SM Cause 값 확인 (T0)<br>3) Home 버튼 등으로 백그라운드 전환<br>4) 30 초 후 Debug Screen 재진입 (resume) — SM Cause 값 확인 (T1)<br>5) Application 강제 종료 후 재실행 — SM Cause 값 확인 (T2)<br>6) logcat broad capture: `setEsmCause`, `EsmCause`, `SM Cause`, `sm cause`, `cause:27`, `call_end_reason`, `0x1544`, `0x713A` (보강) |
| Expected | T0 = T1 = T2 (resume / 재실행 모두 cause 값 유지) / framework 가 저장된 cause 다시 읽어 표시 |
| PASS 기준 | DebugScreen 표시값이 T0/T1/T2 모두 동일 + 3-way ground truth 동시 일치 → `runtime PASS` |
| FAIL 기준 | T1 또는 T2 에서 cause 누락 / 변경 → `BUG-GAP observed` |
| logcat 보강 | 특정 함수명 (`setEsmCause`) 단독 의존 X — broad capture 후 어떤 라인이 호출됐는지 사후 확인. PASS 단독 근거 아님. |
| Reference | 댓글 #30 YanLijie 분석 |

---

## TC-17126-10. E2E 통합 시나리오

| 항목 | 내용 |
|---|---|
| Priority | High |
| Steps | 1) CS Reject 유발 → Debug Screen 캡처<br>2) Airplane on/off 로 reset<br>3) PS Reject 유발 → Debug Screen 캡처<br>4) Airplane on/off 로 reset<br>5) CS+PS Reject 유발 → Debug Screen 캡처 (KT 미인증 SIM 한계로 자체 실행 X / Sh hwang 결과 인용)<br>6) Airplane on/off 로 reset<br>7) SM Reject (잘못된 APN) 유발 → Debug Screen 캡처<br>8) 각 단계 OTA/QMI 로그 동시 캡처 |
| Expected | 4 가지 케이스 OTA cause 값과 Debug Screen 표시값 1:1 일치 / 모든 popup 정상 / cause 값 USIM/Airplane 동작 이전까지 유지 |
| PASS 기준 | TC-01 / TC-02 / TC-04 모두 `runtime PASS` + TC-03 Combined = `NOTE` (Sh hwang 결과 인용) → 본 사이클 `runtime PASS` |
| FAIL 기준 | 4 중 하나라도 cause 불일치 → 해당 단계 `BUG-GAP observed`, 본 통합 사이클 FAIL |
| Reference | 댓글 #21, #27 |

---

## 검증 우선순위

1. **TC-04 (SM Reject)** ★ 핵심
2. **TC-09 (Resume Persistence)** — TC-04 환경 그대로
3. **TC-05 (Cause Persistence)**
4. **TC-01 / TC-02 (CS / PS 회귀)**
5. **TC-07 / TC-08 (UI / Popup 회귀)**
6. **TC-03 (Combined)** — Sh hwang 결과 인용 + `NOTE`
7. **TC-06 (NAS_CS_PS Priority)** — cause #3 트리거 가능성 확인 후 진행 / 불가 시 `NOTE`
8. **TC-10 (E2E)** — Phase 1~4 종합

## 보고 양식 (사용자 제공 양식 + 본 repo 어휘)

```
Build: AT-M150___ DAILY (0527 이후, 정확 ID 확정 후 채움)
검증일: 2026-MM-DD
검증자: jinwu (ALT_Chung)

TC-01 (CS Reject)            : [ ] runtime PASS  [ ] BUG-GAP observed
TC-02 (PS Reject)            : [ ] runtime PASS  [ ] BUG-GAP observed
TC-03 (CS+PS Reject)         : [ ] runtime PASS  [ ] BUG-GAP observed  [ ] NOTE (environment-limited)
TC-04 (SM Reject) ★          : [ ] runtime PASS  [ ] BUG-GAP observed  ← 핵심
TC-05 (Cause Persistence)    : [ ] runtime PASS  [ ] BUG-GAP observed
TC-06 (NAS_CS_PS GMM Prio)   : [ ] runtime PASS  [ ] BUG-GAP observed  [ ] NOTE (trigger unavailable)
TC-07 (Debug UI 렌더링)       : [ ] runtime PASS  [ ] BUG-GAP observed
TC-08 (Reject Popup)         : [ ] runtime PASS  [ ] BUG-GAP observed
TC-09 (Resume Persistence)   : [ ] runtime PASS  [ ] BUG-GAP observed
TC-10 (E2E 통합)             : [ ] runtime PASS  [ ] BUG-GAP observed

첨부: OTA log (QXDM 0x713A), QMI log (0x1544), Debug Screen 스크린샷, UI dump, logcat broad capture
```
