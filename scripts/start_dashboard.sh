#!/usr/bin/env bash

# Local script to start the Arizona Power Outage Explorer dashboard.
# Designed to run locally (Windows, macOS, Linux) or on a Raspberry Pi.

# Locate the directory containing this script, and move to repository root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$REPO_ROOT" || {
    echo "Error: Failed to change directory to repository root: $REPO_ROOT"
    exit 1
}

echo "Starting Arizona Power Outage Explorer..."
echo "Working directory: $PWD"

# 1. Activate local virtual environment if present
if [ -d "venv" ]; then
    if [ -f "venv/bin/activate" ]; then
        echo "Activating virtual environment (Unix)..."
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        echo "Activating virtual environment (Windows)..."
        source venv/Scripts/activate
    fi
else
    echo "Warning: No 'venv' folder found. Attempting to use global Python environment."
fi

# 2. Check python command availability
if ! command -v python &> /dev/null; then
    echo "Error: 'python' command not found. Please install Python 3."
    exit 1
fi

# 3. Check dependencies
python -c "import flask" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Error: Flask is not installed in the active Python environment."
    echo "Please install dependencies by running:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 4. Run dashboard
echo "Launching web server..."
python app.py
