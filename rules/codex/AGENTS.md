# Governor for Codex CLI

## Response Mode
- Start with the answer; skip pleasantries and request restatement.
- Target 90-160 words unless depth requested.
- 3-6 high-signal bullets or compact tables. Debugging: cause → fix → verify.
- No novelty dialect.

## Tool Output Self-Filtering
When you receive tool output (terminal, shell, test runners, build tools):

1. **Repetition check.** If >40% of lines are duplicates (repeated test failures, log lines, build warnings), compress: keep first unique error with file:line, occurrence count, exit code, and summary. Drop duplicates.
2. **Unique content.** If lines are mostly unique (API responses, JSON, code, curl), keep intact. Do NOT summarize unique data.
3. **Threshold.** Only filter output exceeding ~4000 tokens.
4. **Always keep:** error messages, file paths, line numbers, first stack trace, exit codes, test names, assertion details.

## Context Hygiene
- Prefer scoped searches; avoid repo-wide scans unless justified.
- Read only relevant file sections. Don't re-read files already in context.
- For vague prompts, suggest bounded scope before acting.
