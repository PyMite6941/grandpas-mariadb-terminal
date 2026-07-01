#!/usr/bin/env bash
#
# Grandpa's MariaDB Terminal — setup script (Linux / macOS)
#
# Checks for MariaDB (installs if missing), creates a virtual environment,
# installs Python packages, and runs the configurator.
# Run it once:  ./setup.sh
#
set -e

cd "$(dirname "$0")"

# ---- Check / install MariaDB ----
if ! command -v mariadbd >/dev/null 2>&1 && ! command -v mysqld >/dev/null 2>&1; then
    echo ""
    echo "MariaDB/MySQL is not installed. Attempting to install..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt >/dev/null 2>&1; then
            sudo apt update && sudo apt install -y mariadb-server
            sudo systemctl start mariadb
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y mariadb-server
            sudo systemctl start mariadb
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y mariadb-server
            sudo systemctl start mariadb
        else
            echo "Could not determine package manager."
            echo "Please install MariaDB manually: https://mariadb.org/download/"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew >/dev/null 2>&1; then
            brew install mariadb
            brew services start mariadb
        else
            echo "Homebrew not found."
            echo "Please install MariaDB manually: https://mariadb.org/download/"
            exit 1
        fi
    else
        echo "Unsupported OS. Please install MariaDB manually: https://mariadb.org/download/"
        exit 1
    fi

    echo "MariaDB installed and started."
else
    echo "MariaDB found."
fi

# ---- Check / install Python ----
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python isn't installed. Please install Python 3 first: https://www.python.org/downloads/"
    exit 1
fi

echo ""
echo "Creating a virtual environment in .venv ..."
"$PY" -m venv .venv

echo "Installing packages (pymysql, rich, tomlkit) ..."
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "Now let's set up your connection (this writes config.toml)."
./.venv/bin/python configure.py

echo ""
echo "All set! Start the tool any time with:  ./run.sh"
