#!/usr/bin/env python3
"""Evaluate one benchmark fixture/condition for decision preservation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import benchmark_lib


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate decision preservation for one fixture condition")
    parser.add_argument("fixture", type=Path, help="path to fixture JSON")
    parser.add_argument("condition", choices=["control", "caveman", "governor"])
    parser.add_argument("--backend", choices=["none", "claude"], default="none")
    parser.add_argument("--model", default="sonnet")
    args = parser.parse_args()

    fixture = benchmark_lib.load_fixture(args.fixture)
    materialized = benchmark_lib.materialize_condition(fixture, args.condition)
    required = benchmark_lib.score_required_items(fixture, materialized.text)
    payload: dict[str, object] = {
        "fixture_id": fixture["id"],
        "condition": args.condition,
        "source_mode": materialized.source_mode,
        "tokens": materialized.tokens,
        **required,
    }

    if args.backend == "claude":
        payload.update(benchmark_lib.run_claude_decision_eval(fixture, materialized, model=args.model))
    else:
        payload["decision_eval_status"] = "not-run"

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
