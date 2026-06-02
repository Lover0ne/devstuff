---
description: Open Skilltrace dashboard in the browser. Shows all projects, skills, version history, and diffs. "open skilltrace dashboard", "show skill dashboard", "skilltrace UI".
disable-model-invocation: true
---

Run the dashboard generator:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" dashboard
```

This generates a self-contained HTML file and opens it in the default browser.
Pass `--no-open` to generate without opening.
