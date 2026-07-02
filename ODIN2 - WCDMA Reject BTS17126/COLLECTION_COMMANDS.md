# COLLECTION_COMMANDS — ODIN2 WCDMA Reject (BTS-17126)

다음 세션 실기 검증 시 즉시 복사·붙여넣기 사용 가능한 수집 명령 초안. 본 사이클 `adb shell hang` 경험 반영 — Start-Process 격리 사용 권장.

---

## 0. 사전 sanity

```powershell
$adb = "C:\Users\momen\AppData\Local\Android\Sdk\platform-tools\adb.exe"

# 0.1 단말 연결 확인
& $adb devices -l

# 0.2 adb shell 응답 sanity (hang 여부 확인)
& $adb shell echo "alive"
# → "alive" 즉시 출력되어야 정상. 응답 없으면 QXDM 도구 닫고 재시도.

# 0.3 단말 측 logcat daemon sanity
& $adb logcat -d -t 10
# → 최근 10줄 출력되면 정상.
```

**adb shell hang 회복 절차** (본 사이클 발생):
1. QXDM 도구 / QCAT 종료
2. `& $adb kill-server; & $adb start-server`
3. 단말 화면 unlock 상태 유지
4. `adb shell echo alive` 재시도

---

## 1. 환경 상태 캡처 (Phase 1 진입 직전)

```powershell
$adb = "C:\Users\momen\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$dir = "C:\Users\momen\Projects\tc-runner\doc\BTS17126"

# 1.1 build / SIM / network state
$p = Start-Process -FilePath $adb -ArgumentList @('shell','getprop') `
     -RedirectStandardOutput "$dir\getprop_before.txt" -NoNewWindow -PassThru -Wait
"getprop_before exit=$($p.ExitCode) size=$((Get-Item "$dir\getprop_before.txt").Length)"

# 1.2 telephony registry
Start-Process -FilePath $adb -ArgumentList @('shell','dumpsys','telephony.registry') `
     -RedirectStandardOutput "$dir\dumpsys_telephony_before.txt" -NoNewWindow -Wait

# 1.3 connectivity
Start-Process -FilePath $adb -ArgumentList @('shell','dumpsys','connectivity') `
     -RedirectStandardOutput "$dir\dumpsys_connectivity_before.txt" -NoNewWindow -Wait

# 1.4 default APN
Start-Process -FilePath $adb -ArgumentList @('shell','content','query','--uri','content://telephony/carriers/preferapn') `
     -RedirectStandardOutput "$dir\preferapn_before.txt" -NoNewWindow -Wait

# 1.5 allowed network types (RAT)
Start-Process -FilePath $adb -ArgumentList @('shell','cmd','phone','get-allowed-network-types-for-users') `
     -RedirectStandardOutput "$dir\allowed_rat_before.txt" -NoNewWindow -Wait

# 1.6 airplane mode state
Start-Process -FilePath $adb -ArgumentList @('shell','settings','get','global','airplane_mode_on') `
     -RedirectStandardOutput "$dir\airplane_before.txt" -NoNewWindow -Wait
```

**확인 항목**:
- `getprop_before.txt` → `ro.build.display.id` (정확한 0527 Daily ID)
- `dumpsys_telephony_before.txt` → `mServiceState` / `mPreciseDataConnectionState` / `mDataConnectionState`
- `preferapn_before.txt` → 현재 default APN = `test.com` 확인
- `allowed_rat_before.txt` → WCDMA 캠프 강제 적용 확인 (17284 = UMTS|HSPA)
- `airplane_before.txt` → 0 = OFF, 1 = ON

---

## 2. WCDMA 강제 캠프 (필요 시)

```powershell
# 2.1 WCDMA only 캠프 강제 (UMTS|HSPA bitmask = 17284)
Start-Process -FilePath $adb -ArgumentList @('shell','cmd','phone','set-allowed-network-types-for-users','-s','0','17284') `
     -NoNewWindow -Wait

