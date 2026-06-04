#!/bin/bash
# PreToolUse gate — three-stage check.
# Stage 0: Subagent bypass — skip gate entirely for child agents.
# Stage 1: Init gate — block if .skilltrace marker missing (whitelist init/skip to avoid deadlock).
# Stage 2: Task boundary — block once per prompt to force skilltracer evaluation.

# --- DEBUG LOG (temporary) ---
DEBUG_LOG="$HOME/.skilltrace-gate/debug.log"
mkdir -p "$(dirname "$DEBUG_LOG")"
dbg() { echo "[$(date '+%H:%M:%S')] $1" >> "$DEBUG_LOG"; }

# --- Stage 0: Subagent bypass ---
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
dbg "GATE FIRED — tool=$TOOL_NAME length=${#INPUT}"

if echo "$INPUT" | grep -q '"parent_tool_use_id"\s*:\s*"'; then
    dbg "STAGE 0: subagent detected — ALLOW"
    exit 0
fi
dbg "STAGE 0: not subagent — continue"

# --- Stage 1: Init gate ---
MARKER_PATH="$(pwd)/.skilltrace"
MARKER_FOUND=false
if [ -f "$MARKER_PATH" ]; then
    MARKER_FOUND=true
fi
dbg "STAGE 1: marker=$MARKER_FOUND path=$MARKER_PATH"

if [ "$MARKER_FOUND" = false ]; then
    # Allow init/skip wrapper commands through to avoid deadlock
    case "$INPUT" in
        *wrapper.sh*init*|*wrapper.sh*skip*)
            dbg "STAGE 1: whitelist wrapper init/skip — ALLOW"
            exit 0
            ;;
    esac
    # Allow non-blocking tools needed for init/skip flow
    case "$INPUT" in
        *\"AskUserQuestion\"*|*\"Skill\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
            dbg "STAGE 1: whitelist tool=$TOOL_NAME — ALLOW"
            exit 0
            ;;
    esac
    dbg "STAGE 1: no marker, not whitelisted — DENY (tool=$TOOL_NAME)"
    cat << 'DENY'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"ERROR: Skilltrace plugin is active but this project is NOT initialized. Tool use is BLOCKED until resolved. You MUST use AskUserQuestion NOW with: question='Skilltrace is installed. Enable skill tracking for this project?', header='Skilltrace', options=[{label:'Yes',description:'Enable — silently learns from your work and creates reusable skills'},{label:'No',description:'Skip for now — enable later with /skilltrace-init'}]. If user selects Yes: invoke Skill tool with skill='skilltrace:skilltrace-init'. If user selects No: invoke Skill tool with skill='skilltrace:skilltrace-skip'. No other tools will work until this is resolved."}}
DENY
    dbg "STAGE 1: deny JSON emitted"
    exit 0
fi

# --- Stage 2: Task boundary check ---
# Skip if project declined or paused
grep -q '"declined"' "$MARKER_PATH" 2>/dev/null && { dbg "STAGE 2: declined — ALLOW"; exit 0; }
grep -q '"paused"' "$MARKER_PATH" 2>/dev/null && { dbg "STAGE 2: paused — ALLOW"; exit 0; }

# Check for pending reminder (pre-built deny JSON from cmd_reminder)
PENDING="$HOME/.skilltrace-gate/pending"
if [ ! -f "$PENDING" ]; then
    dbg "STAGE 2: no pending — ALLOW"
    exit 0
fi

# Allow non-blocking tools without consuming the reminder
# NOTE: Skill is NOT whitelisted here — skilltracer must go through boundary check
case "$INPUT" in
    *\"AskUserQuestion\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
        dbg "STAGE 2: whitelist tool=$TOOL_NAME — ALLOW (pending kept)"
        exit 0
        ;;
esac

# Fire reminder (output pre-built deny JSON) and disarm
dbg "STAGE 2: firing pending deny (tool=$TOOL_NAME)"
cat "$PENDING"
rm -f "$PENDING"
exit 0
