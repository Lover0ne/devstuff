---
name: history
description: Show full version history of a specific skill with content of each version
---

Show version history for a skill:
1. User provides a skill name or ID. If name, first run `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills` to find the matching ID.
2. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" history {skill_id}`
3. Parse JSON. Present to user:
   - Skill name, ID, project, current version
   - For each version: version number, key changes compared to previous version
   - Highlight what evolved between versions (sections added/removed, steps changed, tools changed)
