---
description: Audit recurring context files and suggest usage-limit optimizations.
disable-model-invocation: false
---

# Governor Audit

Audit paths from `$ARGUMENTS`. If no arguments are provided, audit common memory
files such as `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules`, `AGENTS.md`,
Cursor rules, and Windsurf rules.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" audit $ARGUMENTS
```

Summarize:

- total recurring-context estimate
- largest context files
- duplicate/oversized files
- top three recommendations

Prefer low-friction recommendations before governance:

1. compress always-loaded memory
2. split long details into on-demand skills/reference files
3. filter noisy test/build/search output
4. use `/clear` when task changes
5. use `/compact` only when continuing the same task

Keep recommendations helpful, not bossy. Do not require planning unless the user
explicitly asks or the task is broad and risky.
