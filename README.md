<p align="center">
  <img src="assets/governor-icon.png" width="128" alt="Governor icon" />
</p>

<h1 align="center">Governor for Claude Code</h1>

<p align="center">
  <strong>Keep Claude Code concise, clean, and under control.</strong>
</p>

<p align="center">
  <code>Version 0.2.1</code>
</p>

Compact professional output, context hygiene, tool-output filtering, and usage
telemetry for Claude Code Max users.

Governor is the serious alternative to style-only token savers. It keeps the
agent concise, shrinks recurring memory files, blocks noisy logs from flooding
context, and adds planning guardrails for broad tasks.

The installed Claude Code command namespace is still `/governor:*`.

## Quick Start

```bash
bash install.sh --force
```

Restart Claude Code, then run:

```text
/governor:status
/governor:audit
/governor:compress CLAUDE.md
```

Governor auto-starts in compact professional mode when the plugin is loaded.
Use `/governor:off` to disable response compression and `/governor:on` to
re-enable it.

## V2 Highlights

- **VCLR benchmark harness:** fixture-based benchmarks now score valid-context
  loss, decision preservation, and wrong-decision rate, not only token counts.
- **Structured tool filtering:** Governor preserves high-signal clues from noisy
  MCP-style payloads such as Burp history and Playwright network dumps.
- **No-compress safety boundaries:** risky source reads and code-heavy tool
  outputs stay intact instead of being compacted into something misleading.
- **Capture-ready Caveman comparisons:** the benchmark suite can now replay real
  captured Caveman comparator outputs when Claude CLI auth is available, while
  falling back cleanly to reference text when it is not.
- **Replayable Governor reference cases:** the last reference-style Governor
  benchmark rows can now be refreshed into captured replay files instead of
  staying hand-written forever.

## Why It Exists

Heavy Claude Code users do not only burn quota on long answers. The bigger
session killers are often:

- bloated always-loaded context such as `CLAUDE.md`, notes, and rules
- huge Bash/test/build output copied into conversation context
- vague prompts that trigger broad scans and repeated failed attempts
- scope drift during long coding tasks
- compactions caused by preventable context growth

Governor attacks those system problems while keeping the interaction
professional and readable.

## Early Results

These are directional pilot results, not universal claims.

Same machine, fresh Claude CLI Sonnet sessions, same multi-turn task, same
starting repo snapshot. This pilot measured an implementation contract, a real
implementation turn, a later conflicting stakeholder request, and a final drift
check.

| Condition | Output Tokens | Cost | Turns | Intent Preserved | Obvious Regression Found |
|---|---:|---:|---:|---|---|
| Control | 10,997 | $0.5169 | 21 | Yes | No |
| Governor | 10,113 | $0.4933 | 22 | Yes | No |
| Delta | -8.0% | -4.6% | +4.8% | Tie | Tie |

What this means:

- Governor reduced output tokens and total cost in this pilot.
- Governor preserved the original implementation contract and rejected later
  scope drift.
- This was not a speed win; Governor took one extra turn.
- This is early evidence, not a broad claim across all Claude Code tasks.

Notes:

- `n=1` pilot run
- Claude CLI Sonnet
- Multi-turn static dashboard task
- Browser-level smoke testing and larger multi-task comparisons are still in
  progress
- Repo-visible pilot artifacts: `benchmarks/pilot-intent-results.md` and
  `benchmarks/pilot-intent-run.csv`

Governor should not be judged by token savings alone. Throwing context away is
easy. The harder problem is reducing avoidable quota burn while preserving
correctness, intent, and useful model behavior over longer sessions.

## Micro Benchmarks

Small local smoke benchmarks. Useful for understanding where savings come from,
but not substitutes for real task runs. These are kept as narrow regression
checks; the V2 fixture suite is the main benchmark surface.

### Output Tokens

Three technical explanation prompts, Sonnet, no tools.

| Condition | Output Tokens | Avg / Prompt | Saved vs Control |
|---|---:|---:|---:|
| Control | 2967 | 989 | 0.0% |
| Caveman | 1634 | 545 | 44.9% |
| Governor | 1320 | 440 | 55.5% |

### Memory Compression

One `project-notes.md` sample from the Caveman compression fixtures.

