---
description: Explain or summarize Governor vs Caveman performance benchmark results.
disable-model-invocation: false
---

# Governor Benchmark

Use this command when the user wants an actual Governor vs Caveman performance
comparison.

If the user provides a CSV path, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare_benchmarks.py" "${CSV_PATH}"
```

If no CSV is provided, explain the benchmark protocol from
`benchmarks/README.md`:

- Run the same tasks under `control`, `caveman`, `governor-hooks`, and
  `governor-compressed`.
- Use fresh sessions, the same model, the same repo commit, and exact prompt
  text from `benchmarks/tasks.json`.
- Record context %, five-hour usage delta, output tokens, tool tokens blocked,
  failed tool calls, compactions, wall time, and task success.
- Summarize with `scripts/compare_benchmarks.py`.

Keep the response practical. Do not claim Governor beats Caveman until the CSV
contains measured runs.
