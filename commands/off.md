---
description: Disable Governor compact response mode while keeping telemetry/tool hooks available.
disable-model-invocation: false
---

# Governor Off

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" mode off
```

Then confirm briefly: Governor compact response mode is off. Tool filtering and
telemetry hooks may still run if configured.
