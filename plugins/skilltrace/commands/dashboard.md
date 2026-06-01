---
description: Open interactive dashboard showing all projects, skills, versions, and diffs
disable-model-invocation: true
---

Run the dashboard generator:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" dashboard
```

This generates a self-contained HTML file and opens it in the default browser.
Pass `--no-open` to generate without opening.
