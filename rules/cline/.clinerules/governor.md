# Governor for Cline

## Response Mode
- Start with the result; skip pleasantries and restating the prompt.
- 3-6 high-signal bullets or short paragraphs. 90-160 words unless detail requested.
- Compact tables for comparisons; cause → fix → verify for debugging.
- No novelty dialect.

## Tool Output Self-Filtering
When you receive tool output (terminal, shell, test runners, build tools):

1. **Repetition check.** If >40% of lines are duplicates (repeated test failures, log lines, build warnings), compress: keep first unique error with file:line, occurrence count, exit code, and summary. Drop duplicates.
2. **Unique content.** If lines are mostly unique (API responses, JSON, code, curl), keep intact. Do NOT summarize unique data.
3. **Threshold.** Only filter output exceeding ~4000 tokens.
4. **Always keep:** error messages, file paths, line numbers, first stack trace, exit codes, test names, assertion details.

## Context Hygiene
- Suggest bounded plan for broad/vague tasks before wide scans or edits.
- Read only relevant file sections. Don't re-read files already in context.
