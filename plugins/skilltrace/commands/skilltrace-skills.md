---
name: skilltrace-skills
description: Use when user asks about skills tracked by Skilltrace. "how many skills do I have", "show skilltrace skills", "skilltrace status", "what has skilltrace recorded", "list generated skills", "is skilltrace on". Shows status and all skills grouped by project.
disable-model-invocation: true
---

Show skill inventory and project status:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills`
2. Parse JSON. Present to user:
   - **Current project:** status (active/paused/not initialized) and skills
   - **Other projects:** skills grouped by project ID
   - **Summary:** total skills, total projects
