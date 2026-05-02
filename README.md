<p align="center">
  <img src="assets/governor-icon.png" width="128" alt="Governor icon" />
</p>

<h1 align="center">Governor for Claude Code</h1>

<p align="center">
  <strong>Keep Claude Code concise, clean, and under control.</strong>
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

## Benchmarks

Small local smoke benchmarks, not universal claims. Same machine, same prompt
set, Claude CLI non-interactive runs.

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

Interpretation: Caveman is excellent at style compression. Governor aims for
broader quota control: compact output, recurring-context compression, noisy-tool
filtering, telemetry, and retry reduction.

## Features

- **Always-on compact mode:** `SessionStart` and `UserPromptSubmit` hooks keep
  responses concise in every Claude Code chat.
- **Professional memory compression:** `/governor:compress CLAUDE.md` rewrites
  verbose memory files into dense prose.
- **Protected-span safety:** code blocks, inline code, paths, URLs, commands,
  env vars, versions, headings, tables, and warnings are preserved.
- **Quality guard:** low-savings compression is rejected and the backup is
  restored instead of pretending success.
- **Tool-output filtering:** noisy Bash/test/build output is summarized while
  preserving failure signals.
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
| `/governor:full` | Let the next Bash command return full output |
| `/governor:plan "task"` | Produce an implementation contract before broad work |
| `/governor:guard` | Check current changes against the approved plan |
| `/governor:benchmark` | Explain or summarize benchmark results |
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