# 2.2 확인
Start-Process -FilePath $adb -ArgumentList @('shell','cmd','phone','get-allowed-network-types-for-users') `
     -RedirectStandardOutput "$dir\allowed_rat_after.txt" -NoNewWindow -Wait
```

**NOTE**: PCAT NV 10 직접 쓰기는 framework RIL overwrite 로 무력. Android 12+ 는 `allowed_network_types_for_reasons` 가 source of truth (메모리 기록).

---

## 3. TC-04 SM Reject 트리거 + 캡처

### 3.1 트리거 (사용자 수기 / 또는 명령)

```text
1. 잘못된 APN (`test.com`) default 선택 확인
2. WCDMA 캠프 명령 적용 (Section 2)
3. 비행기 모드 OFF (단말 UI)
   → PDP Context Activation 자동 시도
   → SM_ACTIVATE_PDP_CONTEXT_REJECT cause=27 수신
4. 약 30~60초 PDP retry 동안 QXDM 로그 시간 마킹
5. Settings → Debug Screen info 진입
```

### 3.2 캡처 명령 (Debug Screen 화면 노출 직후)

```powershell
# 3.2.1 logcat all-buffer dump (반드시 본 시점에 — buffer가 wrap 되기 전)
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logcat_all = "$dir\logcat_all_TC04_$ts.txt"
Start-Process -FilePath $adb -ArgumentList @('logcat','-d','-b','all','-v','threadtime') `
     -RedirectStandardOutput $logcat_all -NoNewWindow -Wait
"size=$((Get-Item $logcat_all).Length)"

# 3.2.2 Debug Screen UI dump (현재 화면)
Start-Process -FilePath $adb -ArgumentList @('shell','uiautomator','dump','/sdcard/ui_dump_TC04.xml') `
     -NoNewWindow -Wait
Start-Process -FilePath $adb -ArgumentList @('pull','/sdcard/ui_dump_TC04.xml',"$dir\ui_dump_TC04_$ts.xml") `
     -NoNewWindow -Wait

# 3.2.3 dumpsys telephony.registry (precise state)
Start-Process -FilePath $adb -ArgumentList @('shell','dumpsys','telephony.registry') `
     -RedirectStandardOutput "$dir\dumpsys_telephony_TC04_$ts.txt" -NoNewWindow -Wait

# 3.2.4 스크린샷 (보강)
Start-Process -FilePath $adb -ArgumentList @('exec-out','screencap','-p') `
     -RedirectStandardOutput "$dir\debugscreen_TC04_$ts.png" -NoNewWindow -Wait
```

**3-way 추출**:
- OTA: QXDM HDF → QCAT 0x713A filter → `SM_ACTIVATE_PDP_CONTEXT_REJECT` → `sm_cause_val=?`
- QMI: QXDM HDF → QCAT 0x1544 filter → `wds_start_network_interface` resp → `call_end_reason=?` / `verbose.call_end_reason=?`
- Debug Screen: `ui_dump_TC04_*.xml` → SM Cause 텍스트 / `debugscreen_TC04_*.png` 시각 확인

---

## 4. TC-09 Resume Persistence (TC-04 동반)

```powershell
# T0: TC-04 직후 캡처 = 위 3.2 결과 사용

# 4.1 Debug Screen 백그라운드 전환 (Home key)
Start-Process -FilePath $adb -ArgumentList @('shell','input','keyevent','KEYCODE_HOME') `
     -NoNewWindow -Wait

# 4.2 30초 대기 후 Debug Screen 재진입
Start-Sleep -Seconds 30
Start-Process -FilePath $adb -ArgumentList @('shell','am','start','-n','com.android.phone/.settings.DebugScreen') `
     -NoNewWindow -Wait
Start-Sleep -Seconds 2

