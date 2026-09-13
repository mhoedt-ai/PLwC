@echo off
setlocal
set "PLWC_DIAG_SHARE=%~dp0"
pushd "%PLWC_DIAG_SHARE%" >nul 2>&1
if errorlevel 1 (
    echo Der Diagnoseordner konnte nicht geoeffnet werden: %PLWC_DIAG_SHARE%
    if not "%PLWC_DIAG_NO_PAUSE%"=="1" pause
    exit /b 2
)
set "PLWC_DIAG_CONSOLE_LOG=%PLWC_DIAG_SHARE%PLwC-r27-Diagnose-Konsolenprotokoll.txt"
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ".\collect-r27-legacy-state.ps1" -OutputDirectory "." > "%PLWC_DIAG_CONSOLE_LOG%" 2>&1
set "PLWC_DIAG_EXIT=%ERRORLEVEL%"
type "%PLWC_DIAG_CONSOLE_LOG%"
popd
echo.
if not "%PLWC_DIAG_EXIT%"=="0" (
    echo Diagnose fehlgeschlagen. Exitcode: %PLWC_DIAG_EXIT%
    echo Fehlerprotokoll: %PLWC_DIAG_CONSOLE_LOG%
)
if not "%PLWC_DIAG_NO_PAUSE%"=="1" pause
exit /b %PLWC_DIAG_EXIT%
