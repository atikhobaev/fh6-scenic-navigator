@echo off
setlocal
cd /d "%~dp0"
title FH6 Navigator - Rebuild Offline Map Data

echo.
echo ==========================================
echo   FH6 Navigator - OFFLINE MAP REBUILD
echo ==========================================
echo.
echo Internet is NOT used.
echo Rebuilds Planner map catalogs only from data already bundled with this release.
echo Progress is shown below so the process never looks frozen.
echo.

where py >nul 2>nul
if errorlevel 1 goto :python
py -3 -u -m tools.places_import.offline_rebuild
set "EXITCODE=%ERRORLEVEL%"
goto :done

:python
python -u -m tools.places_import.offline_rebuild
set "EXITCODE=%ERRORLEVEL%"

:done
echo.
if "%EXITCODE%"=="0" (
  echo Offline map rebuild complete.
) else (
  echo Offline rebuild failed. See the ERROR line above.
)
pause
endlocal & exit /b %EXITCODE%
