@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title BUG-5426 APN Monitor

REM ============================================================
REM BUG-5426 PDP context (CGDCONT) monitor
REM
REM 판정 기준: modem AT+CGDCONT? 응답의 +CGDCONT: 라인 개수
REM   - baseline == current → PASS
REM   - current > baseline  → FAIL (BUG5426_REPRO)
REM   - current < baseline  → FAIL (CID_DECREASE)
REM   - AT 질의 자체 실패    → FAIL (AT_*)
REM
REM 사용법:
REM   BUG5426_APN_Monitor.bat             (기본: reboot 20회)
REM   BUG5426_APN_Monitor.bat 10 both     (both 10회)
REM   BUG5426_APN_Monitor.bat 30 emcall   (긴급호 30회)
REM ============================================================

REM ── 인자 ──
set ITERATIONS=20
set SCENARIO=reboot
if not "%~1"=="" set ITERATIONS=%~1
if not "%~2"=="" set SCENARIO=%~2

REM ── 로그 디렉토리 (바탕화면 고정) ──
for /f "delims=" %%D in ('powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"') do set "DESKTOP_PATH=%%D"
set "LOG_DIR=!DESKTOP_PATH!\BUG5426_logs"
set "BOOT_LOG_DIR=!LOG_DIR!\boot_logs"
set "CID_SNAP_DIR=!LOG_DIR!\cid_snapshots"
set "PERSIST_DIR=!LOG_DIR!\persist_logs"
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!"
if not exist "!BOOT_LOG_DIR!" mkdir "!BOOT_LOG_DIR!"
if not exist "!CID_SNAP_DIR!" mkdir "!CID_SNAP_DIR!"

REM ── 타임스탬프 ──
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list 2^>nul') do set "DT=%%I"
set "TIMESTAMP=%DT:~0,8%_%DT:~8,6%"
set "LOG_FILE=!LOG_DIR!\cid_%TIMESTAMP%.csv"

REM ── PS1 경로 탐색 (fallback: 같은 디렉토리 → output\ → ..\output\) ──
set "PS1_PATH="
if exist "%~dp0BUG5426_at_query.ps1" set "PS1_PATH=%~dp0BUG5426_at_query.ps1"
if not defined PS1_PATH if exist "%~dp0output\BUG5426_at_query.ps1" set "PS1_PATH=%~dp0output\BUG5426_at_query.ps1"
if not defined PS1_PATH if exist "%~dp0..\output\BUG5426_at_query.ps1" set "PS1_PATH=%~dp0..\output\BUG5426_at_query.ps1"
if not defined PS1_PATH (
    echo [ERROR] BUG5426_at_query.ps1 not found. Looked in:
    echo   %~dp0BUG5426_at_query.ps1
    echo   %~dp0output\BUG5426_at_query.ps1
    echo   %~dp0..\output\BUG5426_at_query.ps1
    pause
    exit /b 1
)

REM ── 시작 안내 ──
echo ============================================================
echo   BUG-5426 PDP Context Monitor (AT+CGDCONT based)
echo ============================================================
echo.
echo   Scenario   : %SCENARIO%
echo   Iterations : %ITERATIONS%
echo   PS1 helper : !PS1_PATH!
echo.
echo   [사전 설정 확인]
echo     1. logcat persist 로깅 활성화 (persist.logd.logpersistd = logcatd)
echo     2. Qualcomm USB driver 설치 + 모뎀 COM 포트 정상 (teraterm 연결 확인)
echo     3. WWAN AutoConfig 중지 (sc stop WwanSvc)
echo.
echo   [로그 저장 경로]
echo     CSV 결과    : !LOG_FILE!
echo     부팅 로그    : !BOOT_LOG_DIR!\
echo     CID 스냅샷   : !CID_SNAP_DIR!\
echo     persist     : 종료 시 저장 여부 선택
echo.
echo   [종료] Ctrl+C 시 persist 로그 저장 여부 확인 후 종료
echo ============================================================
echo.

REM ── ADB 확인 ──
where adb >nul 2>&1
if errorlevel 1 (
    if exist "%~dp0adb.exe" (
        set "PATH=%~dp0;%PATH%"
        echo [INFO] Using adb.exe from same folder.
    ) else (
        echo [ERROR] adb not found.
        echo.
        echo   Download platform-tools from:
        echo   https://developer.android.com/tools/releases/platform-tools
        echo   Place adb.exe next to this bat file, or add to PATH.
        echo.
        pause
        exit /b 1
    )
)
adb version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] adb failed to run
    pause
    exit /b 1
)

