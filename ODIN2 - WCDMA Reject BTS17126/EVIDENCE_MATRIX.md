# EVIDENCE_MATRIX — ODIN2 WCDMA Reject (BTS-17126)

각 TC 별 **핵심 axes (PASS blocker)** / **보강 axes (PASS blocker 아님)** / **NOTE (scope 밖)** 를 분리해 명시. CLAUDE.md §4.2 "핵심 axes vs 보강 axes 분리" + §2.2 NOTE 어휘 적용. BTS18697 패턴 승격.

---

## 공통 어휘

| 라벨 | 의미 | PASS 영향 |
|---|---|---|
| **CORE** | PASS 판정의 핵심 axes — 미수집 시 PASS blocker | YES (수집 필수) |
| **SUPPORT** | 보강 근거 — 미수집이어도 PASS 판정 가능 | NO |
| **NOTE** | scope 밖 / 외부 정책 / 환경 한계 / 보조 진단 자료 | NO (FAIL 영향 없음) |

---

## TC-17126-01 — CS Reject Cause 표시 (회귀)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| OTA `LOCATION_UPDATE_REJECT` `rej_cause_val=N` | CORE | QXDM 0x713A UMTS UE OTA | — |
| Debug Screen `MM Cause` 필드 = N | CORE | UI dump / 스크린샷 | — |
| Reject popup cause = N (예 "(N)") | CORE | 단말 화면 popup 캡처 | — |
| logcat radio buffer cause 추적 | SUPPORT | `adb logcat -d -b radio` (telephony / qcril_qmi 등) | broad grep |
| QMI 0x1544 reject_cause (CS path) | SUPPORT | QXDM 0x1544 | 일치하면 보강, 없어도 PASS 가능 |

**PASS 기준**: 3-way (OTA / Debug screen / popup) 모두 동일 `N` → `runtime PASS`.

**이전 라운드**: Z0409U `runtime PASS` (cause=2) — 회귀 baseline.

---

## TC-17126-02 — PS Reject Cause 표시 (회귀)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| OTA `GMM_ATTACH_REJECT` `gmm_cause_val=7` | CORE | QXDM 0x713A | "GPRS services not allowed" |
| Debug Screen `GMM Cause` = 7 | CORE | UI dump / 스크린샷 | — |
| QMI 0x1544 reject 정보 (service_domain=Packet switched, reject_cause=7) | CORE | QXDM 0x1544 | 3-way 의 PS side |
| logcat radio buffer | SUPPORT | broad grep | — |
| Reject popup | SUPPORT | 화면 캡처 | popup 없을 수 있음 (PS-only 시) |

**PASS 기준**: 3-way (OTA / QMI / Debug screen) 모두 cause=7 → `runtime PASS`.

**이전 라운드**: Z0409U `runtime PASS` (cause=7) — 회귀 baseline.

---

## TC-17126-03 — CS+PS Combined Reject (회귀)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| OTA Combined Attach Reject (CS cause=2 + GMM cause=7) | CORE | QXDM 0x713A | Combined 동시 reject |
| Debug Screen MM Cause=2 + GMM Cause=7 | CORE | UI dump | — |
| QMI 양 도메인 reject 정보 | CORE | QXDM 0x1544 | — |
| KT 미인증 SIM 환경 한계 | **NOTE** | — | PS-only scope 만 trigger, Combined 자체 재현 불가 |
| Sh hwang 별도 결과 (Combined OK) | **NOTE** | 인용 | scope 밖 — 본 환경 PASS 근거 아님, 정황 인용용 |

**PASS 기준 (트리거 가능한 환경에서)**: 3-way 일치 → `runtime PASS`.

**본 환경 결정**: 우리 측 트리거 불가 → `NOTE: environment-limited (KT 미인증 SIM)` + Sh hwang 결과 인용. **FAIL 처리 아님**.

---

