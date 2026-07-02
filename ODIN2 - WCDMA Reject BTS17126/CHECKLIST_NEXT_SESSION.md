# CHECKLIST_NEXT_SESSION — ODIN2 WCDMA Reject (BTS-17126)

다음 세션 사용자 복귀 시 "무엇부터 확인 / 무엇을 캡처" 가 한눈에. 우선순위 순.

---

## A. 환경 sanity (Phase 1 진입 전 필수)

- [ ] **A1**. 빌드 정확 ID 확정 — YanLijie 측 댓글 / 빌드 zip 파일명 / `getprop ro.build.display.id` 확인. `RESUME.md` 환경 표 갱신.
- [ ] **A2**. 단말 adb shell 응답 sanity:
  - 본 사이클 (2026-05-28) `adb shell <cmd>` 전부 hang. `adb logcat` 만 동작.
  - 가설: QXDM DIAG/USB 채널 점유
  - 복구 절차: QXDM 도구 종료 → `adb kill-server; adb start-server` → `adb shell echo alive` PASS 확인
  - `COLLECTION_COMMANDS.md` Section 0 참조
- [ ] **A3**. 단말 화면 unlock + USB 디버깅 정상.
- [ ] **A4**. KT 미인증 USIM 삽입 (`reference_wcdma_test_sim.md`) — 다른 SIM 사용 금지 (SKT 미인증 = LTE lock).
- [ ] **A5**. APN 설정 → 잘못된 APN (`test.com`) profile 추가 + **default 선택**.
- [ ] **A6**. WCDMA 강제 캠프 명령 적용 여부 결정 (`adb shell cmd phone set-allowed-network-types-for-users -s 0 17284`). 비행기 OFF 직전 적용해도 됨.
- [ ] **A7**. QXDM 마스크 활성:
  - 0x713A UMTS UE OTA
  - 0x1544 QMI_MCS_QCSI_PKT
- [ ] **A8**. QCAT (또는 동등) 후처리 도구 준비 — HDF parse 필수.

---

## B. Phase 1 — TC-04 SM Reject (★ 핵심)

진입 조건: A1~A8 완료.

- [ ] **B1**. 사이클 시각 마킹 시작 (QXDM 로그 + 단말 시각 동기 권장).
- [ ] **B2**. 단말 비행기 OFF → PDP Context Activation 자동 트리거.
- [ ] **B3**. 30~60초 PDP retry 동안 캡처 환경 유지.
- [ ] **B4**. Settings → Debug Screen info 진입.
- [ ] **B5**. 캡처 (`COLLECTION_COMMANDS.md` Section 3.2):
  - [ ] `logcat_all_TC04_<ts>.txt` (all-buffer)
  - [ ] `ui_dump_TC04_<ts>.xml` (Debug Screen)
  - [ ] `dumpsys_telephony_TC04_<ts>.txt`
  - [ ] `debugscreen_TC04_<ts>.png` (스크린샷)
- [ ] **B6**. QXDM HDF stop / save.

### TC-04 PASS / FAIL 판정 (B7~B9)

- [ ] **B7**. QXDM HDF → QCAT 0x713A filter → `SM_ACTIVATE_PDP_CONTEXT_REJECT` 추출. **`sm_cause_val = ?`** 기록.
- [ ] **B8**. QXDM HDF → QCAT 0x1544 filter → `wds_start_network_interface` resp 추출. **`verbose.call_end_reason = ?`** 기록.
- [ ] **B9**. `ui_dump_TC04_<ts>.xml` 파싱 → **`SM Cause = ?`** 기록.

**판정**:
- B7 = B8 = B9 = 27 → `runtime PASS` (BTS-17126 SM Reject fix 완료)
- B9 = 0 또는 비어있음 → `BUG-GAP observed` (이전 라운드 회귀 재현, fix 미적용)
- B7 / B8 = 27 + B9 != 27 → `BUG-GAP observed` (3-way 불일치, framework 표시 라우팅 누락)

---

## C. Phase 1 — TC-09 Resume Persistence (TC-04 동반)

진입 조건: B1~B6 완료.

- [ ] **C1**. T0 = B5 결과 사용.
- [ ] **C2**. Debug Screen Home (`KEYCODE_HOME`) → 30초 대기 → 재진입.
- [ ] **C3**. `ui_dump_TC09_T1_<ts>.xml` 캡처.
- [ ] **C4**. `am force-stop com.android.phone` → 재실행 → 재진입.
- [ ] **C5**. `ui_dump_TC09_T2_<ts>.xml` 캡처.
- [ ] **C6**. logcat broad grep 적용 (`COLLECTION_COMMANDS.md` Section 5).

