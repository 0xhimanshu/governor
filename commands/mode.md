---
description: Control Governor. Show or set mode (on/off), allow full output for the next diagnostic step, or apply strict governance to the current task.
disable-model-invocation: false
---

# Governor Mode

Read the first word of `$ARGUMENTS` and act accordingly. If `$ARGUMENTS` is
empty, report the current mode.

## No arguments — report current mode

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" mode status
```

## `on` — enable compact professional mode

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" mode compact
```

Confirm briefly: compact mode is on. It reinforces dense professional output on
every prompt while hooks are active.

## `off` — disable compact response mode

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" mode off
```

Confirm briefly: compact response mode is off. Tool filtering and telemetry
hooks still run if configured.

## `full` — full tool output for the next step

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/governor.py" full
```

This sets a one-tool-call override; it does not disable hooks globally.

- Prefer focused commands over broad reruns.
- Do not summarize away critical lines.
- If output is enormous, ask before rerunning with full logs.

Mention that `GOVERNOR_FULL=1 <command>` does the same thing inline, and is
immune to parallel-call cancellation.

## `strict` — stricter governance for the current task

Guidance only: unlike `on`, `off`, and `full`, this stores no state. It shapes
your behavior for the current task and nothing else. Do not carry it into
unrelated future tasks, and do not report it as a persisted mode.

- Require an implementation contract before broad edits.
- Run a drift check after edit phases.
- Avoid broad scans unless justified.
- Stop and report when requirements are ambiguous.

## Notes

Plain language works too and needs no command: "turn off governor" or "enable
governor" is detected by the prompt hook.
