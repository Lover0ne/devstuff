---
name: skilltrace-dashboard
description: Use when user asks to open the Skilltrace dashboard. "open skilltrace dashboard", "show skill dashboard", "skilltrace UI", "open dashboard". Opens an interactive HTML page in the browser.
---

Run the dashboard generator:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" dashboard
```

This generates a self-contained HTML file and opens it in the default browser.
Pass `--no-open` to generate without opening.
