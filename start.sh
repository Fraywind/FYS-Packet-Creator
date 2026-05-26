#!/usr/bin/env bash
# FYS Packet Creator. One-click start script for macOS and Linux.

set -e
cd "$(dirname "$0")"

echo
echo "============================================================"
echo "  FYS Packet Creator"
echo "============================================================"
echo

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python is not installed or not on PATH."
    echo
    echo "Install Python 3.9 or newer from https://python.org/downloads"
    exit 1
fi

echo "Checking dependencies..."
"$PYTHON" -m pip install --quiet --disable-pip-version-check -r requirements.txt
echo "Dependencies OK."
echo
echo "Starting the server at http://localhost:5050 ..."
echo "(Leave this window open while you use the tool. Press Ctrl+C to stop.)"
echo

# Open the default browser shortly after the server boots.
(
    sleep 3
    if command -v open >/dev/null 2>&1; then
        open http://localhost:5050
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost:5050
    fi
) &

"$PYTHON" app.py
