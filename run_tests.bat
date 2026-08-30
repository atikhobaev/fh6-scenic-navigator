@echo off
cd /d "%~dp0"
py -3 -m unittest discover -s tests -p "test_*.py"
if errorlevel 1 pause & exit /b 1
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js not found - JavaScript unit tests skipped.
) else (
  node --test tests\nav_logic.test.mjs tests\routing.test.mjs tests\route_data.test.mjs tests\ui_structure.test.mjs
)
pause
