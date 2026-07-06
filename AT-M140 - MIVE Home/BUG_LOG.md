# BUG_LOG — AT-M140 (스타일폴더 2) × MIVE Home

## 요약

| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| DATA-002 | Mobile Data / boot consent-gate | OBSERVED | OPEN (제품 ruling 대기) | 데이터 ON 이 재부팅을 못 넘김 — 부팅 시 consent-gate 가 강제 OFF. 정식 요구사항 미정의 | reboot_cycle_verify.sh (--data-mode) | run_20260706_190539 FAIL #1/#3 |

## DATA-002 — 모바일 데이터 ON 재부팅 미유지 (boot consent-gate)

- **기능 영역**: Mobile Data / 부팅 시 데이터 consent (LensConfirmDataDialog)
- **진단 상태**: `OBSERVED` — KDDI 단일 캐리어 × smoke. `CONFIRMED` 은 2캐리어 × 정/역 재현 필요(§4.2)
- **이슈 상태**: `OPEN` — 제품 owner ruling 대기 (버그 vs 정상 판정 미확정)
- **단말**: AT-M140 (alt_thor2), Android 14, build UP1A.231005.007, SIM=KDDI
- **앱**: MIVE Home (com.hnlens.simplemode)
- **요약**: `svc data enable` 로 데이터 ON 후 재부팅하면 부팅 후 `mobile_data=0` 으로 복귀. OFF 는 유지(정상).
- **기대 결과**: — ("데이터 ON 재부팅 유지"(DATA-002)는 리포 내 정식 요구사항으로 **부재**. reboot_cycle_verify.sh 헤더의 저자 관례 ID이며, THOR2-J miveHome TC 시트에도 데이터-유지 TC 없음 — 타 설정(STL-005 터치잠금·VM-003 진동)엔 재부팅-유지 TC 존재)
- **실제 결과** (3-way ground truth 일치):
  - 스크립트 키 `settings global mobile_data`: 1 → 재부팅 → 0
  - telephony: `mIsDataEnabled` true→false, `mDataConnectionState` 2→0
  - 8초 정착본도 리셋 (스크립트 1초 pre-reboot 타이밍 아티팩트 아님)
  - `xt_preboot_mobile_data_enabled` 재부팅에 0→1 반전
- **메커니즘 (by-design consent-gate)**: 부팅 시 `(Odin|Lens)ConfirmDataBootReceiver performOffData` 가 데이터 강제 OFF → `com.android.phone/.LensConfirmDataDialogActivity` consent 팝업 → 사용자 "사용" 재탭 필요. 근거 = `doc/BUG25796_Mobile_Data_sync_issue/BUG_REPORT_25796.md` (ODIN2/AT-M150 "Odin" prefix 동일 프레임워크). AT-M140 은 "Lens" prefix 로 직접 관찰.
- **재현 절차**: `svc data enable` → 정착 → `adb reboot` → boot_completed → `settings get global mobile_data` (=0)
- **증거**: `새 폴더 (2)/files/reboot_cycle_logs/run_20260706_190539/` (results.csv, FAIL_reboot_0001/0003 artifacts) + 본 세션 3-way 격리 테스트 (RESULT_2026-07-06.md)
- **관련 TC / 이슈**: reboot_cycle_verify.sh(--data-mode alternate) · BUG-25796 (post-consent 130s host WWAN AutoConfig, `CONFIRMED`+`SPEC_GAP`, 종결 — 본 관찰(consent 前 teardown)과 별개 단계)
- **정정 이력**: —

### 스크립트 정책 (동결)

reboot_cycle_verify.sh 의 DATA verdict 는 **현행 FAIL 유지**(raw 관찰 신호). `CONSENT_GATE_OBSERVED` 등 해석 계층은 **코드에 미추가** — 제품 owner 가 DATA-002 요구사항을 확정하기 전까지 스크립트가 판정 정책을 선점하지 않는다(미래 실 data-persist regression 을 NOTE 로 삼킬 위험 차단).

**Owner 확인 질문**: 부팅 시 데이터 consent 재요구(데이터 OFF 로 부팅)가
- (a) 의도된 캐리어 정책 → `NOTE` / consent-flow 처리
- (b) 데이터 ON 유지가 요구사항 → `BUG-GAP` (스크립트 FAIL 유지가 정답)