| Method | Tokens | Saved |
|---|---:|---:|
| Original | 1877 | 0.0% |
| Caveman fixture | 924 | 50.8% |
| Governor medium | 838 | 55.4% |

### Tool Output Filtering

Synthetic noisy `pytest -vv` output with preserved failure lines.

| Raw Output | Filtered Output | Blocked |
|---:|---:|---:|
| 54314 estimated tokens | 1726 estimated tokens | 96.8% |

### Tool Filter Signal Benchmarks (v1.1 micro suite)

Structured/local cases focused on the criticism that compaction can miss the
real clue.

| Case | Filtered? | Blocked | Signal Preserved |
|---|---:|---:|---:|
| Noisy pytest failure buried in long log | Yes | 64.0% | Yes |
| Burp-style MCP payload with large history + one critical finding | Yes | 90.9% | Yes |
| Large `Read` output containing source code | No | 0.0% | Yes |

Repo-visible local artifacts:
- `benchmarks/tool-filter-v1-1-results.md`
- `benchmarks/tool-filter-v1-1-results.json`

### V2 Fixture Suite (Local)

Governor now also has a VCLR-oriented local benchmark harness under
`benchmarks/fixtures/` with 8 starter cases across:

- noisy logs
- structured MCP payloads
- memory/rules files
- multi-turn intent retention
- safety no-compress cases

Recent measured Sonnet run with Claude decision grading:

| Condition | Avg token savings | Avg VCLR | Decision preserved | Wrong decision |
|---|---:|---:|---:|---:|
| Caveman | 69.1% | 0.14 | 87.5% | 12.5% |
| Governor | 45.5% | 0.00 | 100.0% | 0.0% |

What this means:

- Caveman still wins on raw compression.
- Governor preserved more valid context in this run.
- Governor won on decision quality in the latest Sonnet pass.

Important caveat:

- Governor tool cases are generated live.
- Caveman cases are captured replay files.
- Governor memory and intent reference cases can also be refreshed into captured
  replay files.
- Optional Claude CLI decision grading still depends on local CLI auth.
- Refresh the exact numbers after any fixture update or capture refresh.

Repo-visible V2 artifacts:
- `benchmarks/v2-fixture-results.md`
- `benchmarks/v2-fixture-results.json`
- `benchmarks/sonnet-v2-report.md`
- `benchmarks/fixtures/README.md`
- `benchmarks/captured/README.md`

For a cleaner narrative summary, see `benchmarks/sonnet-v2-report.md`.

Reproduce locally:

```bash
python3 scripts/run_benchmark.py \
  --write-json benchmarks/v2-fixture-results.json \
  --write-md benchmarks/v2-fixture-results.md
```

Refresh Caveman captures first when Claude CLI auth is available:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition caveman \
  --model sonnet \
  --write-summary benchmarks/captured/caveman/latest-summary.json
```

Refresh reference-style Governor captures too:

```bash
python3 scripts/capture_fixture_conditions.py \
  --condition governor \
  --model sonnet \
  --write-summary benchmarks/captured/governor/latest-summary.json
