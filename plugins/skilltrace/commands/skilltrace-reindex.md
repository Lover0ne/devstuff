---
name: skilltrace-reindex
description: Use when Skilltrace registry is out of sync with skill files on disk. "reindex skills", "rebuild skilltrace registry", "skills missing from list". Scans .claude/skills/ and re-registers all found SKILL.md files.
---

Rebuild the skill registry from SKILL.md files on disk:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" reindex`
2. Report the result to user: how many skills were indexed
