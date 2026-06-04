---
name: skilltrace-history
description: Use when user asks about previous versions of a Skilltrace skill. "show skill history", "what changed in this skill", "old versions of deploy skill", "how did this skill evolve".
disable-model-invocation: true
---

Show version history for a skill:
1. User provides a skill name or ID. If name, first run `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills` to find the matching ID.
2. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" history {skill_id}`
3. Parse JSON. Present to user:
   - Skill name, ID, project, current version
   - For each version: version number, key changes compared to previous version
   - Highlight what evolved between versions (sections added/removed, steps changed, tools changed)
