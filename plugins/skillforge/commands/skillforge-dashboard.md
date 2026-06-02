---
description: Use when user asks to open the Skillforge dashboard. "open skillforge dashboard", "show generated skills dashboard", "skillforge UI". Opens an interactive HTML page in the browser.
---

Run the dashboard generator:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" dashboard
```

This generates a self-contained HTML file and opens it in the default browser.
Pass `--no-open` to generate without opening.
