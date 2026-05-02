---
description: Create a compact implementation contract before broad app/site/game/refactor work.
disable-model-invocation: false
---

# Governor Plan

Create an implementation contract for `$ARGUMENTS`. This command is explicit
opt-in governance: do not implement yet.

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
Do not make `/governor:plan` a hidden prerequisite for small focused fixes.
