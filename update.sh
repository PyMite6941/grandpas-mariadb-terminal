#!/usr/bin/env bash
#
# Grandpa's MariaDB Terminal -- check for updates (Linux / macOS)
#
# Passes any arguments straight through, e.g.:
#   ./update.sh              # check and offer to update
#   ./update.sh --check      # only tell me if there's an update
#   ./update.sh --level minor
#
set -e
cd "$(dirname "$0")"

# Prefer the venv python if setup has been run; otherwise use system python.
if [ -x "./.venv/bin/python" ]; then
    PY="./.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

exec "$PY" update.py "$@"
