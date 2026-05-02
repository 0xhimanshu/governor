---
description: Automatically compress CLAUDE.md or other memory files with protected-span safety. One-command token savings.
disable-model-invocation: false
---

# Governor Compress

Automatically compress memory files with dense professional prose while
strictly protecting critical spans.

Usage:

```text
/governor:compress [light|medium|aggressive] [file]
```

Default target: `CLAUDE.md`  
Default level: `medium`

Compression targets:

- `light`: remove filler/repetition; target 15-30% savings outside protected spans.
- `medium`: collapse narrative into decision bullets; target 35-55% savings outside protected spans.
- `aggressive`: keep only rules, facts, commands, risks, decisions; target 50-70% savings outside protected spans.

One-command rule: do not ask the user to edit drafts, copy paths, or run
follow-up commands unless manual mode is explicitly requested or a safety
fallback is required.

Internal flow:

- Run Governor auto mode.
- Parse the returned JSON payload.
- Rewrite the protected payload internally.
- Run the JSON finalize command, then inspect `status`.
- If `status=quality_guard_failed` and `next_level` is present, retry once at
  the stronger level using `retry_auto_command`.
- Finalize, validate, recover if needed, and restore the backup on unrecoverable
  failure.
- Reject low-savings output with a quality guard.
- Return only the result summary.

Manual mode (`manual` or `--manual`) is only for very large files or explicit user request.

Protected spans are never modified:

- Code blocks and inline code.
- Paths, URLs, commands, env vars.
- API names, model names, versions, dates.
- Headings, frontmatter, tables.
- Warnings and irreversible rules.
- Brand and design tokens.

After compression, report:

- Original vs compressed token estimate.
- Memory saved percentage.
- Validation status.
- Quality-guard status.
- Backup location.
