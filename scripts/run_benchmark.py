#!/usr/bin/env python3
"""Run Governor V2 fixture benchmarks with VCLR scoring."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import benchmark_lib


DEFAULT_CONDITIONS = ("control", "caveman", "governor")


def average(values: list[float]) -> float | None:
    return mean(values) if values else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)

    control_by_fixture = {row["fixture_id"]: row for row in rows if row["condition"] == "control"}
    summary: dict[str, dict[str, float | None]] = {}
    for condition, items in grouped.items():
        token_savings: list[float] = []
        filtered_rate: list[float] = []
        decision_preserved: list[float] = []
        wrong_decision: list[float] = []
        for item in items:
            control = control_by_fixture.get(item["fixture_id"])
            if control and control["tokens"] > 0:
                token_savings.append(100 * (control["tokens"] - item["tokens"]) / control["tokens"])
            if item.get("filtered") is not None:
                filtered_rate.append(1.0 if item["filtered"] else 0.0)
            if item.get("decision_eval_status") == "ok":
                decision_preserved.append(float(item.get("decision_preserved") or 0.0))
                wrong_decision.append(float(item.get("wrong_decision") or 0.0))

        summary[condition] = {
            "fixtures": float(len(items)),
            "avg_tokens": average([float(item["tokens"]) for item in items]),
            "avg_token_savings_pct": average(token_savings),
            "avg_vclr": average([float(item["vclr"]) for item in items]),
            "avg_items_lost": average([float(item["required_items_lost"]) for item in items]),
            "filtered_rate": average(filtered_rate),
            "decision_preservation_rate": average(decision_preserved),
            "wrong_decision_rate": average(wrong_decision),
        }
    return summary


def fmt(value: float | None, suffix: str = "", precision: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value:.{precision}f}{suffix}"


def percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100


def render_markdown(rows: list[dict[str, Any]], summary: dict[str, dict[str, float | None]], backend: str) -> str:
    source_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        source_counts[row["source_mode"]] += 1
    lines = [
        "# Governor V2 Benchmark Report",
        "",
        f"Decision backend: `{backend}`",
        "",
        "## Condition Summary",
        "",
        "| Condition | Fixtures | Avg tokens | Avg token savings | Avg VCLR | Avg items lost | Filtered rate | Decision preservation | Wrong decision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in DEFAULT_CONDITIONS:
        item = summary.get(condition)
        if not item:
            continue
        lines.append(
            f"| {condition} | "
            f"{fmt(item['fixtures'], precision=0)} | "
            f"{fmt(item['avg_tokens'], precision=0)} | "
            f"{fmt(item['avg_token_savings_pct'], '%')} | "
            f"{fmt(item['avg_vclr'])} | "
            f"{fmt(item['avg_items_lost'])} | "
            f"{fmt(percent(item['filtered_rate']), '%')} | "
            f"{fmt(percent(item['decision_preservation_rate']), '%')} | "
            f"{fmt(percent(item['wrong_decision_rate']), '%')} |"
        )

    lines.extend(
        [
            "",
            "## Source Coverage",
            "",
            "| Source mode | Rows |",
            "|---|---:|",
        ]
    )
    for source_mode, count in sorted(source_counts.items()):
        lines.append(f"| {source_mode} | {count} |")

    lines.extend(
        [
            "",
            "## Per Fixture",
            "",
            "| Fixture | Category | Condition | Source | Tokens | Lost/Total | VCLR | Filtered | Decision status |",
            "|---|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        filtered = "-"
        if row.get("filtered") is not None:
            filtered = "yes" if row["filtered"] else "no"
        lines.append(
            f"| {row['fixture_id']} | {row['category']} | {row['condition']} | {row['source_mode']} | "
            f"{row['tokens']} | {row['required_items_lost']}/{row['required_items_total']} | "
            f"{row['vclr']:.2f} | {filtered} | {row.get('decision_eval_status', 'not-run')} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Governor V2 benchmark fixtures")
    parser.add_argument("--fixtures-dir", type=Path, default=benchmark_lib.FIXTURES_DIR)
    parser.add_argument("--categories", help="comma-separated category filter")
    parser.add_argument("--fixtures", help="comma-separated fixture id filter")
    parser.add_argument("--decision-backend", choices=["none", "claude"], default="none")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    args = parser.parse_args()

    categories = {item.strip() for item in (args.categories or "").split(",") if item.strip()}
    fixture_ids = {item.strip() for item in (args.fixtures or "").split(",") if item.strip()}

    fixtures = [benchmark_lib.load_fixture(path) for path in benchmark_lib.list_fixture_paths(args.fixtures_dir)]
    if categories:
        fixtures = [fixture for fixture in fixtures if fixture.get("category") in categories]
    if fixture_ids:
        fixtures = [fixture for fixture in fixtures if fixture.get("id") in fixture_ids]

    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        for condition in DEFAULT_CONDITIONS:
            if condition != "control" and condition not in (fixture.get("conditions") or {}):
                continue
            materialized = benchmark_lib.materialize_condition(fixture, condition, model=args.model)
            row: dict[str, Any] = {
                "fixture_id": fixture["id"],
                "category": fixture.get("category"),
                "condition": condition,
                "source_mode": materialized.source_mode,
                "tokens": materialized.tokens,
                "filtered": materialized.filtered,
                "filter_reason": materialized.filter_reason,
                "hook_ms": materialized.hook_ms,
                **benchmark_lib.score_required_items(fixture, materialized.text),
            }
            if args.decision_backend == "claude":
                row.update(benchmark_lib.run_claude_decision_eval(fixture, materialized, model=args.model))
            else:
                row["decision_eval_status"] = "not-run"
            rows.append(row)

    summary = summarize(rows)
    report = render_markdown(rows, summary, args.decision_backend)
    print(report)

    payload = {"rows": rows, "summary": summary, "decision_backend": args.decision_backend}
    if args.write_json:
        args.write_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.write_md:
        args.write_md.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
