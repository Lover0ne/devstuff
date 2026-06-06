#!/bin/bash
# PreToolUse gate — three-stage check.
# Stage 0: Subagent bypass — skip gate entirely for child agents.
# Stage 1: Init gate — block if .skilltrace marker missing (whitelist init/skip to avoid deadlock).
# Stage 2: Task boundary — block once per prompt to force skilltracer evaluation.

# --- Stage 0: Subagent bypass ---
INPUT=$(cat)

if echo "$INPUT" | grep -q '"parent_tool_use_id"[[:space:]]*:[[:space:]]*"'; then
    exit 0
fi

# --- Stage 1: Init gate ---
MARKER_PATH="$(pwd)/.skilltrace"
if [ ! -f "$MARKER_PATH" ]; then
    case "$INPUT" in
        *wrapper.sh*init*|*wrapper.sh*skip*)
            exit 0
            ;;
    esac
    case "$INPUT" in
        *\"AskUserQuestion\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
            exit 0
            ;;
    esac
    PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    PROJECT_DIR="$(pwd)"
    DENY_JSON=$(cat << DENY
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"ERROR: Skilltrace plugin is active but this project is NOT initialized. Tool use is BLOCKED until resolved. You MUST use AskUserQuestion NOW with: question='Skilltrace is installed. Enable skill tracking for this project?', header='Skilltrace', options=[{label:'Yes',description:'Enable — silently learns from your work and creates reusable skills'},{label:'No',description:'Skip for now — enable later with /skilltrace-start'}]. After the user answers: if Yes, run this exact Bash command: bash \"${PLUGIN_ROOT}/hooks/wrapper.sh\" init \"${PROJECT_DIR}\" — if No, run this exact Bash command: bash \"${PLUGIN_ROOT}/hooks/wrapper.sh\" skip \"${PROJECT_DIR}\" — Do NOT use the Skill tool for init or skip. You MUST NOT skip or init without asking the user first. Autonomous skipping is forbidden."}}
DENY
)
    echo "$DENY_JSON"
    exit 0
fi

# --- Stage 2: Task boundary check ---
grep -q '"declined"' "$MARKER_PATH" 2>/dev/null && exit 0
grep -q '"paused"' "$MARKER_PATH" 2>/dev/null && exit 0

PENDING="$HOME/.skilltrace-gate/pending"
[ ! -f "$PENDING" ] && exit 0

# Allow non-blocking tools without consuming the reminder
case "$INPUT" in
    *\"AskUserQuestion\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
        exit 0
        ;;
    *wrapper.sh*|*\"Skill\"*)
        exit 0
        ;;
esac

# Fire reminder (atomic consume) and disarm
CONSUMED="${PENDING}.$$"
if mv "$PENDING" "$CONSUMED" 2>/dev/null; then
    cat "$CONSUMED"
    rm -f "$CONSUMED"
fi
exit 0
