#!/bin/bash
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -n "$WINDIR" ]]; then
    echo "$INPUT" | py "${SCRIPT_DIR}/src/cli.py" "$@" 2>/dev/null \
    || echo "$INPUT" | python "${SCRIPT_DIR}/src/cli.py" "$@"
elif command -v python3 &>/dev/null; then
    echo "$INPUT" | python3 "${SCRIPT_DIR}/src/cli.py" "$@"
else
    echo "$INPUT" | python "${SCRIPT_DIR}/src/cli.py" "$@"
fi
