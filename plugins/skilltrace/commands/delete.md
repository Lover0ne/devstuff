---
name: delete
description: Delete a skill from registry and disk
---

Delete a skill:
1. User provides a skill name or ID. If name, first run `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills` to find the matching ID.
2. **Confirm with user before deleting.** Show skill name, version, and project. Ask "Delete this skill? This removes all versions."
3. If confirmed, run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" delete {skill_id}`
4. Report what was removed.
