@echo off
REM Grandpa's MariaDB Terminal -- launcher (Windows)
REM
REM Runs the tool using the virtual environment created by setup.bat.
REM If you haven't run setup yet, it will do that for you first.

cd /d "%~dp0"

if not exist ".venv" (
    echo First run -- setting things up ...
    call setup.bat
)

".venv\Scripts\python.exe" mariadb_terminal.py
pause
