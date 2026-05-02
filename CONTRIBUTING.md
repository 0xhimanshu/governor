# Contributing to Governor

Thanks for helping make Governor sharper. This project is small on purpose:
every change should help users save context, avoid noisy tool output, or reduce
retry waste without making Claude Code feel bossy.

## What Good Contributions Look Like

- Clear user value: fewer tokens, cleaner context, safer compression, better
  telemetry, simpler install, or better docs.
- Small scope: focused changes are easier to review and less likely to break
  hooks.
- Honest numbers: benchmark claims must include the prompt set, model, command,
  and raw result file when possible.
- Professional tone: no novelty dialects, hype, or vague marketing claims.
- Low friction: default behavior should guide, not nag. Strict behavior belongs
  behind explicit commands or config.

## Before You Start

1. Check existing issues or open one describing the problem.
2. Keep the change narrow. Avoid unrelated formatting, renames, or rewrites.
3. For behavior changes, describe the user workflow before touching code.

## Local Setup

Clone the repository, then run Governor directly as a local Claude Code plugin:

```bash
gh repo clone 0xhimanshu/claude-code-governor
cd claude-code-governor
claude --plugin-dir .
```

For local install testing:

```bash
bash install.sh --force
```

For other-agent rule snippets:

```bash
bash install.sh --project /path/to/project --agents all
```

## Test Checklist

Run the checks that match your change:

```bash
python3 -m py_compile scripts/*.py
bash -n install.sh
python3 scripts/compare_benchmarks.py benchmarks/run-sheet.csv
```

If you have the Claude CLI authenticated, also run:

```bash
claude plugin validate .
```

For compression changes, test at least one small markdown file and confirm:

- a timestamped backup is created
- protected spans remain intact
- low-savings output is rejected unless explicitly allowed
- recovery restores safe content when validation fails
- the final report includes before/after token estimates

For hook changes, confirm:

- hooks fail quietly when input JSON is missing or incomplete
- `/governor:off` disables compact response guidance
- `/governor:on` re-enables it
- `/governor:full` allows the next Bash command to return full output
- tool summaries keep the first relevant failure, file/line hints, and useful
  tail lines

## Benchmark Contributions

Use `benchmarks/run-sheet.csv` for comparison runs. Good benchmark submissions
include:

- the exact prompt or task
- model name
- condition: `control`, `caveman`, `governor-hooks`,
  `governor-compressed`, or `governor-strict`
- output tokens, context growth, blocked tool-output tokens, failures,
  compactions, and wall time where available
- short notes about anything unusual

Do not present one benchmark as universal proof. Governor should report measured
savings, not fixed magic percentages.

## Pull Request Guidelines

Please include:

- what changed
- why it helps users
- how you tested it
- benchmark data for performance or compression claims
- screenshots only when changing README visuals or public docs

Avoid:

- broad generated rewrites
- drive-by formatting
- hidden behavior changes in docs-only PRs
- claims that are not measured
- changes that make every prompt feel like a planning ceremony

## Code Quality

Governor should feel like a careful local tool:

- prefer deterministic local logic over model calls when possible
- keep model calls reserved for semantic compression, planning, or drift review
- keep hooks fast and defensive
- store local telemetry only under the plugin data directory
- do not leak file contents, logs, or telemetry to external services
- restore backups instead of accepting unsafe compression output

## Security and Privacy

Governor may process memory files, prompts, tool output, and local telemetry.
Treat those as sensitive.

- Do not add network calls without a clear user-controlled reason.
- Do not upload benchmark logs containing secrets or private code.
- Do not compress files that contain secrets.
- Redact tokens, keys, customer names, and private repository paths in issues.

## License

By contributing, you agree that your contribution is released under the MIT
License used by this repository.
