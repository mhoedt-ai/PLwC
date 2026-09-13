@echo off
setlocal
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0collect-r27-legacy-state.ps1" -OutputDirectory "%~dp0"
set "PLWC_DIAG_EXIT=%ERRORLEVEL%"
echo.
if not "%PLWC_DIAG_EXIT%"=="0" echo Diagnose fehlgeschlagen. Exitcode: %PLWC_DIAG_EXIT%
pause
exit /b %PLWC_DIAG_EXIT%
