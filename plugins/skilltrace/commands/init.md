---
name: init
description: Enable Skilltrace tracking for the current project
---

Initialize Skilltrace for this project:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" init`
2. Parse the JSON response and confirm to the user that the project is now tracked
3. Skilltrace will silently observe future sessions and generate reusable skills automatically
