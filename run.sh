#!/usr/bin/env bash
#
# Grandpa's MariaDB Terminal — launcher (Linux / macOS)
#
# Runs the tool using the virtual environment created by setup.sh.
# If you haven't run setup yet, it will do that for you first.
#
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "First run — setting things up ..."
    ./setup.sh
fi

exec ./.venv/bin/python mariadb_terminal.py
