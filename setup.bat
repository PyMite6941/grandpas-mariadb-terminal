@echo off
REM Grandpa's MariaDB Terminal -- setup script (Windows)
REM
REM Creates a virtual environment and installs the packages the tool needs.
REM Just double-click this file, or run it once:  setup.bat

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo Python isn't installed. Please install Python 3 first: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Creating a virtual environment in .venv ...
%PY% -m venv .venv

echo Installing packages (pymysql, rich, tomlkit) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements2.txt

echo.
echo Now let's set up your connection (this writes config.toml).
".venv\Scripts\python.exe" configure.py

echo.
echo All set! Start the tool by double-clicking run.bat
echo.
pause