REM ── 단말 연결 확인 ──
echo [%time%] Checking device connection...
set DEVICE_FOUND=0
for /f "tokens=1" %%d in ('adb devices 2^>nul ^| %SystemRoot%\System32\findstr.exe /r "device$"') do (
    set "DEVICE_ID=%%d"
    set DEVICE_FOUND=1
)
if !DEVICE_FOUND! EQU 0 (
    echo [ERROR] No device connected.
    pause
    exit /b 1
)
echo [%time%] Device: !DEVICE_ID!

for /f "delims=" %%a in ('adb shell getprop ro.product.model 2^>nul') do set "MODEL=%%a"
for /f "delims=" %%a in ('adb shell getprop ro.build.display.id 2^>nul') do set "BUILD=%%a"
echo [%time%] Model: !MODEL!  Build: !BUILD!

REM ── logpersistd 활성화 확인 ──
for /f "delims=" %%a in ('adb shell getprop persist.logd.logpersistd 2^>nul') do set "LOGPD=%%a"
set "LOGPD=!LOGPD: =!"
set "LOGPD=!LOGPD:	=!"
if /i not "!LOGPD!"=="logcatd" (
    echo.
    echo [ERROR] persist.logd.logpersistd = "!LOGPD!"  ^(expected: logcatd^)
    echo   persist 로그가 수집되지 않는 상태입니다. 다음 명령으로 활성화 후 재실행하세요:
    echo     adb shell setprop persist.logd.logpersistd logcatd
    echo     adb reboot
    echo.
    pause
    exit /b 1
)
echo [%time%] logpersistd: !LOGPD! OK

REM ── Qualcomm Modem 존재 여부 사전 체크 ──
powershell -NoProfile -Command "if (Get-CimInstance -ClassName Win32_POTSModem -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Qualcomm.*Modem' }) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Qualcomm Modem not found. Check Qualcomm USB driver, USB cable, port-bridge service, and device USB enumeration.
    pause
    exit /b 1
)
echo [%time%] Qualcomm Modem OK

REM ── WWAN AutoConfig 중지 ──
sc stop WwanSvc >nul 2>&1

REM ── SIM 정보 (참고용, 판정에는 미사용) ──
for /f "delims=" %%a in ('adb shell getprop gsm.sim.operator.numeric 2^>nul') do set "SIM_MNC=%%a"
set "SIM_MNC=!SIM_MNC: =!"
set "SIM_MNC=!SIM_MNC:~0,5!"
for /f "delims=" %%a in ('adb shell getprop gsm.sim.operator.alpha 2^>nul') do set "SIM_OP=%%a"
if "!SIM_MNC!"=="" set "SIM_MNC=unknown"
echo [%time%] SIM: !SIM_OP! [!SIM_MNC!]  (info only)
echo.

REM ── Baseline 획득 (비행기 ON 상태에서, 2회 연속 측정) ──
call :AT_BASELINE
if errorlevel 1 (
    echo.
    echo [ERROR] baseline acquisition failed
    pause
    exit /b 1
)

REM ── 시작 확인 ──
echo.
echo ============================================================
echo  Ready. Baseline = !BL! CIDs (via !BASE_COM!)
echo  Press Enter to start. Cancel: Ctrl+C
echo ============================================================
pause >nul

REM ── CSV 헤더 ──
echo iteration,scenario,result,fail_reason,detail,cid_count,baseline,radio_on,reg_home,com_port > "!LOG_FILE!"

REM ── 메인 루프 ──
set PC=0
set FC=0
set AT_STREAK=0
set ABORTED=0

for /l %%i in (1,1,%ITERATIONS%) do (
    if !AT_STREAK! GEQ 3 (
        echo.
        echo [ABORT] 3 consecutive AT failures detected. Stopping script.
        set ABORTED=1
        goto :REPORT
    )
    if "%SCENARIO%"=="reboot" (
        call :REBOOT %%i
    ) else if "%SCENARIO%"=="emcall" (
        call :EMCALL %%i
    ) else (
        set /a "M=%%i %% 2"
        if !M! EQU 1 ( call :REBOOT %%i ) else ( call :EMCALL %%i )
    )
    echo   --- [%%i/%ITERATIONS%] PASS=!PC! FAIL=!FC! AT_STREAK=!AT_STREAK! ---
)

