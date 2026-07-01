@echo off
REM Grandpa's MariaDB Terminal -- check for updates (Windows)
REM
REM Double-click to check, or run with arguments, e.g.:
REM   update.bat --check
REM   update.bat --level minor

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" update.py %*
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py update.py %*
    ) else (
        python update.py %*
    )
)

pause
