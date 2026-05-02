# Captured Benchmark Conditions

This directory holds replayable benchmark condition outputs captured from live
Claude CLI runs.

Current intended use:

- `benchmarks/captured/caveman/*.json` stores Caveman-style comparator outputs
  generated from the same raw fixture input.
- `benchmarks/captured/governor/*.json` stores replayable Governor comparator
  outputs for fixtures whose Governor condition is still reference-style.

Each capture file should include:

- `fixture_id`
- `condition`
- `model`
- `captured_at`
- `system_source`
- `fixture_fingerprint`
- `text`

Generate captures with:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition caveman \
  --model sonnet \
  --write-summary benchmarks/captured/caveman/latest-summary.json
```

And for reference-style Governor fixtures:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition governor \
  --model sonnet \
  --write-summary benchmarks/captured/governor/latest-summary.json
```

If Claude CLI auth is unavailable, the script will fail cleanly and leave the
fixture suite on its inline fallback comparator text. On auth failure it stops
early instead of pointlessly retrying every fixture.

Captured files are only reused when their `fixture_fingerprint` matches the
current fixture definition. If a fixture changes, rerun capture refresh.
