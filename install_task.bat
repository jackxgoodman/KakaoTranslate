@echo off
setlocal EnableDelayedExpansion

set TASK_NAME=KakaoTranslate
set SCRIPT_DIR=%~dp0
:: Strip trailing backslash
if "!SCRIPT_DIR:~-1!"=="\" set SCRIPT_DIR=!SCRIPT_DIR:~0,-1!
set RUN_SCRIPT=!SCRIPT_DIR!\run.bat

echo.
echo  KakaoTranslate ^— Auto-start installer
echo  =========================================
echo  Task name : %TASK_NAME%
echo  Script    : %RUN_SCRIPT%
echo  Trigger   : At login, after a 60-second delay
echo              (delay lets KakaoTalk finish starting first)
echo.

:: Delete any existing task with the same name first
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create the task: runs at login, 60-second startup delay, minimised window
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%RUN_SCRIPT%\"" ^
    /sc ONLOGON ^
    /delay 0001:00 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo  [OK] Task created successfully.
    echo.
    echo  IMPORTANT — also make KakaoTalk start at login:
    echo    KakaoTalk ^> Settings ^> General ^> "Run KakaoTalk when Windows starts"
    echo.
    echo  Logs are written to:
    echo    !SCRIPT_DIR!\kakaotranslate.log
    echo.
    echo  To remove auto-start, run uninstall_task.bat
) else (
    echo  [ERROR] Could not create task.
    echo  Try right-clicking install_task.bat and choosing "Run as administrator".
)

echo.
pause
