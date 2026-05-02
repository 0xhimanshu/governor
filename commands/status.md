---
description: Show Claude Code Governor usage dashboard and waste heat map.
disable-model-invocation: false
---

# Governor Status

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" status
```

Report the compact dashboard:

- tool-output tokens blocked
- soft prompt suggestions
- tool failures observed
- compactions observed
- biggest waste sources
- session and estimated lifetime totals

Keep the response short. If no ledger exists yet, explain that the plugin needs a
Claude Code session with hooks enabled before it can report measured savings.
