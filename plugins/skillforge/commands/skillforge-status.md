---
name: skillforge-status
description: Use when you want to check Skillforge status. "skillforge status", "how many skills generated", "is skillforge active".
disable-model-invocation: true
---

Show Skillforge status:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" status`
2. Parse JSON and report: total skills across all projects, skills for this project, last updated timestamp
