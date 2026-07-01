@echo off
REM Grandpa's MariaDB Terminal -- setup script (Windows)
REM
REM Checks for MariaDB (installs if missing), creates a virtual environment,
REM installs Python packages, and runs the configurator.
REM Just double-click this file, or run it once:  setup.bat

cd /d "%~dp0"

REM ---- Check / install MariaDB ----
where mariadbd.exe >nul 2>nul
if %errorlevel% neq 0 (
    where mysql.exe >nul 2>nul
)
if %errorlevel% neq 0 (
    echo.
    echo MariaDB is not installed. Attempting to install via winget...
    winget install --id MariaDB.Server --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo.
        echo Could not install MariaDB automatically.
        echo Please install MariaDB manually from: https://mariadb.org/download/
        pause
        exit /b 1
    )
    echo MariaDB installed.

    REM Start the MariaDB service if it was registered as a service.
    sc query MariaDB >nul 2>nul
    if %errorlevel% equ 0 (
        net start MariaDB >nul 2>nul
    )
) else (
    echo MariaDB found.
)

REM ---- Check Python ----
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
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Now let's set up your connection (this writes config.toml).
".venv\Scripts\python.exe" configure.py

echo.
echo All set! Start the tool by double-clicking run.bat
echo.
pause