## TC-17126-04 — SM Reject Cause 표시 ★ 핵심

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| OTA `SM_ACTIVATE_PDP_CONTEXT_REJECT` `sm_cause_val=27 (0x1b)` | **CORE** | QXDM 0x713A | 3GPP TS 24.008 Table 10.5.157 "Missing or unknown APN" |
| QMI 0x1544 `wds_start_network_interface` resp / `call_end_reason=WDS_CER_UNKNOWN_APN` / `verbose.call_end_reason=27` | **CORE** | QXDM 0x1544 | QMI side ground truth |
| Debug Screen `SM Cause: 27` (또는 cause text label) | **CORE** | UI dump / 스크린샷 | UI side ground truth |
| Debug Screen 재진입 후 SM Cause 유지 (T0 = T1) | **CORE** | UI dump 2회 (TC-09 와 일부 중복) | resume 후 retain 확인 |
| logcat broad grep (`setEsmCause`, `cause:27`, `0x713A`, `0x1544`, `WDS_CER_UNKNOWN_APN`, `call_end_reason`) | SUPPORT | `adb logcat -d -b all` | 보강 근거. 특정 함수명 의존 X (사용자 명시) |
| Reject popup (SM 경우 popup 유무) | SUPPORT | 화면 캡처 | popup 없을 수 있음 |
| dumpsys telephony.registry `mPreciseDataConnectionState` | SUPPORT | `adb shell dumpsys telephony.registry` | reject reason 보강 |

**PASS 기준**: OTA `sm_cause=27` + QMI `verbose.call_end_reason=27` + DebugScreen `SM Cause: 27` **3-way 동시 일치** + Debug Screen 재진입 후 값 유지 → `runtime PASS`.

**FAIL 기준**: DebugScreen `SM Cause` 가 비어있거나 0 또는 다른 값 → `BUG-GAP observed` (이전 라운드 cause27→0 회귀 재현).

**이전 라운드**: Sh hwang 측 `BUG-GAP observed` (cause27→0). 자체 측 미수행. 본 빌드 fix 검증 핵심.

---

