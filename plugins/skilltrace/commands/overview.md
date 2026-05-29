---
name: overview
description: Show skills across all projects with counts and details
---

Show cross-project skill overview:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" overview`
2. Parse JSON. Present to user grouped by project ID:
   - Current project marked clearly
   - For each project: list skills with name, version, description
   - Summary: total skills, total projects, skills per project
