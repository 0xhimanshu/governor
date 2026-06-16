<p align="center">
  <img src="assets/governor-icon.png" width="128" alt="Governor icon" />
</p>

<h1 align="center">Governor for Claude Code</h1>

<p align="center">
  <strong>Keep long Claude Code sessions sharp under quota pressure.</strong>
</p>

<p align="center">
  Reduce noisy tool output, recurring context bloat, and drift without throwing away the clue.
</p>

<p align="center">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-plugin-6D4AFF" />
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.3-black" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-0F766E" />
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#why-governor">Why Governor</a> ·
  <a href="#benchmarks">Benchmarks</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#install">Install</a>
</p>

Governor is a Claude Code plugin for context hygiene, tool-output filtering,
memory compression, telemetry, and drift guardrails.

It is built for the harder problem than "make the model talk less":

> keep long Claude Code sessions efficient without making the model dumber.

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

## Why Governor

Long Claude Code sessions usually do not fail because Claude writes one extra
paragraph.

They fail because context gets polluted:

- verbose test, build, and MCP output floods the transcript
- bloated recurring files like `CLAUDE.md`, notes, and rules tax every session
- broad prompts trigger repo-wide scans and retries
- scope drift compounds over time

Governor is designed for that failure mode.

## What It Does

| Capability | What it does | Why it matters |
|---|---|---|
| Tool-output filtering | Compacts noisy Bash, search, web, task, and MCP-style output when confidence is high | Keeps logs from dominating context |
| Memory compression | Rewrites bloated recurring prompt files into denser, safer forms | Lowers recurring prompt tax |
| Compact mode | Keeps Claude Code responses concise and professional | Reduces avoidable output bloat |
| Telemetry | Reports measured savings, failures, compactions, and waste heat | Lets you see whether Governor is helping |
| Drift guardrails | Adds planning and scope checks for broad tasks | Helps long sessions stay on track |

## Why It Feels Different

Most token-saving tools optimize one layer:

- shorter replies
- shorter command output

Governor is built for the broader session problem:

- tool spam
- recurring context tax
- MCP-heavy workflows
- long-task drift
- wasted retries

That is why Governor's benchmark story starts with valid-context loss and
decision preservation, not only token counts.

## Benchmarks

### V2 Sonnet Fixture Run

Recent measured Sonnet run with Claude decision grading:

| Condition | Avg token savings | Avg VCLR | Decision preserved | Wrong decision |
|---|---:|---:|---:|---:|
| Caveman | 69.1% | 0.14 | 87.5% | 12.5% |
| Governor | 45.5% | 0.00 | 100.0% | 0.0% |

What this means:

- Caveman still wins on raw compression.
- Governor preserved more valid context in this run.
- Governor won on decision quality in the latest Sonnet pass.

Artifacts:

- `benchmarks/v2-fixture-results.md`
- `benchmarks/v2-fixture-results.json`
- `benchmarks/sonnet-v2-report.md`

### Early Multi-Turn Pilot

Same machine, fresh Claude CLI Sonnet sessions, same multi-turn task, same
starting repo snapshot.

| Condition | Output Tokens | Cost | Turns | Intent Preserved | Obvious Regression Found |
|---|---:|---:|---:|---|---|
| Control | 10,997 | $0.5169 | 21 | Yes | No |
| Governor | 10,113 | $0.4933 | 22 | Yes | No |
| Delta | -8.0% | -4.6% | +4.8% | Tie | Tie |

This was a narrow pilot, not a universal claim. It matters because Governor
kept the implementation contract intact while shaving cost on a real multi-turn
coding task.

### Tool Filter Signal Checks

Structured/local cases focused on the criticism that compaction can miss the
real clue.

| Case | Filtered? | Blocked | Signal Preserved |
|---|---:|---:|---:|
| Noisy pytest failure buried in long log | Yes | 64.0% | Yes |
| Burp-style MCP payload with large history + one critical finding | Yes | 90.9% | Yes |
| Large `Read` output containing source code | No | 0.0% | Yes |

## Compared To

### RTK

RTK is excellent at shrinking shell output.

Governor is aimed at the wider Claude Code session:

- tool-output filtering
- recurring prompt-file hygiene
- MCP and structured payload handling
- drift-sensitive long sessions
- measured savings and waste heat inside Claude Code

### Caveman

Caveman is excellent when the main goal is making Claude talk in fewer tokens.

Governor is built for the broader session problem:

- less tool spam
- less recurring context tax
- less drift
- more decision preservation under pressure

Short version:

