#!/bin/bash
# First-run setup for Skilltrace
set -e

SKILLTRACE_DIR="$HOME/.claude/skilltrace"
SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$SKILLTRACE_DIR/versions"
mkdir -p "$SKILLS_DIR"

echo '{"status": "ok", "action": "manual_setup_complete"}'