# T1: 재진입 UI dump
Start-Process -FilePath $adb -ArgumentList @('shell','uiautomator','dump','/sdcard/ui_dump_TC09_T1.xml') `
     -NoNewWindow -Wait
Start-Process -FilePath $adb -ArgumentList @('pull','/sdcard/ui_dump_TC09_T1.xml',"$dir\ui_dump_TC09_T1_$ts.xml") `
     -NoNewWindow -Wait

# 4.3 강제 종료 (com.android.phone process) → 재실행
Start-Process -FilePath $adb -ArgumentList @('shell','am','force-stop','com.android.phone') `
     -NoNewWindow -Wait
Start-Sleep -Seconds 3
Start-Process -FilePath $adb -ArgumentList @('shell','am','start','-n','com.android.phone/.settings.DebugScreen') `
     -NoNewWindow -Wait
Start-Sleep -Seconds 2

# T2: 재실행 후 UI dump
Start-Process -FilePath $adb -ArgumentList @('shell','uiautomator','dump','/sdcard/ui_dump_TC09_T2.xml') `
     -NoNewWindow -Wait
Start-Process -FilePath $adb -ArgumentList @('pull','/sdcard/ui_dump_TC09_T2.xml',"$dir\ui_dump_TC09_T2_$ts.xml") `
     -NoNewWindow -Wait
```

**PASS 검증**: `ui_dump_TC04_*.xml` (T0) = `ui_dump_TC09_T1_*.xml` (T1) = `ui_dump_TC09_T2_*.xml` (T2) — SM Cause 필드 값 모두 동일.

---

## 5. logcat broad grep (TC-04 / TC-09 보강)

```powershell
$pattern = 'setEsmCause|EsmCause|SmCause|SM Cause|sm_cause|cause:?\s*27|cause\s*=\s*27|SM_ACTIVATE_PDP|WDS_CER_UNKNOWN_APN|Missing or unknown APN|MISSING_UNKNOWN_APN|call_end_reason|verbose_call_end|0x1544|0x713A|UNKNOWN_APN|MM Cause|GMM Cause|gmm_cause|rej_cause|DebugScreen'
Select-String -Path "$dir\logcat_all_TC04_*.txt" -Pattern $pattern -CaseSensitive:$false | `
     Select-Object Filename, LineNumber, Line | `
     Format-Table -AutoSize | Out-File "$dir\logcat_grep_TC04_$ts.txt"
"grep size=$((Get-Item "$dir\logcat_grep_TC04_$ts.txt").Length)"
```

**NOTE (사용자 명시)**: logcat 패턴은 SUPPORT 근거. PASS blocker 아님. 어떤 라인이 호출됐는지 사후 확인용.

---

## 6. TC-05 Persistence 트리거 / 캡처

```text
T0: TC-04 와 동일 환경 → SM Cause 확인 (위 3.2 결과 사용)

T1 (시간 경과 retain): 
  Start-Sleep -Seconds 180   # 3분 대기
  (위 3.2.2 UI dump 재실행, suffix _TC05_T1_)
  → 비교: T0 SM Cause == T1 SM Cause (retain 확인)

T2 (USIM 제거 또는 Airplane ON):
  사용자 수기: USIM 제거 또는 Airplane mode ON
  Start-Sleep -Seconds 10
  (UI dump 재실행, suffix _TC05_T2_)
  → 비교: T2 SM Cause clear 허용

T3 (정상 USIM 재삽입 또는 Airplane OFF + 정상 등록):
  사용자 수기: USIM 재삽입 또는 Airplane OFF
  Start-Sleep -Seconds 60   # 등록 대기
  (UI dump 재실행, suffix _TC05_T3_)
  → 비교: T3 SM Cause clear 확인
```

---

## 7. TC-01 / TC-02 트리거 (회귀)

### TC-01 (CS Reject)
```text
1. WCDMA only 캠프 유지
2. Airplane 토글로 reset → 정상 USIM 등록 후 CS Reject 환경 유도
   (KT 미인증 SIM 환경에서 CS LU Reject 자연 발생 가능)
