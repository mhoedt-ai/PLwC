@echo off
setlocal
set "PLWC_DIAG_SHARE=%~dp0"
pushd "%PLWC_DIAG_SHARE%" >nul 2>&1
if errorlevel 1 (
    echo Der Diagnoseordner konnte nicht geoeffnet werden: %PLWC_DIAG_SHARE%
    pause
    exit /b 2
)
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ".\collect-r27-legacy-state.ps1" -OutputDirectory "%PLWC_DIAG_SHARE%"
set "PLWC_DIAG_EXIT=%ERRORLEVEL%"
popd
echo.
if not "%PLWC_DIAG_EXIT%"=="0" echo Diagnose fehlgeschlagen. Exitcode: %PLWC_DIAG_EXIT%
pause
exit /b %PLWC_DIAG_EXIT%
