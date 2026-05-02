---
description: Enable strict governance behavior for the current task.
disable-model-invocation: false
---

# Governor Strict Mode

For the current task, use stricter governance:

- require an implementation contract before broad edits
- run drift guard after edit phases
- avoid broad scans unless justified
- keep tool output compact
- stop and report when requirements are ambiguous

Strict mode is task-scoped. Do not assume it remains enabled for future unrelated
tasks unless the user says so.

