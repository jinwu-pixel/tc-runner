@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title THOR2_J Call Multitask Memory-Stress Monitor

:: ============================================================
:: THOR2_J (AT-M140, low-RAM) 통화 중 멀티태스킹 메모리 압박 repro loop
::
:: 사용법:
::   BUG_CallMultitask_Monitor.bat 5 01000000000          (CALL arm, N=5, callee 발신)
::   BUG_CallMultitask_Monitor.bat 5 NOCALL               (대조군: 통화 없이 동일 버스트)
::   BUG_CallMultitask_Monitor.bat 5 01000000000 <serial> (단말 시리얼 override)
::
:: callee = 자동응답 회선. 잠금은 None/Swipe 임시(테스트 후 패턴 복원).
:: 동일모델 2대 연결 시 SERIAL 핀 필수(오발사 가드는 harness가 재확인).
:: ============================================================

set CYCLES=5
set SERIAL=B2700125BW000083
set ARM=
set CALLEE=
if not "%~1"=="" set CYCLES=%~1
if /I "%~2"=="NOCALL" set ARM=--no-call
if /I not "%~2"=="NOCALL" if not "%~2"=="" set CALLEE=--callee %~2
if not "%~3"=="" set SERIAL=%~3

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
echo Serial: %SERIAL%
echo Cycles: %CYCLES%
echo Arm:    %ARM% %CALLEE%
echo.

%PY% "%~dp0scripts\multitask_call_stress.py" --serial %SERIAL% -n %CYCLES% %ARM% %CALLEE%

echo.
pause