## TC-17126-05 — Cause Persistence (USIM / Airplane)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| T0: Reject 수신 직후 Debug Screen cause 값 | **CORE** | UI dump / 스크린샷 | baseline |
| T1: 시간 경과 (수 초~분) 후 Debug Screen 재진입 cause 값 | **CORE** | UI dump | retain 확인 |
| T2: USIM 제거 또는 Airplane ON 후 Debug Screen cause 값 | **CORE** | UI dump | clear 허용 시점 |
| T3: 정상 USIM 재삽입 또는 Airplane OFF + 정상 등록 후 cause 값 | **CORE** | UI dump | clear 확인 |
| OTA cause 값 (해당 시점 reject 의 ground truth) | CORE | QXDM 0x713A | T0 / T1 cause 값 비교 baseline |
| 후속 indication cause=0 발생 시점 (framework) | SUPPORT | logcat radio + QMI | T0 / T1 사이 framework 후속 indication 추적 |
| AP recording 활용 (#18 정책 언급) | SUPPORT | — | framework / RIL side AP 가 cause 값 저장하는지 |

**PASS 기준**: T0 = T1 (시간 경과해도 값 retain) + T2 또는 T3 에서 clear → §4.2 **정/역 재현 패턴** 만족 → `runtime PASS`.

**FAIL 기준**: T1 < T0 (덮어쓰기 발생) → `BUG-GAP observed`.

---

## TC-17126-06 — NAS_CIRCUIT_AND_PACKET_SWITCHED GMM Priority

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| cause #3 ("Illegal MS") 유도 가능 여부 자체 | **PENDING** | — | 트리거 방법 자체가 미확정 — `OPEN_QUESTIONS.md` 참조 |
| OTA reject cause=3 (Combined service_domain) | CORE (트리거 시) | QXDM 0x713A | 트리거 가능한 경우만 |
| QMI 0x1544 service_domain=NAS_CIRCUIT_AND_PACKET_SWITCHED + reject_cause=3 | CORE (트리거 시) | QXDM 0x1544 | — |
| Debug Screen 표시값 (cause #3, **GMM 슬롯 우선**) | CORE (트리거 시) | UI dump | #22 Sh hwang Request — MM 아닌 GMM 으로 표시되어야 함 |
| Reject popup cause = 3 | SUPPORT | 화면 캡처 | — |

**PASS 기준 (트리거 가능 시)**: 3-way 모두 cause #3 + DebugScreen GMM 슬롯에 표시 → `runtime PASS`.

**PASS blocker 아닌 NOTE 후보**: 트리거 불가 → `NOTE: trigger method unavailable / environment-limited`. **FAIL 처리 아님**.

---

## TC-17126-07 — Debug Screen UI 렌더링 (회귀)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| Debug Screen 정상 필드 표시 (DLCH/ULCH/BAND/PLMN/Cell/MM State/SubState/MM Cause/GMM State/SubState/GMM Cause/SM Cause/RRC/RSSI/Tx) | **CORE** | UI dump / 스크린샷 | 모든 필드 존재 확인 |
| "알 수 없음" 단일 텍스트 아님 | **CORE** | UI dump | 1차 Gerrit 해소 회귀 검증 |
| 화면 캡처 (사람 확인용) | SUPPORT | 스크린샷 | — |

**PASS 기준**: 정상 필드 모두 표시 → `runtime PASS`.

**FAIL 기준**: "알 수 없음" 단일 또는 필드 누락 → `BUG-GAP observed`.

---

## TC-17126-08 — Reject Popup 표시 (회귀)

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| Reject popup 표시 (OTA cause 에 맞는 텍스트) | **CORE** | 화면 캡처 | 예 "(3)" cause number |
| Popup cause number = Debug Screen MM Cause = OTA cause | **CORE** | popup + UI dump + QXDM | 3-way 일치 |
| Popup 문구 OCR 또는 수기 transcript | SUPPORT | — | 문구 검증 보강 |

**PASS 기준**: 3-way (popup / DebugScreen / OTA) cause 일치 → `runtime PASS`.

---

## TC-17126-09 — Debug Screen Resume Persistence

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| T0: 최초 진입 DebugScreen SM Cause | **CORE** | UI dump | baseline (TC-04 와 중복 가능) |
| T1: 백그라운드 30초 후 재진입 SM Cause | **CORE** | UI dump | resume 동작 |
| T2: 강제 종료 후 재실행 후 SM Cause | **CORE** | UI dump | persistence 강도 검증 |
| OTA / QMI ground truth (해당 시점 reject 값) | **CORE** | QXDM | 3-way 의 외부 axes |
| logcat broad grep (`setEsmCause`, `EsmCause`, `cause:27` 등) | SUPPORT | `adb logcat -d -b all` | 함수명 의존 X, 사후 어떤 라인 호출됐는지 확인용 |
| Debug Screen launch event (`ActivityTaskManager: START ... DebugScreen`) | SUPPORT | logcat main | 진입 시각 검증 |

**PASS 기준**: T0 = T1 = T2 (모두 동일 cause 값) + 외부 3-way ground truth 동시 일치 → `runtime PASS`.

**logcat 메모**: 본 사이클 `logcat_v2.txt` 에서 DebugScreen launch 2건 (19:06:36 / 19:08:23) 확인됨 — 같은 task ID 106 → resume scenario 일부 흔적. cause 라인은 radio buffer 필요.

---

## TC-17126-10 — E2E 통합

| Evidence | 라벨 | 추출 위치 | 비고 |
|---|---|---|---|
| TC-01 / TC-02 / TC-04 결과 모두 `runtime PASS` | **CORE** | 각 TC 결과 | — |
| TC-03 Combined 결과 | NOTE / CORE | KT 미인증 SIM 한계 | Sh hwang 결과 인용 + `NOTE` |
| Airplane on/off reset 동작 정상 | SUPPORT | UI / dumpsys | — |
| 각 단계 OTA / QMI 로그 동시 캡처 | **CORE** | QXDM HDF | 시간 순 정렬된 evidence |
| 각 단계 Debug Screen 캡처 | **CORE** | 스크린샷 / UI dump | 4 시점 (CS / PS / Combined / SM) |
| logcat 전 구간 | SUPPORT | `adb logcat -d -b all` 시간 마킹 | — |

**PASS 기준**: TC-01 / TC-02 / TC-04 모두 `runtime PASS` + TC-03 `NOTE` 처리 → 본 통합 사이클 `runtime PASS`.

---

## 본 사이클 (2026-05-28) Evidence 현황 요약

| TC | OTA (QXDM 0x713A) | QMI (QXDM 0x1544) | Debug Screen | logcat broad | 본 사이클 결론 |
|---|---|---|---|---|---|
| TC-01 ~ TC-10 | HDF 캡처 완료 (parse 미수행) | HDF 캡처 완료 (parse 미수행) | UI dump 미수집 (adb hang) | main buffer 4MB / radio 0 | 모두 미수행 — 다음 세션 Phase 1 |
| TC-09 보강 | — | — | DebugScreen launch 2건 logcat 확인 (19:06:36 / 19:08:23) | — | resume 동작 흔적만 SUPPORT 수준 |

다음 세션 진입 시 위 표의 **CORE** 항목들이 각 TC 별로 채워져야 PASS / FAIL 판정 가능.
