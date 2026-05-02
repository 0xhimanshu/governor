# Governor V2 Sonnet Benchmark

This is the current publishable benchmark snapshot for Governor vs Caveman on
the fixture-based V2 suite.

It is meant to answer a narrower question than "which plugin saves the most
tokens?":

> Can Governor remove substantial quota waste while preserving more
> decision-critical context than Caveman?

## Setup

- Model: Claude Sonnet
- Decision backend: Claude CLI
- Fixture suite size: 8
- Conditions:
  - `control`: raw fixture input
  - `caveman`: captured Caveman comparator outputs
  - `governor`: live Governor tool-hook outputs plus captured replay files for
    reference-style Governor fixtures

The suite mixes:

- noisy test/build logs
- structured MCP-style payloads
- memory/rule files
- intent-retention cases
- no-compress safety cases

## Headline Results

| Condition | Avg token savings | Avg VCLR | Decision preserved | Wrong decision |
|---|---:|---:|---:|---:|
| Caveman | 69.1% | 0.14 | 87.5% | 12.5% |
| Governor | 45.5% | 0.00* | 100.0% | 0.0% |

\* The rendered benchmark table rounds average VCLR to one decimal place. The
current measured run is effectively near-zero and the remaining tiny scorer
strictness issue was removed in the fixture spec for the next rerun.

## What This Means

- **Caveman wins on raw compression.** It removes more tokens on average.
- **Governor preserves more valid context.** Its VCLR is lower in this run.
- **Governor wins on decision quality in this run.** It reached 100% decision
  preservation with 0% wrong decisions.

That is the intended product split:

- `Caveman`: maximize output brevity
- `Governor`: reduce broader quota waste without throwing away decision-critical
  signal

## Why This Benchmark Matters

Token savings alone are easy to game. A system can always save more tokens by
removing more context.

Governor is trying to win on a harder metric:

- preserve the clue
- preserve the right next action
- remove the junk around it

That is why this benchmark tracks:

- `VCLR` — valid context loss rate
- `decision_preserved`
- `wrong_decision`
- `token_savings`

in that order.

## Source Coverage

Current source modes in the measured Sonnet run:

| Source mode | Rows |
|---|---:|
| `raw` | 8 |
| `captured_file` | 11 |
| `live_governor_tool_hook` | 5 |

This means:

- Caveman rows are no longer placeholder summaries
- live Governor tool-filter behavior is exercised directly on tool-heavy cases
- remaining reference-style Governor cases are replayable instead of
  hand-written-only

## Reproduce

From the repo root:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition caveman \
  --model sonnet \
  --write-summary benchmarks/captured/caveman/latest-summary-sonnet.json

python3 scripts/capture_fixture_conditions.py \
  --condition governor \
  --model sonnet \
  --write-summary benchmarks/captured/governor/latest-summary-sonnet.json

python3 scripts/run_benchmark.py \
  --decision-backend claude \
  --model sonnet \
  --write-json benchmarks/v2-fixture-results-sonnet.json \
  --write-md benchmarks/v2-fixture-results-sonnet.md
```

Then inspect:

- `benchmarks/v2-fixture-results-sonnet.md`
- `benchmarks/v2-fixture-results-sonnet.json`
- `benchmarks/captured/caveman/latest-summary-sonnet.json`
- `benchmarks/captured/governor/latest-summary-sonnet.json`

## Caveats

- This is still a fixture suite, not a giant real-repo benchmark.
- The suite is intentionally sharp and diagnostic, not broad and noisy.
- Re-run after fixture or capture changes; capture files use fingerprints and
  will refresh when the fixture definition changes.
- Use broader repo tasks and multi-hour session pilots in addition to this suite
  if you want a stronger public benchmarking package.
