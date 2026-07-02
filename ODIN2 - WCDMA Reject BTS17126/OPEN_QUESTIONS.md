# OPEN_QUESTIONS — ODIN2 WCDMA Reject (BTS-17126)

본 사이클 (2026-05-28) 종료 시점 미해결 질문 누적. 다음 세션 사용자 / Sh hwang / YanLijie 측 회신 후 갱신.

---

## Q1. 빌드 정확 ID

- **상태**: PENDING
- **현재 표기**: "2026-05-27 이후 Daily"
- **확인 방법**: YanLijie 측 빌드 zip 명 또는 단말 `getprop ro.build.display.id` / `ro.build.version.incremental`
- **영향**: 검증 결과 보고 시 빌드 ID 정확 명시 필요 (RESULT_<날짜>.md 메타)
- **다음 액션**: 사용자 측 YanLijie 댓글 또는 본인 측 build map 확인

---

## Q2. TC-06 NAS_CIRCUIT_AND_PACKET_SWITCHED 트리거 방법

- **상태**: PENDING (사용자도 의미/트리거 불명 — 본 사이클 사용자 명시)
- **단서**: #22 Sh hwang Request — "When ap received NAS_CIRCUIT_AND_PACKET_SWITCHED reject cause message via QMI, apply GMM reject cause instead of MM Reject Cause"
  - QMI `service_domain = NAS_CIRCUIT_AND_PACKET_SWITCHED` + `reject_cause` 인 경우 framework 에서 GMM cause 우선 적용해야 함
  - reject cause 후보 = #3 ("Illegal MS") — 사용자 명시
- **트리거 후보** (가설):
  - Combined Attach + 특정 network 거부 응답
  - Modem AT command 으로 강제 cause 주입 (테스트 모드)
  - Network simulator (CMW500 등) 사용
- **본 환경 한계**: KT 미인증 USIM = PS-only scope, Combined 자체 재현 어려움
- **다음 액션**: Sh hwang 측 재현 환경 확인 또는 트리거 방법 회신 요청. 불가능 시 본 BUG 사이클에서는 `NOTE: trigger unavailable / environment-limited` 로 종료.

---

## Q3. HDF 파일 parse 후 cause 값

- **상태**: PENDING (QCAT 미실행)
- **파일**: `doc/BTS17126/Test_05-28.19-09-20-776.hdf` (136 MB, 2026-05-28 19:09:20 시점)
- **필요 추출**:
  - 0x713A UMTS UE OTA — 사이클 시각 (19:06:36 / 19:08:23 DebugScreen 진입 ± 60초) 윈도우 안의 reject 메시지
  - 0x1544 QMI_MCS_QCSI_PKT — 같은 윈도우 안 `wds_start_network_interface` resp
- **의문**:
  - HDF 안에 SM Reject cause=27 메시지가 실제 포함됐는가? (= 본 사이클이 의도된 트리거를 발생시켰는가?)
  - DebugScreen 진입 시점에 SM Cause 표시값은 무엇이었나? (UI dump 미수집)
- **다음 액션**: 사용자 측 QCAT 으로 HDF 열어 0x713A / 0x1544 추출 → `EVIDENCE_MATRIX.md` 채움

---

## Q4. adb shell hang 근본 원인

- **상태**: 가설 단계
- **관찰**: `adb logcat -d -b main` 은 4MB 캡처 성공 / `adb shell <cmd>` 는 모두 hang
- **가설**:
  - QXDM 도구가 USB DIAG 채널 점유 → adb shell pty 응답 지연
  - 단말 측 adbd 다중 로깅 부하
  - Start-Process 격리해도 동일 → PowerShell pipeline 문제 아님
- **검증 방법**:
  - QXDM 종료 후 adb shell 응답 회복 확인
  - 단말 재부팅 후 응답 회복 확인
  - 다른 ODIN2 단말 (있다면) 비교
- **다음 액션**: 다음 세션 진입 시 QXDM 종료 → `adb shell echo alive` PASS 확인 → 정상 시 위 가설 확정

---

## Q5. TC-09 logcat 특정 함수명 (`setEsmCause` 등) framework 위치

- **상태**: SUPPORT 근거 — PASS blocker 아님 (사용자 명시)
- **단서**: 댓글 #30 YanLijie 분석에서 `setEsmCause` 호출 라인 18738 언급
- **사용자 결정**: 특정 함수명 의존 X — broad grep 으로 사후 어떤 라인이 호출됐는지 확인
- **다음 액션**: TC-09 실행 후 `logcat_all_TC09_<ts>.txt` broad grep 결과에서 어떤 cause 관련 라인이 출현했는지 사후 분석. 단, PASS 판정은 DebugScreen / OTA / QMI ground truth 기반.

