---
description: Temporarily ask Governor to avoid compacting tool output for the next diagnostic step.
disable-model-invocation: false
---

# Governor Full Output

The user wants full output for diagnostics. For the next relevant command:

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" full
```

- Prefer focused commands over broad reruns.
- Do not summarize away critical lines.
- If output is enormous, ask before rerunning with full logs.

This sets a one-tool-call hook override. It does not disable hooks globally.
