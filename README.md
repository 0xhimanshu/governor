<p align="center">
  <img src="assets/governor-icon.png" width="128" alt="Governor icon" />
</p>

<h1 align="center">Governor for Claude Code</h1>

<p align="center">
  <strong>Keep long AI coding sessions sharp under quota pressure.</strong>
</p>

<p align="center">
  Now also works with Cursor · Windsurf · Cline · Codex CLI · Gemini CLI · Hermes · DeepSeek
</p>

<p align="center">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-plugin-6D4AFF" />
  <img alt="Cursor" src="https://img.shields.io/badge/Cursor-skill-00A67E" />
  <img alt="Windsurf" src="https://img.shields.io/badge/Windsurf-skill-3B82F6" />
  <img alt="Cline" src="https://img.shields.io/badge/Cline-skill-F59E0B" />
  <img alt="Codex CLI" src="https://img.shields.io/badge/Codex%20CLI-skill-10A37F" />
  <img alt="Gemini CLI" src="https://img.shields.io/badge/Gemini%20CLI-skill-4285F4" />
  <img alt="Hermes" src="https://img.shields.io/badge/Hermes-skill-E44D26" />
  <img alt="DeepSeek" src="https://img.shields.io/badge/DeepSeek-skill-536DFE" />
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.4-black" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-0F766E" />
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#multi-agent-support">Multi-Agent</a> ·
  <a href="#why-governor">Why Governor</a> ·
  <a href="#benchmarks">Benchmarks</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#install">Install</a>
</p>

Governor started as a Claude Code plugin for context hygiene, tool-output
filtering, memory compression, telemetry, and drift guardrails.

**As of v0.2.4, Governor's core behavior — content-aware tool-output filtering
and context hygiene — works with any AI coding agent** via prompt-based skills.
No hooks or MCP required.

> Keep long coding sessions efficient without making the model dumber.

The Claude Code command namespace is `/governor:*`.

## Quick Start

### Claude Code (full plugin)

```bash
bash install.sh --force
```

Restart Claude Code, then run:

```text
/governor:status
/governor:audit
/governor:compress CLAUDE.md
```

### Other Agents (prompt-based skill)

```bash
bash install.sh --project /path/to/project --agents all
```

This copies a Governor rules file into your project for each agent. The rules
teach the agent to self-filter noisy tool output, preserve unique data, and
maintain context hygiene — automatically, every session.

## Multi-Agent Support

Governor works at two levels:

| Agent | Integration | What You Get |
|---|---|---|
| **Claude Code** | Plugin with hooks | Full: auto-filtering, telemetry, compression, drift guard, `/governor:*` commands |
| **Cursor** | `.cursor/rules/governor.mdc` | Self-filtering, compact mode, context hygiene |
| **Windsurf** | `.windsurf/rules/governor.md` | Self-filtering, compact mode, context hygiene |
| **Cline** | `.clinerules/governor.md` | Self-filtering, compact mode, context hygiene |
| **Codex CLI** | `AGENTS.md` | Self-filtering, compact mode, context hygiene |
| **Gemini CLI** | `GEMINI.md` | Self-filtering, compact mode, context hygiene |
| **Hermes** 🆕 | `.hermes.md` | Self-filtering, compact mode, context hygiene |
| **DeepSeek** 🆕 | `.dsh/rules/governor.md` | Self-filtering, compact mode, context hygiene |

**How it works for non-Claude agents:** Governor's rules file teaches the agent
to apply content-aware filtering itself. When tool output has >40% duplicate
lines (test failures, log spam, build warnings), the agent compresses it —
keeping the first error, file:line, and exit code. When output is unique (API
responses, JSON, code), it passes through intact. No external dependencies.

Claude Code gets the deepest integration because it supports plugin hooks.
Other agents get the core behavior via prompt engineering.

## Why Governor

Long coding sessions usually do not fail because the AI writes one extra
paragraph.

They fail because context gets polluted:

