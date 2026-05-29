---
name: skills
description: List all Skilltrace skills with descriptions, versions, and project info
---

Show skill inventory:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills`
2. Parse JSON. Present to user grouped by project:
   - **This project:** skills created here, with name, description, version
   - **Other projects:** skills from elsewhere, same format
   - **Summary:** total count, this project count, other projects count
