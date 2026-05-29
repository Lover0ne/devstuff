---
name: show
description: Show the full content of a specific skill by name or ID
---

Show a skill's content:
1. User provides a skill name or ID. If name, first run `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills` to find the matching ID.
2. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" show {skill_id}`
3. Parse JSON. Present to user:
   - Skill metadata (name, version, project, created/updated)
   - Full SKILL.md content formatted as markdown
