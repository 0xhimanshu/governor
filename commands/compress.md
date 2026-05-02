---
description: Automatically compress CLAUDE.md or other memory files with protected-span safety. One-command token savings.
disable-model-invocation: false
---

# Governor Compress

Automatically compress memory files with dense professional prose while strictly protecting critical spans.

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

User experience: one command. Do not ask the user to edit drafts, copy paths, or run follow-up commands unless manual mode is explicitly requested or safety fallback is required.

Automatic execution is internal:

- Run Governor auto mode.
- Rewrite the protected payload internally.
- Finalize, validate, recover if needed, and restore the backup on unrecoverable failure.
- Reject low-savings output with a quality guard.
- If `light` or `medium` fails the quality guard, retry once at the next stronger level.
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
