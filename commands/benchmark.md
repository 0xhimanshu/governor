---
description: Explain or summarize Governor vs Caveman performance benchmark results.
disable-model-invocation: false
---

# Governor Benchmark

Use this command when the user wants an actual Governor vs Caveman performance
comparison or wants to run the V2 benchmark suite.

If the user says `/governor:benchmark refresh-caveman`, refresh captured
Caveman comparator files first, then rerun the V2 suite:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/capture_fixture_conditions.py" \
  --condition caveman \
  --model sonnet \
  --write-summary "${CLAUDE_PLUGIN_ROOT}/benchmarks/captured/caveman/latest-summary.json"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_benchmark.py" \
  --write-json "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.json" \
  --write-md "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.md"
```

If capture refresh reports `claude-auth-unavailable`, stop and explain that the
benchmark can only use inline fallback comparators until Claude CLI is logged in.

If the user says `/governor:benchmark refresh-governor`, refresh the replayable
Governor comparator files for reference-style fixtures, then rerun the V2 suite:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/capture_fixture_conditions.py" \
  --condition governor \
  --model sonnet \
  --write-summary "${CLAUDE_PLUGIN_ROOT}/benchmarks/captured/governor/latest-summary.json"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_benchmark.py" \
  --write-json "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.json" \
  --write-md "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.md"
```

If the user provides a CSV path, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare_benchmarks.py" "${CSV_PATH}"
```

If no CSV is provided, run the V2 fixture suite:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_benchmark.py" \
  --write-json "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.json" \
  --write-md "${CLAUDE_PLUGIN_ROOT}/benchmarks/v2-fixture-results.md"
```

If the user explicitly wants live Caveman captures and Claude CLI auth is
available, refresh them first:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/capture_fixture_conditions.py" \
  --condition caveman \
  --model sonnet \
  --write-summary "${CLAUDE_PLUGIN_ROOT}/benchmarks/captured/caveman/latest-summary.json"
```

Then explain the protocol from `benchmarks/README.md`:

- Run `python3 scripts/run_benchmark.py` for the fixture-based V2 suite.
- Compare the same fixture inputs under `control`, `caveman`, and `governor`.
- Use fresh sessions, the same model, the same repo commit, and exact prompt
  text when using model-judged evaluations.
- Track VCLR, decision preservation, wrong-decision rate, and token savings in
  that order.
- Treat inline comparator text as framework-grade only; captured Caveman files
  are needed for publishable head-to-head claims.

Keep the response practical. Do not claim Governor beats Caveman until the CSV
contains measured runs. Token savings are a win only when success rate,
requirement coverage, quality score, and verification evidence are retained.
For coding benchmarks, call out runtime/selector/event-handler bugs as quality
regressions even if output tokens drop.
