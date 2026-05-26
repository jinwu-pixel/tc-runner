@echo off
setlocal
cd /d "%~dp0"
title QC AP Log Capture

rem ============================================================
rem Qualcomm Android AP log capture through reboot
rem
rem Usage:
rem   1) Run this bat
rem   2) When "Phase 1" appears, reboot the device manually
rem   3) After boot finishes, press Ctrl+C to end
rem
rem Output: %USERPROFILE%\Desktop\QC_AP_Logs\capture_<timestamp>\
rem ============================================================

rem --- locate qc_ap_log_capture.py (same folder or scripts\ subfolder) ---
set "SCRIPT="
if exist "%~dp0qc_ap_log_capture.py" set "SCRIPT=%~dp0qc_ap_log_capture.py"
if not defined SCRIPT if exist "%~dp0scripts\qc_ap_log_capture.py" set "SCRIPT=%~dp0scripts\qc_ap_log_capture.py"
if not defined SCRIPT (
    echo [ERROR] qc_ap_log_capture.py not found.
    echo   Place it next to this bat, or in a scripts\ subfolder.
    echo   Current dir: %~dp0
    pause
    exit /b 1
)

rem --- locate python ---
call :find_python
if not defined PY (
    echo [ERROR] Python not found.
    echo   Tried:
    echo     - PATH ^(python, py^)
    echo     - %~dp0venv\Scripts\python.exe
    echo     - %USERPROFILE%\AppData\Local\Programs\Python\Python3xx\python.exe
    echo     - %USERPROFILE%\AppData\Local\Programs\Python\Launcher\py.exe
    echo   Install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

rem --- locate adb (must be on PATH, or common Android SDK locations) ---
call :find_adb
if not defined ADB_OK (
    echo [ERROR] adb not found on PATH.
    echo   Install Android Platform Tools and add to PATH:
    echo   https://developer.android.com/tools/releases/platform-tools
    pause
    exit /b 1
)

echo Python : %PY%
echo adb    : found
echo Script : %SCRIPT%
echo.

rem --- run (do not forward %* to avoid drag-drop arg issues) ---
"%PY%" "%SCRIPT%"
set RC=%errorlevel%

echo.
echo [exit code: %RC%]
pause
endlocal
exit /b %RC%

:find_python
set "PY="
where python >nul 2>&1 && set "PY=python" && goto :eof
where py >nul 2>&1 && set "PY=py" && goto :eof
if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe" & goto :eof
for %%V in (313 312 311 310 39) do (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python%%V\python.exe" (
        set "PY=%USERPROFILE%\AppData\Local\Programs\Python\Python%%V\python.exe"
        goto :eof
    )
)
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Launcher\py.exe" set "PY=%USERPROFILE%\AppData\Local\Programs\Python\Launcher\py.exe" & goto :eof
goto :eof

:find_adb
set "ADB_OK="
where adb >nul 2>&1 && set "ADB_OK=1" && goto :eof
rem common Android SDK platform-tools locations
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    set "PATH=%LOCALAPPDATA%\Android\Sdk\platform-tools;%PATH%"
    set "ADB_OK=1"
    goto :eof
)
if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe" (
    set "PATH=%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools;%PATH%"
    set "ADB_OK=1"
    goto :eof
)
if exist "C:\platform-tools\adb.exe" (
    set "PATH=C:\platform-tools;%PATH%"
    set "ADB_OK=1"
    goto :eof
)
goto :eof
