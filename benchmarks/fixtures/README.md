# Governor V2 Fixtures

Fixtures are the backbone of the V2 benchmark suite.

The goal is not only to measure token savings, but to measure whether a
condition preserved enough valid context to keep the next decision correct.

## Two Fixture Modes

### 1. `live`

`live` fixtures use a tool-event recipe or payload and let Governor generate its
own compacted output locally.

Use these when the benchmark should exercise real Governor behavior, such as:

- noisy pytest or build logs
- Burp-style MCP payloads
- Playwright network payloads
- safety no-compress cases like `Read`

### 2. `reference`

`reference` fixtures use inline comparator text for one or more conditions.

Use these when the category does not yet have a fully automated generator, such
as:

- memory-file compression examples
- multi-turn intent summaries
- contract or rule-file preservation cases

Reference fixtures are still useful for VCLR scoring, but they are not the same
thing as a live product benchmark. Treat them as scoring fixtures or regression
examples until replaced with real captured outputs.

## Control / Caveman / Governor

- `control` is always implicit raw input.
- `caveman` can use a captured replay file when available, otherwise it falls
  back to inline comparator text.
- `governor` can be either:
  - `governor_tool_hook` for live tool-output generation
  - `inline` for reference fixtures, with optional captured replay files

For publishable Caveman comparisons, generate captured outputs from the same raw
fixture input:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition caveman \
  --model sonnet \
  --write-summary benchmarks/captured/caveman/latest-summary.json
```

Captured outputs are stored under `benchmarks/captured/`.
They are only reused when the capture fingerprint matches the current fixture.

For reference-style Governor fixtures, you can also refresh captured replay
files:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition governor \
  --model sonnet \
  --write-summary benchmarks/captured/governor/latest-summary.json
```

## Required Items

Each fixture must define `required_items`.

These are the concrete context items that must survive compaction, such as:

- failing test name
- critical endpoint
- warning / irreversible rule
- file path
- version or date that changes behavior

VCLR is computed as:

`lost_required_items / total_required_items`

## Decision Scoring

Fixtures may also define:

- `decision_prompt`
- `correct_action_signals`
- `wrong_action_signals`
- `correct_action_threshold`

The optional Claude CLI evaluator asks for the next action using only the
candidate context, then scores the answer against those signals.

## Run

Deterministic VCLR run:

```bash
python3 scripts/run_benchmark.py
```

Optional Claude CLI decision run:

```bash
python3 scripts/run_benchmark.py --decision-backend claude --model sonnet
```

If Claude CLI auth is unavailable, the runner will record that rather than
crashing the whole benchmark.