- verbose test, build, and MCP output floods the transcript
- bloated recurring files like `CLAUDE.md`, notes, and rules tax every session
- broad prompts trigger repo-wide scans and retries
- scope drift compounds over time

Governor is designed for that failure mode — in Claude Code and beyond.

## What It Does

| Capability | What it does | Where it works |
|---|---|---|
| Tool-output filtering | Compacts noisy output when content is repetitive; preserves unique data | All 8 agents |
| Compact mode | Keeps responses concise and professional | All 8 agents |
| Context hygiene | Avoids re-reads, broad scans, and context waste | All 8 agents |
| Memory compression | Rewrites bloated prompt files into denser, safer forms | Claude Code |
| Telemetry | Reports measured savings, failures, compactions, and waste heat | Claude Code |
| Drift guardrails | Adds planning and scope checks for broad tasks | Claude Code |

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

Governor is aimed at the wider coding session:

- tool-output filtering across all agents
- recurring prompt-file hygiene
- MCP and structured payload handling
- drift-sensitive long sessions
- measured savings and waste heat

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
- Cursor / Windsurf / Cline / Hermes / DeepSeek users who want context hygiene without switching tools
- MCP-heavy workflows (Burp, Playwright, structured tool output)
- prompt-heavy repos with large rules or command docs
- teams using multiple AI agents on the same codebase

Governor is less useful for:

- tiny chats
- already-clean prompt files
- users who only want meme-simple answer shortening

## Features

- **Content-aware tool filtering:** large outputs are only compacted when
  content is repetitive noise (>40% duplicate lines). Unique data — API
  responses, Burp proxy history, curl output, structured JSON — passes through
  unfiltered. Works in all supported agents.
- **Always-on compact mode:** keeps responses concise and professional.
  In Claude Code via hooks; in other agents via rules files.
- **Professional memory compression:** `/governor:compress CLAUDE.md` rewrites
  verbose memory files into dense prose. (Claude Code)
- **Protected-span safety:** code blocks, inline code, paths, URLs, commands,
  env vars, versions, headings, tables, and warnings are preserved.
- **Quality guard:** low-savings compression is rejected and the backup is
  restored instead of pretending success.
- **Inline full-output bypass:** set `GOVERNOR_FULL=1` as an env var in the
  same Bash call to skip compaction without a separate command. Immune to
  parallel-call cancellation.
- **Telemetry ledger:** `/governor:status` reports blocked tokens, failures,
  compactions, and statusline snapshots when available. (Claude Code)
- **Prompt guidance:** vague broad prompts get soft, non-blocking suggestions.
- **Plan and drift guard:** explicit contracts for broad builds, then scope
  checks with `/governor:guard`. (Claude Code)

## Commands

Claude Code plugin commands:

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
| `/governor:benchmark` | Run or explain the V2 benchmark suite |
| `/governor:install-rules` | Copy Governor skills into other-agent projects |

## Install

### Claude Code (Full Plugin)

```bash
gh repo clone 0xhimanshu/governor
cd governor
bash install.sh --force
```

### Other Agents

```bash
bash install.sh --project /path/to/project --agents all
```

Or install for specific agents:

```bash
bash install.sh --project . --agents cursor,windsurf
bash install.sh --project . --agents cline,codex,gemini
bash install.sh --project . --agents hermes,deepseek
```

### Local Development

```bash
claude --plugin-dir .
```

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

## Benchmarking

Use `benchmarks/` for measured comparisons.

Recommended conditions:

- `control`: no token/style plugin
- `caveman`: Caveman enabled as normal
- `governor-hooks`: Governor hooks enabled, memory unchanged
- `governor-compressed`: Governor after `/governor:compress CLAUDE.md`
- `governor-strict`: optional strict-mode run for broad tasks

Run:

```bash
python3 scripts/run_benchmark.py \
  --write-json benchmarks/v2-fixture-results.json \
  --write-md benchmarks/v2-fixture-results.md
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
request, especially for compression, hook, telemetry, agent rules, or benchmark
changes.

## License

MIT. See [LICENSE](LICENSE).
