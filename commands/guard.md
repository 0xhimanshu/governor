---
description: Check current changes against the latest approved implementation contract.
disable-model-invocation: false
---

# Governor Guard

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" guard $ARGUMENTS
```

Use the result to report:

- possible scope drift
- planned files not changed yet
- acceptance tests still needed
- smallest safe next step

Keep the guidance concise and action-oriented.

