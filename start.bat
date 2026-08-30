@echo off
setlocal
cd /d "%~dp0"
title FH6 Scenic Navigator

echo.
echo ==========================================
echo   FH6 Scenic Navigator v1.19.0 HORIZON COMMAND UI + I18N
echo ==========================================
echo.
echo Planner catalog data is bundled with this release and is NOT downloaded at startup.
echo Startup progress is shown as 1/4 ... 4/4.
echo The browser opens only AFTER the HTTP and Forza UDP sockets are ready.
echo.

where py >nul 2>nul
if errorlevel 1 goto :try_python
py -3 -u launcher.py
set "EXITCODE=%ERRORLEVEL%"
goto :done

:try_python
where python >nul 2>nul
if errorlevel 1 goto :no_python
python -u launcher.py
set "EXITCODE=%ERRORLEVEL%"
goto :done

:no_python
echo.
echo ERROR: Python 3 was not found.
echo Install Python 3.10+ from python.org and enable Add Python to PATH.
echo Then run start.bat again.
echo.
set "EXITCODE=1"

:done
if not "%EXITCODE%"=="0" pause
endlocal & exit /b %EXITCODE%