3. QXDM 0x713A → LOCATION_UPDATE_REJECT rej_cause_val 확인
4. Debug Screen 진입 → MM Cause 캡처 (`ui_dump_TC01_`)
```

### TC-02 (PS Reject)
```text
1. WCDMA only 캠프 유지
2. Airplane 토글로 reset → 정상 APN 으로 변경 → GPRS/PS Attach 시도
3. QXDM 0x713A → GMM_ATTACH_REJECT gmm_cause_val 확인
4. Debug Screen 진입 → GMM Cause 캡처 (`ui_dump_TC02_`)
```

---

## 8. QXDM HDF 후처리 (사용자 측 QCAT 작업)

```text
QCAT 도구로 HDF 열기 → filter 적용

1. 0x713A UMTS UE OTA Message
   - LOCATION_UPDATE_REJECT (CS) → rej_cause_val
   - GMM_ATTACH_REJECT (PS) → gmm_cause_val  
   - SM_ACTIVATE_PDP_CONTEXT_REJECT (SM) → sm_cause_val ★ TC-04 핵심

2. 0x1544 QMI_MCS_QCSI_PKT
   - wds_start_network_interface response
     → result_code (QMI_RESULT_FAILURE)
     → error_code (QMI_ERR_CALL_FAILED)
     → call_end_reason (WDS_CER_UNKNOWN_APN)
     → verbose.call_end_reason (= 27) ★ TC-04 핵심

3. 시간 마킹 = 본 cycle 트리거 시각 ± 60초 윈도우
```

추출값을 `RESULT_<날짜>.md` 의 evidence 표에 채워 넣음.

---

## 9. 디렉토리 구조 (캡처 후 예시)

```
doc/BTS17126/
├── Test_<날짜>.hdf                    # QXDM HDF (사용자 측 캡처)
├── getprop_before.txt                  # 환경 sanity
├── dumpsys_telephony_before.txt
├── preferapn_before.txt
├── allowed_rat_before.txt
├── allowed_rat_after.txt
├── airplane_before.txt
├── logcat_all_TC04_<ts>.txt           # TC-04 트리거 logcat all-buffer
├── ui_dump_TC04_<ts>.xml              # TC-04 Debug Screen T0
├── debugscreen_TC04_<ts>.png          # TC-04 스크린샷
├── dumpsys_telephony_TC04_<ts>.txt
├── ui_dump_TC09_T1_<ts>.xml           # TC-09 resume T1
├── ui_dump_TC09_T2_<ts>.xml           # TC-09 force-stop T2
├── ui_dump_TC05_T1_<ts>.xml           # TC-05 시간 경과 T1
├── ui_dump_TC05_T2_<ts>.xml           # TC-05 USIM/Airplane T2
├── ui_dump_TC05_T3_<ts>.xml           # TC-05 정상 등록 T3
├── ui_dump_TC01_<ts>.xml              # TC-01 CS Reject
├── ui_dump_TC02_<ts>.xml              # TC-02 PS Reject
├── logcat_grep_TC04_<ts>.txt          # broad grep 결과
└── ...
```

---

## 10. 안전 / 제약

- 본 명령은 **비파괴 read-only + 단말 측 RAT 강제만** 포함. APN 적용 / USIM 변경 / flash 는 사용자 수기.
- QXDM HDF 캡처는 사용자 측 QXDM 도구 (Claude 트리거 없음).
- WCDMA 캠프 명령 (`set-allowed-network-types-for-users`) 은 단말 RAT 변경이므로 사용자 명시 후 적용.
- adb shell 명령은 hang 가능성 있음 → 본 사이클 경험 반영, Start-Process 격리 사용 권장.
- 모든 캡처 산출은 `doc/BTS17126/` 아래 누적 (`<단말명> - <앱명>/catalog/` 가 아님 — QXDM 도구 캡처 영역이므로 doc 경로 유지).
