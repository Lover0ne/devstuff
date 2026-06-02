#!/bin/bash
# PreToolUse gate — three-stage check.
# Stage 0: Subagent bypass — skip gate entirely for child agents.
# Stage 1: Init gate — block if .skilltrace marker missing (whitelist init/skip to avoid deadlock).
# Stage 2: Task boundary — block once per prompt to force skilltracer evaluation.

# --- Stage 0: Subagent bypass ---
INPUT=$(cat)
if echo "$INPUT" | grep -q '"parent_tool_use_id"\s*:\s*"'; then
    exit 0
fi

# --- Stage 1: Init gate ---
DIR="$(pwd)"
MARKER_FOUND=false
MARKER_PATH=""
while true; do
    if [ -f "$DIR/.skilltrace" ]; then
        MARKER_FOUND=true
        MARKER_PATH="$DIR/.skilltrace"
        break
    fi
    PARENT="$(dirname "$DIR")"
    [ "$PARENT" = "$DIR" ] && break
    DIR="$PARENT"
done

if [ "$MARKER_FOUND" = false ]; then
    # Allow init/skip wrapper commands through to avoid deadlock
    case "$INPUT" in
        *wrapper.sh*init*|*wrapper.sh*skip*)
            exit 0
            ;;
    esac
    # Allow non-blocking tools needed for init/skip flow
    # NOTE: Skill is NOT whitelisted — prevents agents from autonomously skipping init
    case "$INPUT" in
        *\"AskUserQuestion\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
            exit 0
            ;;
    esac
    PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    cat << DENY
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"ERROR: Skilltrace plugin is active but this project is NOT initialized. Tool use is BLOCKED until resolved. You MUST use AskUserQuestion NOW with: question='Skilltrace is installed. Enable skill tracking for this project?', header='Skilltrace', options=[{label:'Yes',description:'Enable — silently learns from your work and creates reusable skills'},{label:'No',description:'Skip for now — enable later with /skilltrace-init'}]. After the user answers: if Yes run: bash \\\"${PLUGIN_ROOT}/hooks/wrapper.sh\\\" init. If No run: bash \\\"${PLUGIN_ROOT}/hooks/wrapper.sh\\\" skip. You MUST NOT skip or init without asking the user first. Autonomous skipping is forbidden."}}
DENY
    exit 0
fi

# --- Stage 2: Task boundary check ---
# Skip if project declined or paused
grep -q '"declined"' "$MARKER_PATH" 2>/dev/null && exit 0
grep -q '"paused"' "$MARKER_PATH" 2>/dev/null && exit 0

# Check for pending reminder (pre-built deny JSON from cmd_reminder)
PENDING="$HOME/.skilltrace-gate/pending"
[ ! -f "$PENDING" ] && exit 0

# Allow non-blocking tools without consuming the reminder
# NOTE: Skill is NOT whitelisted here — skilltracer must go through boundary check
case "$INPUT" in
    *\"AskUserQuestion\"*|*\"TaskCreate\"*|*\"TaskUpdate\"*|*\"TaskList\"*|*\"TaskGet\"*|*\"EnterPlanMode\"*|*\"ExitPlanMode\"*|*\"CronCreate\"*|*\"CronDelete\"*|*\"CronList\"*|*\"ScheduleWakeup\"*)
        exit 0
        ;;
esac

# Fire reminder (output pre-built deny JSON) and disarm
cat "$PENDING"
rm -f "$PENDING"
exit 0
