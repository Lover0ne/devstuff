---
name: skillforge-skills
description: List all generated utility skills with versions, filterable by project
---

List generated skills:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skills`
2. Parse JSON and present a formatted table:
   - Skill name, version, category, description
   - Mark which skills belong to the current project
   - Show total counts: this project vs other projects
