@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title BUG-5426 APN Monitor (Python)

:: ============================================================
:: Python 버전 런처
:: Python이 설치된 환경에서 사용
::
:: 사용법:
::   BUG5426_APN_Monitor_py.bat                  (기본: reboot 20회)
::   BUG5426_APN_Monitor_py.bat 10 both          (both 10회)
::   BUG5426_APN_Monitor_py.bat 30 emcall_only   (긴급호 30회)
:: ============================================================

set ITERATIONS=20
set SCENARIO=reboot_only
if not "%~1"=="" set ITERATIONS=%~1
if not "%~2"=="" set SCENARIO=%~2

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
echo   순수 bat 버전을 사용하세요: BUG5426_APN_Monitor.bat
pause
exit /b 1

:found
echo Python: %PY%
echo.

:: WWAN AutoConfig 중지
sc stop WwanSvc >nul 2>&1

%PY% "%~dp0scripts\apn_reboot_loop.py" -n %ITERATIONS% -s %SCENARIO% --stop-on-fail

echo.
pause
