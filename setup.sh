#!/usr/bin/env bash
#
# Grandpa's MariaDB Terminal — setup script (Linux / macOS)
#
# Creates a virtual environment and installs the packages the tool needs.
# Run it once:  ./setup.sh
#
set -e

cd "$(dirname "$0")"

# Pick a python command that exists.
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python isn't installed. Please install Python 3 first: https://www.python.org/downloads/"
    exit 1
fi

echo "Creating a virtual environment in .venv ..."
"$PY" -m venv .venv

echo "Installing packages (pymysql, rich, tomlkit) ..."
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install -r requirements.txt

echo
echo "Now let's set up your connection (this writes config.toml)."
./.venv/bin/python configure.py

echo
echo "All set! Start the tool any time with:  ./run.sh"
