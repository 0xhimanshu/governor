# Changelog

## 0.2.3 (2026-05-24)

### Added

- **Multi-agent skill support**: Governor rules files now include full
  tool-output self-filtering and context hygiene instructions for Cursor,
  Windsurf, Cline, Codex CLI, and Gemini CLI. Each agent learns to
  self-filter noisy output, preserve unique data, and maintain context
  hygiene — no hooks or MCP required.
- **Content-aware filtering**: tool output is now checked for repetition before
  compacting. Unique content (API responses, Burp proxy history, curl output,
  structured JSON) passes through unfiltered. Only repetitive noise (>40%
  duplicate lines) gets compacted.
- **`GOVERNOR_FULL` env var**: set `GOVERNOR_FULL=1` inline in a Bash command
  to bypass compaction without a separate `/governor:full` call. Immune to
  parallel-call cancellation that could kill the standalone command.

### Fixed

- Tool output from MCP servers (Burp, Playwright, etc.) no longer gets
  incorrectly compacted when the data is unique and needed for analysis.
- `cat` on unique files (e.g., skill definitions, source code) no longer
  triggers compaction via the noisy-command heuristic.

## 0.2.2 (2026-05-13)

### Fixed

- Status dashboard no longer shows negative net savings. Removed misleading
  overhead/net-saved metrics; dashboard now shows only "tokens saved" as the
  headline metric.
- Split-brain ledger: `all_ledger_paths()` discovers and merges ledger files
  from all known locations with `Path.resolve()` dedup and OSError guards.
- Statusline no longer crashes after overhead field removal.

## 0.2.1

### Added

- V2 fixture benchmark suite with VCLR scoring.
- Structured tool filtering for MCP-style payloads.
- No-compress safety boundaries for risky source reads.
- Captured Caveman comparator replays.
- Multi-agent rule snippets (Codex, Gemini, Cursor, Windsurf, Cline).

## 0.1.0

- Initial release: compact mode, memory compression, tool-output filtering,
  telemetry ledger, prompt guidance, plan/drift guard.
