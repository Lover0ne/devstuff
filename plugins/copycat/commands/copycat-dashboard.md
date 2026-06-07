---
name: copycat-dashboard
description: Use when user asks to open the Copycat dashboard. "open copycat dashboard", "show template dashboard", "copycat UI", "view cloned templates".
---

Open the Copycat template dashboard:
1. Run (use Bash tool, not PowerShell): `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" dashboard`
2. Parse JSON response and confirm to user that dashboard was opened
