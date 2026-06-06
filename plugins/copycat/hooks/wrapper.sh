#!/bin/bash
# Hook dispatcher — pipes stdin (hook_data JSON) to Python CLI
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -n "$WINDIR" ]]; then
    if command -v py &>/dev/null; then
        echo "$INPUT" | py "${SCRIPT_DIR}/src/cli.py" "$@"
    elif command -v python &>/dev/null; then
        echo "$INPUT" | python "${SCRIPT_DIR}/src/cli.py" "$@"
    else
        echo '{"error":"Python not found"}' >&2
        exit 1
    fi
elif command -v python3 &>/dev/null; then
    echo "$INPUT" | python3 "${SCRIPT_DIR}/src/cli.py" "$@"
else
    echo "$INPUT" | python "${SCRIPT_DIR}/src/cli.py" "$@"
fi