goto :REPORT

REM ============================================================
REM :RUN_PS1 <outfile>
REM   → sets CUR_CIDS, CUR_COM, AT_FAIL_REASON (empty on success)
REM ============================================================
:RUN_PS1
set "RP_OUT=%~1"
set "CUR_CIDS=-1"
set "CUR_COM=NONE"
set "AT_FAIL_REASON=UNKNOWN"
set "PS1_SUM=%TEMP%\bug5426_ps1_sum.tmp"
del "!PS1_SUM!" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "!PS1_PATH!" -OutFile "!RP_OUT!" -SummaryFile "!PS1_SUM!" >nul 2>&1
set "PS1_LAST_LINE="
if exist "!PS1_SUM!" for /f "usebackq delims=" %%L in ("!PS1_SUM!") do set "PS1_LAST_LINE=%%L"
if not defined PS1_LAST_LINE (
    set "AT_FAIL_REASON=EMPTY_RESP"
    goto :eof
)
for /f "tokens=1-6 delims== " %%A in ("!PS1_LAST_LINE!") do (
    set "CUR_COM=%%B"
    set "CUR_CIDS=%%D"
    if /i "%%E"=="FAIL" set "AT_FAIL_REASON=%%F"
)
if !CUR_CIDS! GEQ 0 set "AT_FAIL_REASON="
goto :eof

REM ============================================================
REM :AT_BASELINE
REM   비행기 ON 상태로 맞춘 뒤 2회 연속 일치할 때만 BL 확정 (최대 2 round)
REM ============================================================
:AT_BASELINE
echo [%time%] Putting device into airplane-ON state for baseline...
call :SET_AIRPLANE_ON
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul

set BASE_ROUND=0
:AT_BASELINE_LOOP
set /a BASE_ROUND+=1
if !BASE_ROUND! GTR 2 (
    echo [ERROR] baseline did not stabilize after 2 rounds ^(4 measurements^)
    exit /b 1
)
echo [%time%] Baseline round !BASE_ROUND! ...

call :RUN_PS1 "!CID_SNAP_DIR!\000_BASELINE_r!BASE_ROUND!_a_%TIMESTAMP%.txt"
set "BASE_CID_A=!CUR_CIDS!"
set "BASE_FR_A=!AT_FAIL_REASON!"
set "BASE_COM=!CUR_COM!"
if !BASE_CID_A! LEQ 0 (
    echo [WARN] baseline round !BASE_ROUND! first read failed: !BASE_FR_A!
    %SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
    goto :AT_BASELINE_LOOP
)

%SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul

call :RUN_PS1 "!CID_SNAP_DIR!\000_BASELINE_r!BASE_ROUND!_b_%TIMESTAMP%.txt"
set "BASE_CID_B=!CUR_CIDS!"
set "BASE_FR_B=!AT_FAIL_REASON!"
if !BASE_CID_B! LEQ 0 (
    echo [WARN] baseline round !BASE_ROUND! second read failed: !BASE_FR_B!
    %SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
    goto :AT_BASELINE_LOOP
)

if !BASE_CID_A! NEQ !BASE_CID_B! (
    echo [WARN] baseline mismatch round !BASE_ROUND!: !BASE_CID_A! vs !BASE_CID_B!
    %SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
    goto :AT_BASELINE_LOOP
)

set BL=!BASE_CID_A!
copy /y "!CID_SNAP_DIR!\000_BASELINE_r!BASE_ROUND!_b_%TIMESTAMP%.txt" "!CID_SNAP_DIR!\latest_baseline.txt" >nul 2>&1
echo [%time%] Baseline confirmed: !BL! CIDs ^(round !BASE_ROUND!, com=!BASE_COM!^)
exit /b 0

