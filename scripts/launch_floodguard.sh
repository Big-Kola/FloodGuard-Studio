#!/usr/bin/env bash
# Launch FloodGuard Studio from any working directory.
# The GUI is shown through WSLg when started from Windows.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/floodguard.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
    echo "FloodGuard Studio: virtual environment missing at $PROJECT_DIR/.venv" >&2
    exit 1
fi

{
    printf '\n===== %s starting FloodGuard Studio =====\n' "$(date '+%Y-%m-%d %H:%M:%S')"
} >>"$LOG_FILE"

exec ".venv/bin/python" app.py >>"$LOG_FILE" 2>&1
