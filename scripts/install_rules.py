#!/usr/bin/env python3
"""Install Governor always-on rule snippets into a project."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


RULE_MAP = {
    "codex": ("rules/codex/AGENTS.md", "AGENTS.md"),
    "gemini": ("rules/gemini/GEMINI.md", "GEMINI.md"),
    "cursor": ("rules/cursor/.cursor/rules/governor.mdc", ".cursor/rules/governor.mdc"),
    "windsurf": ("rules/windsurf/.windsurf/rules/governor.md", ".windsurf/rules/governor.md"),
    "cline": ("rules/cline/.clinerules/governor.md", ".clinerules/governor.md"),
}


def parse_agents(raw: str) -> list[str]:
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not items or "all" in items:
        return sorted(RULE_MAP)
    unknown = [item for item in items if item not in RULE_MAP]
    if unknown:
        raise ValueError(f"unknown agent(s): {', '.join(unknown)}")
    return items


def install_rules(project: Path, agents: list[str], force: bool = False) -> int:
    root = Path(__file__).resolve().parents[1]
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)

    for agent in agents:
        source_rel, dest_rel = RULE_MAP[agent]
        source = root / source_rel
        dest = project / dest_rel
        if not source.exists():
            print(f"Missing rule source for {agent}: {source}")
            return 1
        if dest.exists() and not force:
            print(f"Skipped existing {agent} rule: {dest} (use --force to overwrite)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        print(f"Installed {agent} rule: {dest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Governor rule snippets into a project")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--agents", default="all", help="comma list: codex,gemini,cursor,windsurf,cline,all")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        agents = parse_agents(args.agents)
    except ValueError as exc:
        print(exc)
        return 2
    return install_rules(args.project, agents, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