> RTK compresses commands. Caveman compresses style. Governor protects the session.

## Best Fit

Governor is best for:

- Claude Code Max users who hit long-session limits
- MCP-heavy workflows
- Burp / Playwright / structured tool output
- prompt-heavy repos with large rules or command docs
- teams who care about drift, reproducibility, and auditability

Governor is less useful for:

- tiny chats
- already-clean prompt files
- users who only want meme-simple answer shortening

## Features

- **Always-on compact mode:** `SessionStart` and `UserPromptSubmit` hooks keep
  responses concise in every Claude Code chat.
- **Professional memory compression:** `/governor:compress CLAUDE.md` rewrites
  verbose memory files into dense prose.
- **Protected-span safety:** code blocks, inline code, paths, URLs, commands,
  env vars, versions, headings, tables, and warnings are preserved.
- **Quality guard:** low-savings compression is rejected and the backup is
  restored instead of pretending success.
- **Content-aware tool filtering:** large outputs are only compacted when
  content is repetitive noise (>40% duplicate lines). Unique data — API
  responses, Burp proxy history, curl output, structured JSON — passes through
  unfiltered. Noisy test failures, repetitive logs, and build spam still get
  compacted.
- **Inline full-output bypass:** set `GOVERNOR_FULL=1` as an env var in the
  same Bash call to skip compaction without a separate command. Immune to
  parallel-call cancellation.
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

### Install Governor Skills For Other Agents

```bash
bash install.sh --project /path/to/project --agents all
```

Governor works as a **prompt-based skill** for any AI coding agent. Each agent
gets a rules file that teaches it to self-filter noisy tool output, preserve
unique data, and maintain context hygiene — no hooks or MCP required.

| Agent | Rule File | What It Does |
|---|---|---|
| Claude Code | Plugin hooks | Full: auto-filtering, telemetry, compression, drift guard |
| Codex CLI | `AGENTS.md` | Self-filtering, compact mode, context hygiene |
| Gemini CLI | `GEMINI.md` | Self-filtering, compact mode, context hygiene |
| Cursor | `.cursor/rules/governor.mdc` | Self-filtering, compact mode, context hygiene |
| Windsurf | `.windsurf/rules/governor.md` | Self-filtering, compact mode, context hygiene |
| Cline | `.clinerules/governor.md` | Self-filtering, compact mode, context hygiene |

Claude Code gets the deepest integration (hooks, telemetry, statusline,
`/governor:*` commands). Other agents get the core behavior — tool-output
self-filtering with content-aware noise detection — via prompt engineering.

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
| `light` | Remove filler and repetition; preserve most rationale |
| `medium` | Collapse narrative into decision bullets |
| `aggressive` | Keep only rules, facts, commands, risks, and decisions |

Set `GOVERNOR_ALLOW_LOW_SAVINGS=1` only if you intentionally want to keep a
low-savings compression result.

## Telemetry

Governor stores a local JSONL ledger. The status command automatically discovers
and merges ledger files from all known locations, including the plugin data
directory set by Claude Code (`CLAUDE_PLUGIN_DATA`) and the manual fallback
path. Deduplication uses resolved paths so symlinks and non-canonical paths
do not cause double-counting.

It tracks:

- tool-output tokens blocked
- full-output overrides
- prompt-risk suggestions
- Bash failures
- compactions
- statusline snapshots
- memory compression savings

Prompt caching can reduce usage and cost but does not necessarily reduce
context window occupancy. Governor reports those separately when Claude Code
exposes the data.

## Benchmarking

Use `benchmarks/` for measured comparisons.

Recommended conditions:

- `control`: no token/style plugin
- `caveman`: Caveman enabled as normal
- `governor-hooks`: Governor hooks enabled, memory unchanged
- `governor-compressed`: Governor after `/governor:compress CLAUDE.md`
- `governor-strict`: optional strict-mode run for broad tasks

Primary metrics:

- valid-context loss rate
- decision preservation
- wrong-decision rate
- five-hour usage delta
- assistant output tokens
- tool-output tokens blocked
- wall time
- task success

Run:

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
- Use `/governor:full` before a diagnostic command when you need unfiltered logs,
  or prefix with `GOVERNOR_FULL=1` to bypass inline.
- For installed-but-inactive behavior, launch Claude Code with
  `GOVERNOR_DEFAULT_MODE=off`.

## Contributing

Contributions are welcome when they make Governor more useful, safer, or easier
to trust. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull
request, especially for compression, hook, telemetry, or benchmark changes.

## License

MIT. See [LICENSE](LICENSE).
