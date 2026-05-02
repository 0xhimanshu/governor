# Multi-turn intent retention pilot

This file records the early pilot referenced in the README `Early Results`
section.

It is a directional result, not a broad claim across all Claude Code tasks.

## Setup

- Same machine
- Fresh Claude CLI Sonnet sessions
- Same static dashboard fixture
- Same four-turn task flow for both conditions:
  1. Write an implementation contract
  2. Implement the approved scope
  3. Receive a conflicting stakeholder request to add a hero/product-page style reskin
  4. Perform a final contract check and smallest corrective edit if needed

Conditions used:

- `control`: no Governor prompt shaping
- `governor-hooks`: Governor compact prompt plus quality-floor and intent-retention guidance

## Result table

| Condition | Output tokens | Cost | Turns | Intent preserved | Obvious regression found |
|---|---:|---:|---:|---|---|
| Control | 10,997 | $0.5169 | 21 | Yes | No |
| Governor | 10,113 | $0.4933 | 22 | Yes | No |
| Delta | -8.0% | -4.6% | +4.8% | Tie | Tie |

Additional token observations:

| Metric | Control | Governor | Delta |
|---|---:|---:|---:|
| Cache creation input tokens | 61,545 | 59,088 | -4.0% |
| Cache read input tokens | 401,604 | 397,902 | -0.9% |

## Interpretation

- Governor reduced output tokens and total cost in this pilot.
- Governor preserved the original implementation contract and rejected later
  scope drift.
- This was not a speed win; Governor took one extra turn.
- The earlier broken-selector regression seen in a previous draft did not appear
  in this rerun.

## Caveats

- `n=1` pilot run
- Static review and syntax checks only; browser-level smoke testing is still pending
- This pilot used a constrained static dashboard fixture, not a large real-world repo
- The CSV companion file is [pilot-intent-run.csv](./pilot-intent-run.csv)
