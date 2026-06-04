---
name: skilltrace-status
description: Use when user asks if Skilltrace is active, enabled, or running. "is skilltrace on", "skilltrace status", "is tracking enabled". Shows enabled/disabled state, skill count, and project ID.
disable-model-invocation: true
---

Show current Skilltrace status:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" status`
2. Parse the JSON response and report to user: enabled/disabled, total skills, project skills, project ID, last updated
