---
description: Create an implementation contract before broad work, or check current changes against the saved contract.
disable-model-invocation: false
---

# Governor Plan

This command has two phases and picks the right one automatically.

First, check whether this project already has a contract. Run this exactly as
written; do not append `$ARGUMENTS`, which is a task description, not a path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" guard --check
```

- Output starts with `NO_CONTRACT` → run the **Contract phase** below.
- Output starts with `CONTRACT_FOUND` and `$ARGUMENTS` is empty → run the
  **Drift phase** below.
- Output starts with `CONTRACT_FOUND` but `$ARGUMENTS` describes a task that
  clearly differs from the named contract → treat it as new work and run the
  **Contract phase**.

## Contract phase

Create an implementation contract for `$ARGUMENTS`. This is explicit opt-in
governance: do not implement yet.

Use bounded research when facts are current or market/design/API dependent. Keep
research compact and cite sources when browsing.

Return a contract with:

- product concept and audience
- key research facts or assumptions
- brand/theme/storyline
- UI strategy and responsive states
- architecture and data model
- implementation phases
- planned files or file areas
- acceptance tests
- drift guardrails
- stop conditions

At the end, include a JSON contract block with these keys:

```json
{
  "title": "",
  "goal": "",
  "requirements": [],
  "planned_files": [],
  "acceptance_tests": [],
  "drift_guardrails": [],
  "stop_conditions": []
}
```

Also save the same JSON contract into plugin data before returning:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" save-contract --title "SHORT TASK TITLE"
```

Pass the JSON on stdin. The helper generates a safe lowercase slug.

Tell the user implementation should begin only after they approve the contract.
Do not make this command a hidden prerequisite for small focused fixes.

## Drift phase

Run the full guard:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" guard
```

Use its output to report:

- possible scope drift
- planned files not changed yet
- acceptance tests still needed
- smallest safe next step

Keep the guidance concise and action-oriented.
