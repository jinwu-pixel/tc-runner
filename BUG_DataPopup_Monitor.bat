@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title BUG Z0513U Data Popup Race Monitor

:: ============================================================
:: ODIN2 Z0513U Mobile Data Popup race repro loop launcher
::
:: 사용법:
::   BUG_DataPopup_Monitor.bat                        (기본: N=3, variant=?)
::   BUG_DataPopup_Monitor.bat 3 V1                   (V1=MODEM+DM+ADB, N=3)
::   BUG_DataPopup_Monitor.bat 10 V2                  (V2=+RMNET+ADPL+QDSS, N=10)
::   BUG_DataPopup_Monitor.bat 10 V1 <device_serial>  (특정 단말 시리얼 지정)
::
:: QXDM + ADB 셋업 가정: 도구는 adb 통로만 사용, diag port 비방해.
:: USB composition 전환은 사용자 영역 (도구는 라벨만 기록).
:: ============================================================

set ITERATIONS=3
set VARIANT=?
set SERIAL=
if not "%~1"=="" set ITERATIONS=%~1
if not "%~2"=="" set VARIANT=%~2
if not "%~3"=="" set SERIAL=--serial %~3

:: Python 탐색
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY=python
    goto :found
)
if exist "%~dp0venv\Scripts\python.exe" (
    set PY=%~dp0venv\Scripts\python.exe
    goto :found
)

echo [ERROR] Python을 찾을 수 없습니다.
pause
exit /b 1

:found
echo Python: %PY%
echo Iterations: %ITERATIONS%
echo Variant: %VARIANT%
echo Serial: %SERIAL%
echo.

%PY% "%~dp0scripts\data_popup_repro_loop.py" -n %ITERATIONS% --variant %VARIANT% %SERIAL%

echo.
pause
