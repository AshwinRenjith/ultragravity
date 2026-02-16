#!/bin/bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Check if arguments are provided
if [ $# -eq 0 ]; then
        echo "Usage: ./run.sh \"<instruction>\""
        echo "Examples:"
        echo "  ./run.sh \"Write a note about my meeting at 2pm\""
        echo "  ./run.sh \"Write a greetings message to Ayush Benny\""
    exit 1
fi

if command -v ultragravity >/dev/null 2>&1; then
    ultragravity ask "$@"
else
    if command -v python3 >/dev/null 2>&1; then
        python3 -m ultragravity.cli ask "$@"
    else
        python -m ultragravity.cli ask "$@"
    fi
fi
