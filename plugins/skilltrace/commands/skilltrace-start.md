---
name: skilltrace-start
description: Use when user wants to enable or resume Skilltrace. "start skilltrace", "enable tracking", "resume skilltrace", "re-enable skilltrace", "start tracking again".
---

Start or resume Skilltrace tracking:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" start`
2. Parse JSON response and confirm to user
3. Handles: re-enabling after decline, resuming after stop, or confirming already active