**판정**: T0 = T1 = T2 (SM Cause 값) → `runtime PASS`.

---

## D. Phase 2 — TC-05 Cause Persistence

- [ ] **D1**. TC-04 환경 유지 (Reject cause 보존).
- [ ] **D2**. T1 = 3분 시간 경과 후 UI dump.
- [ ] **D3**. T2 = USIM 제거 또는 Airplane ON (사용자 수기) → UI dump.
- [ ] **D4**. T3 = USIM 재삽입 또는 Airplane OFF + 정상 등록 → UI dump.

**판정**: T0 = T1 (retain) + T2 / T3 clear → `runtime PASS`.

---

## E. Phase 3 — TC-01 / TC-02 / TC-07 / TC-08 회귀

- [ ] **E1**. Airplane reset → CS LU Reject 환경 유도 → QXDM + UI dump → TC-01 / TC-08
- [ ] **E2**. Airplane reset → PS Attach Reject 환경 → QXDM + UI dump → TC-02
- [ ] **E3**. 임의 reject 상태에서 Debug Screen 모든 필드 표시 확인 → TC-07
- [ ] **E4**. Reject popup 캡처 (스크린샷) → cause 일치 확인 → TC-08

---

## F. Phase 4 — TC-03 / TC-06 환경 제약 항목

- [ ] **F1**. TC-03 Combined: KT 미인증 SIM scope 한계 명시. Sh hwang 결과 인용 + `NOTE: environment-limited` 처리. **자체 트리거 시도 X**.
- [ ] **F2**. TC-06 NAS_CS_PS GMM priority:
  - cause #3 ("Illegal MS") 유도 가능 방법 사용자 검토
  - 가능 시 → 트리거 → 3-way 캡처
  - 불가 시 → `NOTE: trigger unavailable / environment-limited`

---

## G. Phase 5 — TC-10 E2E

진입 조건: TC-01 / TC-02 / TC-04 모두 `runtime PASS`.

- [ ] **G1**. 1세션 안에 CS → PS → (Combined `NOTE`) → SM 순서로 재현
- [ ] **G2**. 각 단계 QXDM 시간 마킹 + Debug Screen 캡처
- [ ] **G3**. 4 단계 OTA cause = Debug Screen 표시 1:1 일치 확인

---

## H. 사이클 종료 — 보고서 갱신

- [ ] **H1**. `RESULT_<날짜>.md` 신규 발행 (사이클 1회 = RESULT 1개 원칙)
  - 본 사이클 (2026-05-28) RESULT 와 별도 — `reference_result_series_revalidation_cycle.md`
- [ ] **H2**. `BUG_LOG.md` 본문 갱신 (현재 상태만, 정정 이력 1줄)
- [ ] **H3**. `EVIDENCE_MATRIX.md` evidence 채움
- [ ] **H4**. `OPEN_QUESTIONS.md` 해소된 항목 표시 + 신규 질문 추가
- [ ] **H5**. 사용자 명시 후 batch commit (§7)
  - Claude 자체 commit 금지

---

## I. 위험 / 함정 (본 사이클 학습)

- **adb shell hang** — QXDM 도구가 USB DIAG 채널 점유 시 발생 가능. `adb logcat -d` 는 동작하지만 shell 명령은 응답 안 함. → A2 의 복구 절차 시도.
- **PowerShell pipeline buffer 폭주** — `& $adb logcat -d > $out` 형태 redirect 가 대용량 buffer 시 hang. `Start-Process ... -RedirectStandardOutput` 으로 격리.
- **UTF-16 인코딩** — PowerShell `>` redirect default 가 UTF-16 LE. grep 시 ASCII 패턴 매칭 0건. `Out-File -Encoding utf8` 또는 `Start-Process -RedirectStandardOutput` 사용 권장.
- **HDF binary** — QCAT 없이 parse 불가. QXDM 캡처 후 즉시 QCAT post-process 권장.
- **PDF unreadable** — Read tool 이 bracket path 접근 실패. PDF 원본 참조가 필요하면 사용자 수기 transcript.
- **단말 부재 / 자리비움 중** — 본 repo CLAUDE.md §2.1 에 따라 사용자 명시 신호 없이 단말 조작 금지.

---

## J. 미수행 / 미해결 항목 (본 사이클)

- [ ] 빌드 정확 ID 확정
- [ ] TC-04 / TC-05 / TC-09 / TC-01 / TC-02 / TC-07 / TC-08 / TC-10 모두 실기 미수행
- [ ] HDF parse (QCAT 미실행)
- [ ] TC-06 cause #3 트리거 방법
- [ ] adb shell hang 근본 원인 + 회복 절차 검증

상세 = `OPEN_QUESTIONS.md`.