---

## Q6. KT 미인증 SIM 으로 TC-03 Combined 재현 가능성

- **상태**: 불가 (이전 라운드 경험)
- **이전 라운드 관찰**: KT 미인증 SIM = PS-only scope cause 7 만 트리거됨. Combined 경로 진입 안 됨.
- **다음 액션**: 본 사이클도 동일 한계 가정 → `NOTE: environment-limited` 로 처리. Sh hwang 별도 결과 (Combined OK) 인용.
- **잠재 우회** (사용자 결정 필요):
  - Combined 가능한 SIM 확보 (다른 미인증 USIM, 다른 carrier)
  - Network simulator 사용
  - Sh hwang 측 환경 위임

---

## Q7. APN profile 적용 절차 — 단말 reboot 필요 여부

- **상태**: 정황 단서 — 메모리 `reference_pcat_data_profile.md` "profile 추가 후 재부팅해야 +CGDCONT에 반영됨"
- **의문**: `test.com` APN profile 을 Settings UI 에서 추가 + default 선택만으로 PDP Activation 시 사용되는가? 또는 reboot 필요?
- **다음 액션**: Phase 1 진입 전 APN 적용 후 1회 reboot 권장. reboot 없이 진행 시 `dumpsys telephony.registry` 의 `mApnSetting` 또는 PDP context 추적 보강.

---

## Q8. Debug Screen UI 필드 텍스트 정확 매칭

- **상태**: PENDING (UI dump 미수집)
- **의문**:
  - Debug Screen 의 SM Cause 필드 라벨이 한국어인가 영어인가? (예 "SM Cause" 또는 "SM 원인")
  - cause value 표기 형식 (decimal `27` / hex `0x1b` / text label "Missing or unknown APN")?
  - 필드가 비어있을 때 표시 (`--` / `0` / 빈 문자열)?
- **다음 액션**: Phase 1 진입 첫 UI dump 수집 후 라벨 표기 매핑 fix. `MENU_TREE.md` 또는 본 파일에 매핑 표 추가.

---

## Q9. PDF 원본 (#16, #18, #21, #22, #27, #28, #30) 댓글 내용 fact check

- **상태**: PDF unreadable (본 사이클 Read tool 접근 실패)
- **현재 근거**: 메모리 `project_bug17126_wcdma_reject.md` + 사용자 제공 TC suite 메시지
- **의문**: 메모리 / 사용자 메시지 기록과 PDF 원문 사이 drift 가능성
- **다음 액션**:
  - 사용자 측 PDF 읽기 (수기 transcript)
  - 또는 poppler 설치 / PDF tool 별도 시도 (사용자 결정 — 본 사이클 사용자 명시 "설치 시도 금지")
  - 그 전까지는 메모리 기록을 source 로 신뢰

---

## Q10. cause text label 표시 여부 (PASS 기준 보강)

- **상태**: PENDING — TC-04 PASS 기준에서 "cause text label 까지 함께 표시되면 더 좋음" 명시 (TC_SUITE.md)
- **의문**: Debug Screen 이 `SM Cause: 27` 만 표시하는지, `SM Cause: 27 (Missing or unknown APN)` 같이 text label 도 표시하는지
- **다음 액션**: Phase 1 UI dump 수집 시 확인. 부가 보강 사항 (PASS blocker 아님).

---

## Q11. 본 cycle (2026-05-28) HDF 가 실제 의도된 TC-04 트리거를 캡처했는가

- **상태**: PENDING (QCAT 미실행 + 사용자 부재 중 확인 불가)
- **단서**:
  - HDF 시각 = 19:09:20
  - logcat DebugScreen launch = 19:06:36, 19:08:23
  - APN 설정 / WCDMA 캠프 / 비행기 OFF 적용 여부 미확인 (adb shell hang)
- **다음 액션**: 다음 세션에 사용자 측 QCAT 으로 HDF 열어 0x713A `SM_ACTIVATE_PDP_CONTEXT_REJECT` 메시지 존재 여부 확인. 존재하지 않으면 본 HDF 는 baseline 아님 → 새 사이클 캡처 필요.

---

## Q12. 미수집 보강 자료 (logcat radio buffer, dumpsys, getprop)

- **상태**: 미수집 (본 사이클 adb shell hang)
- **다음 액션**: A2 (adb shell hang 회복) 후 즉시 캡처. `COLLECTION_COMMANDS.md` Section 1 참조.

---

## 본 사이클 종료 시점 누적 = 12건

다음 세션 진입 시 Q1 / Q2 / Q3 / Q4 우선 회신 권장. 나머지는 Phase 1 실기 진입 후 자연 해소.