REM ============================================================
REM :AT_SNAPSHOT <iter> <scenario>
REM   phase = postcall (fixed). Internal retry up to 3 times.
REM   → sets CUR_CIDS, CUR_COM, AT_FAIL_REASON
REM ============================================================
:AT_SNAPSHOT
set "SNAP_ITER=%1"
set "SNAP_SCEN=%2"
set "SNAP_PHASE=postcall"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list 2^>nul') do set "SNAP_DT=%%I"
set "SNAP_TS=!SNAP_DT:~0,8!_!SNAP_DT:~8,6!"

set "IT3=000!SNAP_ITER!"
set "IT3=!IT3:~-3!"

set "SNAP_FILE=!CID_SNAP_DIR!\!IT3!_!SNAP_SCEN!_!SNAP_PHASE!_!SNAP_TS!.txt"

set SNAP_ATTEMPT=0
:AT_SNAPSHOT_RETRY
set /a SNAP_ATTEMPT+=1
call :RUN_PS1 "!SNAP_FILE!"
if !CUR_CIDS! GEQ 0 (
    echo [%time%] Snapshot OK ^(attempt !SNAP_ATTEMPT!^): cid=!CUR_CIDS! com=!CUR_COM!
    goto :eof
)
echo [%time%] Snapshot attempt !SNAP_ATTEMPT! failed: !AT_FAIL_REASON!
if !SNAP_ATTEMPT! GEQ 3 goto :eof
%SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
goto :AT_SNAPSHOT_RETRY

REM ============================================================
REM :WAIT_COM_PORT
REM   reboot 후 Qualcomm Android Modem 재등장 대기. 최대 60초, 2초 간격
REM   (AT 응답 가능 여부는 확인 안 함 → 최종 확인은 AT_SNAPSHOT 재시도)
REM ============================================================
:WAIT_COM_PORT
echo [%time%] Waiting for Qualcomm Android Modem re-enumeration (up to 60s)...
set WAIT_TRIES=0
:WAIT_COM_PORT_LOOP
set /a WAIT_TRIES+=1
if !WAIT_TRIES! GTR 30 (
    echo [%time%] WARNING: Modem port did not reappear within 60s
    exit /b 1
)
powershell -NoProfile -Command "if (Get-CimInstance -ClassName Win32_POTSModem -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Qualcomm.*Modem' }) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    %SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
    goto :WAIT_COM_PORT_LOOP
)
echo [%time%] Modem port detected (tries=!WAIT_TRIES!)
exit /b 0

REM ============================================================
REM :SET_AIRPLANE_ON
REM ============================================================
:SET_AIRPLANE_ON
adb shell "su 0 settings put global airplane_mode_on 1" >nul 2>&1
adb shell "su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true" >nul 2>&1
goto :eof

REM ============================================================
REM :WRITE_CSV
REM   expects: W_ITER W_SCEN W_RESULT W_REASON W_DETAIL W_CIDS W_COM W_RO W_RH
REM   updates: PC/FC, AT_STREAK
REM ============================================================
:WRITE_CSV
echo !W_ITER!,!W_SCEN!,!W_RESULT!,!W_REASON!,"!W_DETAIL!",!W_CIDS!,!BL!,!W_RO!,!W_RH!,!W_COM! >> "!LOG_FILE!"
if /i "!W_RESULT!"=="PASS" (
    set /a PC+=1
    set AT_STREAK=0
) else (
    set /a FC+=1
    set "W_PREFIX=!W_REASON:~0,3!"
    if /i "!W_PREFIX!"=="AT_" (
        set /a AT_STREAK+=1
    ) else (
        set AT_STREAK=0
    )
)
goto :eof

REM ============================================================
REM :JUDGE_CID <iter> <scen> <radio_on> <reg_home>
REM   CUR_CIDS / CUR_COM / AT_FAIL_REASON 기반 PASS/FAIL 판정 후 CSV 기록
REM ============================================================
:JUDGE_CID
set "W_ITER=%1"
set "W_SCEN=%2"
set "W_RO=%3"
set "W_RH=%4"
set "W_CIDS=!CUR_CIDS!"
set "W_COM=!CUR_COM!"

