# TC Patterns — 단말·앱별 구체 패턴

CLAUDE.md §3.4가 본 문서를 참조. 횡단 원칙은 CLAUDE.md, 본 문서는 구체 패턴·reference만.

## 1. 단말 viewport 패턴

### 1.1 스타일폴더 2 (AT-M140, 480×800)
- 단일 swipe로 안 닿는 항목은 **double-swipe**
- 시스템 오버레이가 selector 가리는 경우 있음
- 긴 메뉴는 세션 확장 스크롤로 분할 탐색

### 1.2 AT-M150
- Z0xxxU 빌드 라인 (Z0409U / Z0518U / Z0520U 등)

### 1.3 ODIN2
- 광주 빌드 라인 (Z0513U_Daily / Z0520U_Daily 등)

### 1.4 THOR2 / THOR2_J
- 일본향 라인 (RY07260302M / MY01260300 등)

## 2. DebugScreen 진입·파싱 (ODIN2 계열)

1. 진입: `adb shell am start -n com.android.phone/.settings.DebugScreen`
2. UI dump: `adb shell uiautomator dump /sdcard/dump.xml && adb pull /sdcard/dump.xml`
3. ground-truth 대조: ServiceState / IMS 등록 / +CGCONTRDP 결과와 dump 텍스트 비교
4. WCDMA에서 layout 자체 누락 가능 (BTS18697) — IMS PDN/P-CSCF/MMTEL은 별도 명령으로도 활성 확인

## 3. SIM 선택 reference

| carrier | LTE | WCDMA | 비고 |
|---|---|---|---|
| SKT 미인증 | 캠프 | **불가** (LTE lock) | WCDMA 검증 SIM 아님 |
| KT 미인증 | 캠프 | 캠프 | **WCDMA 검증 SIM** |
| LGU+ | 별도 확인 | 별도 확인 | — |

ODIN2 기준. 단말 라인별 차이는 추후 측정 시 본 표 갱신.

## 4. PCAT data profile
- profile 추가만으로는 `+CGDCONT`에 미반영
- **재부팅 후** 확인

## 5. USB composition persist 검증 (히든메뉴)
- 단말별 function 매핑 그룹화 (`acm` / `serial_cdev` 등)
- Grep 쿼리 표준 + persist 키 확인
- 재부팅 후 매핑 유지 = PASS 조건

## 6. QC AP 로그 (재부팅 무손실)
- 도구: `scripts/qc_ap_log_capture.py` / `QC_AP_Log_Capture.bat`
- `getprop ro.boot.boot_id` 또는 `/proc/sys/kernel/random/boot_id`로 USB 글리치 vs 실재부팅 구분
- 누적 위치: `logs/` (장기), `output/QC_AP log/` (1회성)

## 7. 개선 훅
신규 단말·SIM·viewport·진단 절차 발견 시 CLAUDE.md §8에 1줄 기록 + 본 문서 갱신.