```

Interpretation: Caveman is excellent at pure style compression. Governor aims
for broader quota control: compact output, recurring-context compression,
noisy-tool filtering, telemetry, and retry reduction.

## Features

- **Always-on compact mode:** `SessionStart` and `UserPromptSubmit` hooks keep
  responses concise in every Claude Code chat.
- **Professional memory compression:** `/governor:compress CLAUDE.md` rewrites
  verbose memory files into dense prose.
- **Protected-span safety:** code blocks, inline code, paths, URLs, commands,
  env vars, versions, headings, tables, and warnings are preserved.
- **Quality guard:** low-savings compression is rejected and the backup is
  restored instead of pretending success.
- **Tool-output filtering:** large Bash, search, web, task, and MCP-style
  outputs are compacted when confidence is high; risky source reads are left
  alone.
- **Telemetry ledger:** `/governor:status` reports blocked tokens, failures,
  compactions, and statusline snapshots when available.
- **Prompt guidance:** vague broad prompts get soft, non-blocking suggestions.
- **Plan and drift guard:** explicit contracts for broad builds, then scope
  checks with `/governor:guard`.
- **Portable rule snippets:** compact-mode rules for Codex, Gemini, Cursor,
  Windsurf, and Cline.

## Commands

| Command | Purpose |
|---|---|
| `/governor:on` | Enable compact professional response mode |
| `/governor:off` | Disable response compression |
| `/governor:status` | Show usage dashboard and waste heat map |
| `/governor:audit` | Find bloated memory/rule files and context waste |
| `/governor:compress CLAUDE.md` | Compress memory files with protected-span validation |
| `/governor:full` | Let the next diagnostic command return full output |
| `/governor:plan "task"` | Produce an implementation contract before broad work |
| `/governor:guard` | Check current changes against the approved plan |
| `/governor:benchmark` | Run or explain the V2 benchmark suite; use `refresh-caveman` to refresh captured comparators |
| `/governor:install-rules` | Copy compact-mode rules into other-agent projects |

## Install

### Local Development

```bash
claude --plugin-dir .
```

### One-Line Local Install

```bash
bash install.sh --force
```

### Install From This Repository

```bash
gh repo clone 0xhimanshu/governor
cd governor
bash install.sh --force
```

### Install Rule Files For Other Agents

```bash
bash install.sh --project /path/to/project --agents all
```

Supported rule snippets:

| Agent | Rule File |
|---|---|
| Codex | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/governor.mdc` |
| Windsurf | `.windsurf/rules/governor.md` |
| Cline | `.clinerules/governor.md` |

Other agents get compact professional behavior only. Claude Code is the V1
target for hooks, telemetry, statusline, and Bash output filtering.

## How Compression Works

`/governor:compress` is automatic from the user's point of view:

1. Create a timestamped backup.
2. Mark protected spans.
3. Rewrite the file with dense professional prose.
4. Strip markers.
5. Validate protected content.
6. Attempt protected-span recovery if needed.
7. Reject low-savings output and restore the backup if the quality guard fails.
8. Report exact before/after token estimates and backup location.

Compression levels:

| Level | Target |
|---|---|
| `light` | Remove filler/repetition; preserve most rationale |
| `medium` | Collapse narrative into decision bullets |
| `aggressive` | Keep only rules, facts, commands, risks, and decisions |

Set `GOVERNOR_ALLOW_LOW_SAVINGS=1` only if you intentionally want to keep a
low-savings compression result.

## Telemetry

Governor stores a local JSONL ledger under:

```text
~/.claude/plugins/governor/
```

It tracks:

- tool-output tokens blocked
- full-output overrides
- prompt-risk suggestions
- Bash failures
- compactions
- statusline snapshots
- memory compression savings

Prompt caching can reduce usage/cost but does not necessarily reduce context
window occupancy. Governor reports those separately when Claude Code exposes
the data.

## Benchmarking

Use `benchmarks/` for measured comparisons.

Recommended conditions:

- `control`: no token/style plugin
- `caveman`: Caveman enabled as normal
- `governor-hooks`: Governor hooks enabled, memory unchanged
- `governor-compressed`: Governor after `/governor:compress CLAUDE.md`
- `governor-strict`: optional strict-mode run for broad tasks

Fill `benchmarks/run-sheet.csv`, then run:

```bash
python3 scripts/compare_benchmarks.py benchmarks/run-sheet.csv
```

Primary metrics: five-hour usage delta, peak context %, assistant output
tokens, tool-output tokens blocked, failed tool calls, compactions, wall time,
and task success.

## Design Principles

- Helpful by default, strict only when invoked.
- Professional dense prose, never novelty dialect.
- Measure exact savings where possible.
- Treat 1M context as a ceiling, not a target.
- Keep broad planning and drift checks opt-in.
- Restore backups instead of accepting unsafe or low-value compression.

## Gotchas

- If hooks do not fire, `/governor:status` will show little or no telemetry.
- Existing custom statuslines are not overwritten by the installer.
- Compression sends file content through the active Claude Code/model workflow.
  Do not compress secrets or sensitive private files.
- Use `/governor:full` before a diagnostic command when you need unfiltered logs.
- For installed-but-inactive behavior, launch Claude Code with
  `GOVERNOR_DEFAULT_MODE=off`.

## Contributing

Contributions are welcome when they make Governor more useful, safer, or easier
to trust. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull
request, especially for compression, hook, telemetry, or benchmark changes.

## License

MIT. See [LICENSE](LICENSE).
