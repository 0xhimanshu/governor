---
description: Install Governor compact-mode rule files into a project for Codex, Gemini, Cursor, Windsurf, or Cline.
disable-model-invocation: false
---

# Governor Install Rules

Install always-on compact professional rule snippets into a project.

Usage examples:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_rules.py" --project . --agents all
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_rules.py" --project . --agents codex,cursor
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_rules.py" --project . --agents all --force
```

Explain that these rule files provide compact response behavior for other
agents. They do not install Claude Code telemetry, hooks, statusline, or Bash
output filtering outside Claude Code.
