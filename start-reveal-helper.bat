@echo off
REM Double-click this file to start the RECORD "Go" helper (Windows).
cd /d "%~dp0"
echo Starting RECORD reveal helper...

REM Try the Python launcher first (py), then python, then python3.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py reveal-helper.py
    goto :end
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python reveal-helper.py
    goto :end
)
where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    python3 reveal-helper.py
    goto :end
)

echo.
echo ERROR: Python was not found on your PATH.
echo Install Python from https://www.python.org/downloads/ and tick
echo "Add python.exe to PATH" during setup, then try again.

:end
echo.
pause
