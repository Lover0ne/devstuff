---
name: skilltrace-skills
description: Use when user asks about skills tracked by Skilltrace. "how many skills do I have", "show skilltrace skills", "what has skilltrace recorded", "list generated skills". Only shows skills created by Skilltrace, not all Claude Code skills.
disable-model-invocation: true
---

Show skill inventory:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills`
2. Parse JSON. Present to user grouped by project:
   - **This project:** skills created here, with name, description, version
   - **Other projects:** skills from elsewhere, same format
   - **Summary:** total count, this project count, other projects count
