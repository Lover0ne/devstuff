---
name: status
description: Show Skilltrace status, skill count, and last extraction
---

Show current Skilltrace status:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" status`
2. Parse the JSON response and report to user: enabled/disabled, total skills, project skills, project ID, last updated
