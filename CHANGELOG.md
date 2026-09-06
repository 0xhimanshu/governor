# Changelog

## 0.2.5 (2026-09-06)

### Changed

- **Commands reduced from 11 to 5.** Governor now leans on automation instead of
  manual invocation:
  - `/governor:mode [on|off|full]` replaces `/governor:on`, `/governor:off`,
    `/governor:full`, and `/governor:strict`. With no argument it reports the
    current mode.
  - `/governor:plan` absorbs `/governor:guard`. It checks for a saved contract
    first, writes one when none exists, and reports drift when one does.
  - `/governor:benchmark` and `/governor:install-rules` are no longer slash
    commands. Use `python3 scripts/run_benchmark.py` and
    `python3 scripts/install_rules.py --project . --agents all --force`.
- Compaction notices now suggest `GOVERNOR_FULL=1` first, since the env var is
  immune to parallel-call cancellation.

### Fixed

- **Implementation contracts are now scoped to the project that created them.**
  `guard` previously picked the newest contract in a global directory, so a
  contract saved in one repository produced fabricated scope-drift reports in
  every other repository. Contracts are stamped with their project path on save
  and only matched back to that project.
- `guard --check` reports contract existence without attempting to parse its
  argument as a file path.

### Added

- Comparison table covering Ponytail, Caveman, and RTK, plus a star-history
  chart in the README.

### Compatibility

- `/governor:on`, `/governor:off`, and `/governor:full` still work when typed
  into an upgraded session: the prompt hook honours them even though the command
  files are gone. `/governor:full` matters most here — a silent no-op would have
  compacted the very output the user asked to see in full.
- `/governor:guard`, `/governor:benchmark`, `/governor:install-rules`, and
  `/governor:strict` have no fallback. Use `/governor:plan`, the two scripts
  above, and `/governor:mode` respectively.
- Contracts saved before 0.2.5 carry no project stamp and are no longer
  auto-selected. Pass the JSON path to `guard` explicitly to use one, or write a
  fresh contract with `/governor:plan`.

## 0.2.4 (2026-09-06)

### Added

- **Hermes support**: Governor rules file for Nous Research's Hermes agent
  via `.hermes.md` — the agent's native rules format.
- **DeepSeek Harness support**: Governor rules file for DeepSeek's `dsh` CLI
  via `.dsh/rules/governor.md` — file-scoped rules with glob activation.
- Governor now supports 8 AI coding agents total.

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
- Compact-mode-only rule snippets for other agents (upgraded to full
  self-filtering skills in 0.2.3).

## 0.1.0

- Initial release: compact mode, memory compression, tool-output filtering,
  telemetry ledger, prompt guidance, plan/drift guard.
