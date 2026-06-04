---
name: skilltrace-skip
description: Use when user declines Skilltrace for this project. "skip skilltrace", "don't track this project", "no skilltrace here".
---

Skip Skilltrace tracking for this project:
1. Run: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skip`
2. Parse the JSON response and confirm to the user that Skilltrace is skipped
3. Mention they can enable later anytime with /skilltrace-init
