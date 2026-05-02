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
  failed tool calls, retry loops, compactions, wall time, task success, quality
  score, requirement coverage, critical errors, and human interventions.
- Summarize with `scripts/compare_benchmarks.py`.

Keep the response practical. Do not claim Governor beats Caveman until the CSV
contains measured runs. Token savings are a win only when success rate,
requirement coverage, quality score, and verification evidence are retained.
For coding benchmarks, call out runtime/selector/event-handler bugs as quality
regressions even if output tokens drop.
