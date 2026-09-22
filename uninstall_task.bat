@echo off
set TASK_NAME=KakaoTranslate

echo Removing scheduled task "%TASK_NAME%"...
schtasks /delete /tn "%TASK_NAME%" /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Task removed. KakaoTranslate will no longer start at login.
) else (
    echo [INFO] Task not found ^(may have already been removed^).
)

echo.
pause
