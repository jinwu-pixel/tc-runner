# MENU_TREE — ODIN2 WCDMA Reject 검증 경로

검증 사이클에서 자주 들어가는 화면 / dump / log 경로를 한 곳에. 새 경로 발견 시 추가.

---

## Debug Screen info 진입

- 진입: Settings → Debug Screen info
- Package / Activity (참고 — `reference_odin2_debugscreen.md`):
  - `com.android.phone/.settings.DebugScreen`
  - 직접 launch: `adb shell am start -n com.android.phone/.settings.DebugScreen`
- 표시 필드 (관측 대상):
  - DLCH / ULCH
  - BAND / PLMN / Cell
  - MM State / SubState / **MM Cause**
  - GMM State / SubState / **GMM Cause**
  - **SM Cause**
  - RRC / RSSI / Tx

## APN 설정 (TC-04 / TC-10 SM Reject 트리거)

- 진입: Settings → Connections → Mobile networks → Access Point Names
- 또는 Settings → 모바일 네트워크 → APN
- 잘못된 APN profile (`test.com` 등) 추가 → default 선택
- 참고 link: `https://drive.google.com/file/d/1nsotjoJd2fOyV9ZRxe1QQtZhxM78KB40/view?usp=sharing` (#28)
- 적용 후 PCAT 영향 시 단말 재부팅 필요 (`reference_pcat_data_profile.md` 참조)

## WCDMA 강제 캠프

- `adb shell cmd phone set-allowed-network-types-for-users -s 0 17284`
  - bitmask 17284 = UMTS | HSPA 조합
- PCAT NV 10 직접 쓰기는 프레임워크 RIL overwrite 로 무력 (Android 12+ `allowed_network_types_for_reasons` 가 source of truth)
- SKT 미인증 SIM = LTE lock 으로 절대 사용 금지 (`reference_wcdma_test_sim.md`)
- KT 미인증 USIM 만 WCDMA 캠프 가능

## Ground truth 수집 경로 (§4.2 3-way)

| 출처 | 도구 / 명령 | 비고 |
|---|---|---|
| **OTA (UE side)** | QXDM 0x713A `UMTS UE OTA Message` | `LOCATION_UPDATE_REJECT` / `GMM_ATTACH_REJECT` / `SM_ACTIVATE_PDP_CONTEXT_REJECT` cause 추출 |
| **QMI** | QXDM 0x1544 `QMI_MCS_QCSI_PKT` | `wds_start_network_interface` 응답 `verbose.call_end_reason` 추출 |
| **Debug screen** | UI dump / 스크린샷 / `uiautomator dump` | MM Cause / GMM Cause / SM Cause 필드 캡처 |
| **logcat (보강)** | `adb logcat -d` + grep | broad capture: `setEsmCause`, `EsmCause`, `SM Cause`, `sm cause`, `cause:27`, `call_end_reason`, `0x1544`, `0x713A` (TC-09 보강용, PASS 단독 근거 아님) |

## Reject popup 관찰 경로

- Reject 수신 직후 단말 화면 popup
- 예시 문구: "가입자 인증에 실패하였습니다. 휴대폰 전원을 껐다 켠 후에도 문제가 지속되면 고객센터(1599-0011)에 문의해 주세요. (3)"
- popup의 cause number와 Debug Screen 값 일치 여부 확인 (TC-08)

## 자주 쓰는 보조 명령

- 단말 reboot: `adb reboot` — APN profile 적용 / PCAT 반영 후 권장
- Airplane on/off: `adb shell cmd connectivity airplane-mode enable` / `disable` (frameworks 변경 가능성 있어 단말 UI 토글이 가장 확실)
- USIM 제거 / 재삽입: 물리 동작 (수기)
- UI dump: `adb shell uiautomator dump /sdcard/dump.xml && adb pull /sdcard/dump.xml`
