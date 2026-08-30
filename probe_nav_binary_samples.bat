@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   FH6 NAV Binary Probe
echo ==========================================
echo.
py -3 -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 goto use_py
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 goto use_python
echo Python 3 was not found.
echo Install Python 3.10+ from python.org and try again.
goto done

:use_py
py -3 "%~dp0nav_binary_probe.py" %*
goto done

:use_python
python "%~dp0nav_binary_probe.py" %*

:done
echo.
pause
endlocal