if !CUR_CIDS! EQU -1 (
    set "W_RESULT=FAIL"
    set "W_REASON=AT_!AT_FAIL_REASON!"
    set "W_DETAIL=snapshot_failed reason=!AT_FAIL_REASON!"
    goto :JUDGE_CID_WRITE
)
if !CUR_CIDS! GTR !BL! (
    set "W_RESULT=FAIL"
    set "W_REASON=BUG5426_REPRO"
    set "W_DETAIL=cid=!CUR_CIDS!^(exp=!BL!^)"
    goto :JUDGE_CID_WRITE
)
if !CUR_CIDS! LSS !BL! (
    set "W_RESULT=FAIL"
    set "W_REASON=CID_DECREASE"
    set "W_DETAIL=cid=!CUR_CIDS!^(exp=!BL!^)"
    goto :JUDGE_CID_WRITE
)
set "W_RESULT=PASS"
set "W_REASON=OK"
set "W_DETAIL=cid=!CUR_CIDS!^(exp=!BL!^)"
:JUDGE_CID_WRITE
echo [%time%] !W_RESULT! reason=!W_REASON! cid=!W_CIDS! bl=!BL! com=!W_COM!
call :WRITE_CSV
goto :eof

REM ============================================================
REM :REBOOT <iter>
REM ============================================================
:REBOOT
set "R_ITER=%1"
echo.
echo ==== [#!R_ITER!] REBOOT ====

echo [%time%] Airplane ON...
call :SET_AIRPLANE_ON
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
for /f "delims=" %%a in ('adb shell "settings get global airplane_mode_on" 2^>nul') do set "AP=%%a"
echo [%time%] airplane=!AP!

echo [%time%] logcat clear + reboot...
adb shell "logcat -c" >nul 2>&1
adb shell "su 0 reboot" >nul 2>&1

echo [%time%] Waiting for ADB reconnect...
%SystemRoot%\System32\timeout.exe /t 15 /nobreak >nul
set RC=0
for /l %%w in (1,1,25) do (
    if !RC! EQU 0 (
        for /f "delims=" %%r in ('adb shell "getprop sys.boot_completed" 2^>nul') do (
            if "%%r"=="1" set RC=1
        )
        if !RC! EQU 0 %SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
    )
)
if !RC! EQU 0 (
    echo [%time%] Reconnect FAILED
    set "W_ITER=!R_ITER!"
    set "W_SCEN=REBOOT"
    set "W_RESULT=FAIL"
    set "W_REASON=ADB_TIMEOUT"
    set "W_DETAIL=ADB did not reconnect after reboot"
    set "W_CIDS=-1"
    set "W_COM=NONE"
    set "W_RO=0"
    set "W_RH=0"
    call :WRITE_CSV
    goto :eof
)
echo [%time%] Reconnected OK

REM ── Qualcomm Android Modem 재등장 대기 ──
call :WAIT_COM_PORT
if errorlevel 1 (
    set "W_ITER=!R_ITER!"
    set "W_SCEN=REBOOT"
    set "W_RESULT=FAIL"
    set "W_REASON=AT_NO_PORT"
    set "W_DETAIL=Modem COM port did not reappear within 60s"
    set "W_CIDS=-1"
    set "W_COM=NONE"
    set "W_RO=0"
    set "W_RH=0"
    call :WRITE_CSV
    goto :eof
)

REM ── boot 로그 덤프 ──
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list 2^>nul') do set "BTS=%%I"
set "BT_TS=!BTS:~0,8!_!BTS:~8,6!"
echo [%time%] Dumping boot logs...
adb logcat -b radio -b main -d > "!BOOT_LOG_DIR!\!R_ITER!_REBOOT_!BT_TS!_radio_main.txt" 2>&1
adb logcat -b radio -L -d > "!BOOT_LOG_DIR!\!R_ITER!_REBOOT_!BT_TS!_last_boot_radio.txt" 2>&1

REM ── CarrierConfig 로드 대기 ──
%SystemRoot%\System32\timeout.exe /t 10 /nobreak >nul

REM ── 비행기 유지 상태에서 긴급호 ──
set "ITER_NUM=!R_ITER!"
call :DO_EMCALL
if "!EMCALL_RESULT!"=="FAIL" (
    set "W_ITER=!R_ITER!"
    set "W_SCEN=REBOOT"
    set "W_RESULT=FAIL"
    set "W_REASON=EMCALL_FAIL"
    set "W_DETAIL=emergency call setup failed"
    set "W_CIDS=-1"
    set "W_COM=NONE"
    set "W_RO=0"
    set "W_RH=0"
    call :WRITE_CSV
    adb shell "su 0 settings put global airplane_mode_on 0" >nul 2>&1
    adb shell "su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false" >nul 2>&1
    %SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
    call :SET_AIRPLANE_ON
    %SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
    goto :eof
)

REM ── AT snapshot (비행기 ON 상태에서, baseline 조건과 일치) ──
call :AT_SNAPSHOT !R_ITER! REBOOT

REM ── radio_on / reg_home (참고) ──
adb shell "logcat -d -s RILJ" > "%TEMP%\cid_rilj.txt" 2>&1
set RO=0
set RH=0
for /f %%n in ('type "%TEMP%\cid_rilj.txt" ^| %SystemRoot%\System32\find.exe /c "RADIO_POWER on = true"') do set RO=%%n
for /f %%n in ('type "%TEMP%\cid_rilj.txt" ^| %SystemRoot%\System32\find.exe /c "REG_HOME"') do set RH=%%n

REM ── 판정 및 CSV 기록 ──
call :JUDGE_CID !R_ITER! REBOOT !RO! !RH!

REM ── 다음 iteration 위해 비행기 다시 ON ──
call :SET_AIRPLANE_ON
%SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
goto :eof

REM ============================================================
REM :DO_EMCALL   (비행기 ON 상태 가정, 긴급호 수행)
REM ============================================================
:DO_EMCALL
set "EMCALL_RESULT=OK"

for /f "delims=" %%a in ('adb shell "settings get global airplane_mode_on" 2^>nul') do set "AP_CHK=%%a"
if "!AP_CHK!" NEQ "1" (
    echo [%time%] WARNING: Airplane OFF, skip emergency call
    set "EMCALL_RESULT=FAIL"
    goto :eof
)

echo [%time%] Emergency call 118...
adb shell "su 0 am start -a android.intent.action.CALL_EMERGENCY -d tel:118" >nul 2>&1
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul

adb shell "dumpsys telecom" > "%TEMP%\cid_telecom.txt" 2>&1
%SystemRoot%\System32\findstr.exe /c:"isEmergency: true" "%TEMP%\cid_telecom.txt" >nul 2>&1
if errorlevel 1 (
    echo [%time%] Emergency call FAILED
    set "EMCALL_RESULT=FAIL"
    goto :eof
)

echo [%time%] In call - waiting 15s...
%SystemRoot%\System32\timeout.exe /t 15 /nobreak >nul

echo [%time%] Ending call (pkill phone)...
adb shell "su 0 pkill -f com.android.phone" >nul 2>&1
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul

adb shell "dumpsys telecom" > "%TEMP%\cid_telecom_end.txt" 2>&1
%SystemRoot%\System32\findstr.exe /c:"state=ACTIVE" "%TEMP%\cid_telecom_end.txt" >nul 2>&1
if not errorlevel 1 (
    echo [%time%] Call still active, retry pkill...
    adb shell "su 0 pkill -f com.android.phone" >nul 2>&1
    %SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
)

echo [%time%] Emergency call done
%SystemRoot%\System32\timeout.exe /t 5 /nobreak >nul
goto :eof

REM ============================================================
REM :EMCALL <iter>
REM ============================================================
:EMCALL
set "E_ITER=%1"
echo.
echo ==== [#!E_ITER!] EMERGENCY CALL ====

echo [%time%] Airplane ON...
call :SET_AIRPLANE_ON
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul

for /f "delims=" %%a in ('adb shell "settings get global airplane_mode_on" 2^>nul') do set "AP=%%a"
if "!AP!" NEQ "1" (
    echo [%time%] Retrying airplane mode...
    call :SET_AIRPLANE_ON
    %SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
)
echo [%time%] airplane=!AP!

adb shell "logcat -c" >nul 2>&1

set "ITER_NUM=!E_ITER!"
call :DO_EMCALL
if "!EMCALL_RESULT!"=="FAIL" (
    set "W_ITER=!E_ITER!"
    set "W_SCEN=EMCALL"
    set "W_RESULT=FAIL"
    set "W_REASON=EMCALL_FAIL"
    set "W_DETAIL=emergency call setup failed"
    set "W_CIDS=-1"
    set "W_COM=NONE"
    set "W_RO=0"
    set "W_RH=0"
    call :WRITE_CSV
    adb shell "su 0 settings put global airplane_mode_on 0" >nul 2>&1
    adb shell "su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false" >nul 2>&1
    %SystemRoot%\System32\timeout.exe /t 5 /nobreak >nul
    goto :eof
)

REM ── AT snapshot (비행기 ON 상태에서, baseline 조건과 일치) ──
call :AT_SNAPSHOT !E_ITER! EMCALL

REM ── radio_on / reg_home ──
adb shell "logcat -d -s RILJ" > "%TEMP%\cid_rilj.txt" 2>&1
set RO=0
set RH=0
for /f %%n in ('type "%TEMP%\cid_rilj.txt" ^| %SystemRoot%\System32\find.exe /c "RADIO_POWER on = true"') do set RO=%%n
for /f %%n in ('type "%TEMP%\cid_rilj.txt" ^| %SystemRoot%\System32\find.exe /c "REG_HOME"') do set RH=%%n

call :JUDGE_CID !E_ITER! EMCALL !RO! !RH!

REM ── 다음 iteration 위해 비행기 다시 ON (DO_EMCALL 이 건드리지 않음) ──
call :SET_AIRPLANE_ON
%SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul
goto :eof

REM ============================================================
REM :REPORT
REM ============================================================
:REPORT
echo.
echo ============================================================
echo  FINAL RESULT
echo   PASS: !PC!
echo   FAIL: !FC!
echo   Log : !LOG_FILE!
if "!ABORTED!"=="1" echo   [ABORTED due to 3 consecutive AT failures]
echo ============================================================
echo.

REM ── 비행기 모드 복구 ──
adb shell "su 0 settings put global airplane_mode_on 0" >nul 2>&1
adb shell "su 0 am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false" >nul 2>&1

echo Log       : !LOG_FILE!
echo Boot logs : !BOOT_LOG_DIR!
echo CID snaps : !CID_SNAP_DIR!
echo.

REM ── persist 로그 저장 ──
set /p "SAVE_PERSIST=디바이스 persist 로그를 저장하시겠습니까? (Y/N): "
if /i "!SAVE_PERSIST!"=="Y" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list 2^>nul') do set "PTS=%%I"
    set "PDEST=!PERSIST_DIR!\!PTS:~0,8!_!PTS:~8,6!"
    if not exist "!PERSIST_DIR!" mkdir "!PERSIST_DIR!"
    mkdir "!PDEST!" 2>nul
    echo [%time%] persist 로그 복사 중...
    set "CPERR=%TEMP%\logd_cperr_%RANDOM%.txt"
    adb shell "su 0 cp -r /data/misc/logd/ /data/local/tmp/logd_backup" >"!CPERR!" 2>&1
    adb shell "su 0 chmod -R 755 /data/local/tmp/logd_backup" >nul 2>&1
    set "PTMP=%TEMP%\logd_pull_%RANDOM%"
    mkdir "!PTMP!" 2>nul
    adb pull /data/local/tmp/logd_backup/ "!PTMP!" 2>&1
    xcopy "!PTMP!\logd_backup\*" "!PDEST!\" /E /Y /Q >nul 2>&1
    rmdir /s /q "!PTMP!" 2>nul
    adb shell "su 0 rm -rf /data/local/tmp/logd_backup" >nul 2>&1
    set "LOCAL_BYTES=0"
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "(Get-ChildItem -LiteralPath '!PDEST!' -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum"`) do set "LOCAL_BYTES=%%a"
    if "!LOCAL_BYTES!"=="" set "LOCAL_BYTES=0"
    if "!LOCAL_BYTES!"=="0" (
        echo [WARN] persist 로그 수집 결과가 0 bytes 입니다.
        echo        cp stderr: !CPERR!
    ) else (
        echo [%time%] persist 로그 수집 완료: !LOCAL_BYTES! bytes
        del "!CPERR!" 2>nul
    )
    echo.
    echo 전체 로그 위치:
    echo   CSV       : !LOG_FILE!
    echo   부팅 로그  : !BOOT_LOG_DIR!
    echo   CID 스냅샷 : !CID_SNAP_DIR!
    echo   persist   : !PDEST!
) else (
    echo persist 로그 저장 생략
)

echo.
pause
if "!ABORTED!"=="1" exit /b 2
exit /b 0
