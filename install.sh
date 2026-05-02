#!/usr/bin/env bash
# Governor one-line installer.
#
# Local:
#   bash install.sh
#
# Options:
#   --force              overwrite existing installed copy
#   --no-statusline      do not configure Claude Code statusline
#   --project PATH       copy multi-agent rule snippets into a project
#   --agents LIST        comma list: codex,gemini,cursor,windsurf,cline,all
set -euo pipefail

VERSION="0.2.1"
FORCE=0
SETUP_STATUSLINE=1
PROJECT_DIR=""
AGENTS=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --force|-f)
      FORCE=1
      ;;
    --no-statusline)
      SETUP_STATUSLINE=0
      ;;
    --project)
      shift
      PROJECT_DIR="${1:-}"
      ;;
    --agents)
      shift
      AGENTS="${1:-}"
      ;;
    --all-agents)
      AGENTS="all"
      ;;
    --help|-h)
      printf '%s\n' \
        "Governor installer" \
        "Version: $VERSION" \
        "" \
        "Usage: bash install.sh [options]" \
        "" \
        "Options:" \
        "  --force              overwrite existing installed copy" \
        "  --no-statusline      do not configure Claude Code statusline" \
        "  --project PATH       copy multi-agent rule snippets into a project" \
        "  --agents LIST        comma list: codex,gemini,cursor,windsurf,cline,all" \
        "  --all-agents         shorthand for --agents all" \
        "  --help               show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required." >&2
  exit 1
fi

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
MARKETPLACE_DIR="$CLAUDE_DIR/plugins/marketplaces/governor"
SETTINGS="$CLAUDE_DIR/settings.json"

SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi

if [ -z "$SCRIPT_DIR" ]; then
  echo "ERROR: streamed install is not configured with a download URL yet."
  echo "Clone the repo and run: bash install.sh"
  exit 1
fi

if [ -d "$MARKETPLACE_DIR" ] && [ "$FORCE" -ne 1 ]; then
  echo "Governor already installed at $MARKETPLACE_DIR"
  echo "Re-run with --force to overwrite the installed copy."
else
  echo "Installing Governor v$VERSION marketplace copy..."
  mkdir -p "$(dirname "$MARKETPLACE_DIR")"
  rm -rf "$MARKETPLACE_DIR"
  mkdir -p "$MARKETPLACE_DIR"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git' \
      --exclude '.DS_Store' \
      --exclude 'Archive.zip' \
      --exclude '__pycache__' \
      --exclude '*.pyc' \
      --exclude 'benchmarks/latest-*.json' \
      "$SCRIPT_DIR/" "$MARKETPLACE_DIR/"
  else
    (cd "$SCRIPT_DIR" && tar --exclude='.git' --exclude='.DS_Store' --exclude='Archive.zip' --exclude='__pycache__' --exclude='*.pyc' --exclude='benchmarks/latest-*.json' -cf - .) | (cd "$MARKETPLACE_DIR" && tar -xf -)
  fi
  chmod +x "$MARKETPLACE_DIR/bin/governor" "$MARKETPLACE_DIR/bin/governor-statusline" "$MARKETPLACE_DIR/scripts/compare_benchmarks.py" 2>/dev/null || true
  echo "  Installed: $MARKETPLACE_DIR"
fi

echo "Configuring Claude Code marketplace..."
if command -v claude >/dev/null 2>&1; then
  if claude plugin marketplace add "$MARKETPLACE_DIR" >/dev/null 2>&1; then
    echo "  Marketplace added: $MARKETPLACE_DIR"
  else
    echo "  Marketplace may already exist or Claude declined it; continuing."
  fi
  if claude plugin install governor@governor >/dev/null 2>&1; then
    echo "  Plugin installed: governor@governor"
  else
    echo "  Could not auto-install plugin. You can run:"
    echo "    claude plugin marketplace add \"$MARKETPLACE_DIR\""
    echo "    claude plugin install governor@governor"
  fi
else
  echo "  Claude CLI not found. Later run:"
  echo "    claude plugin marketplace add \"$MARKETPLACE_DIR\""
  echo "    claude plugin install governor@governor"
fi

if [ "$SETUP_STATUSLINE" -eq 1 ]; then
  echo "Configuring statusline..."
  mkdir -p "$CLAUDE_DIR"
  if [ ! -f "$SETTINGS" ]; then
    echo '{}' > "$SETTINGS"
  fi
  cp "$SETTINGS" "$SETTINGS.bak"
  GOVERNOR_SETTINGS="$SETTINGS" GOVERNOR_ROOT="$MARKETPLACE_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path

settings_path = Path(os.environ["GOVERNOR_SETTINGS"])
root = Path(os.environ["GOVERNOR_ROOT"])
try:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
except Exception:
    settings = {}

command = f'"{root / "bin" / "governor-statusline"}"'
existing = settings.get("statusLine")
if not existing:
    settings["statusLine"] = {"type": "command", "command": command}
    print("  Statusline configured.")
elif isinstance(existing, dict) and command in str(existing.get("command", "")):
    print("  Statusline already configured.")
else:
    print("  Existing statusline detected; Governor did not overwrite it.")
    print(f"  Add this to your custom statusline if wanted: {command}")

settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY
fi

if [ -n "$PROJECT_DIR" ] || [ -n "$AGENTS" ]; then
  if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$PWD"
  fi
  if [ -z "$AGENTS" ]; then
    AGENTS="all"
  fi
  python3 "$MARKETPLACE_DIR/scripts/install_rules.py" --project "$PROJECT_DIR" --agents "$AGENTS"
fi

echo ""
echo "Governor v$VERSION installed."
echo "Restart Claude Code, then use:"
echo "  /governor:status"
echo "  /governor:on"
echo "  /governor:compress CLAUDE.md"
