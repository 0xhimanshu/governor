#!/usr/bin/env python3
"""Summarize Governor/Caveman benchmark CSV results.

The CSV is intentionally manual-friendly because Claude Code, Caveman, and
other agents expose different telemetry surfaces. The important part is that
every condition records the same fields for the same task prompt.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


NUMERIC_FIELDS = {
    "start_context_pct",
    "peak_context_pct",
    "end_context_pct",
    "start_5h_pct",
    "end_5h_pct",
    "start_7d_pct",
    "end_7d_pct",
    "assistant_output_tokens_est",
    "tool_output_tokens_blocked_est",
    "memory_original_tokens",
    "memory_compressed_tokens",
    "failed_tool_calls",
    "retry_loops",
    "compactions",
    "wall_minutes",
    "quality_score_0_10",
    "requirements_met",
    "requirements_total",
    "critical_errors",
    "unplanned_files_changed",
    "human_interventions",
}

SUCCESS_SCORE = {
    "success": 1.0,
    "pass": 1.0,
    "yes": 1.0,
    "partial": 0.5,
    "mixed": 0.5,
    "failed": 0.0,
    "fail": 0.0,
    "no": 0.0,
}


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip().replace("%", "")
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def fmt(value: float | None, suffix: str = "", precision: int = 1) -> str:
    if value is None:
        return "-"
    if precision == 0:
        return f"{value:.0f}{suffix}"
    return f"{value:.{precision}f}{suffix}"


def average(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return mean(present)


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, Any]] = []
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            parsed: dict[str, Any] = dict(row)
            for field in NUMERIC_FIELDS:
                parsed[field] = parse_number(row.get(field))
            success_raw = (row.get("task_success") or "").strip().lower()
            parsed["success_score"] = SUCCESS_SCORE.get(success_raw)
            parsed["context_growth_pct"] = delta(parsed.get("end_context_pct"), parsed.get("start_context_pct"))
            parsed["five_hour_delta_pct"] = delta(parsed.get("end_5h_pct"), parsed.get("start_5h_pct"))
            parsed["seven_day_delta_pct"] = delta(parsed.get("end_7d_pct"), parsed.get("start_7d_pct"))
            parsed["memory_saved_pct"] = memory_saved(parsed.get("memory_original_tokens"), parsed.get("memory_compressed_tokens"))
            parsed["requirements_coverage"] = coverage(parsed.get("requirements_met"), parsed.get("requirements_total"))
            rows.append(parsed)
        return rows


def delta(end: float | None, start: float | None) -> float | None:
    if end is None or start is None:
        return None
    return end - start


def memory_saved(original: float | None, compressed: float | None) -> float | None:
    if original is None or compressed is None or original <= 0:
        return None
    return 100 * (original - compressed) / original


def coverage(met: float | None, total: float | None) -> float | None:
    if met is None or total is None or total <= 0:
        return None
    return met / total


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        condition = (row.get("condition") or "unknown").strip() or "unknown"
        grouped[condition].append(row)

    summary: dict[str, dict[str, float | None]] = {}
    for condition, items in grouped.items():
        summary[condition] = {
            "runs": float(len(items)),
            "success_rate": average([item.get("success_score") for item in items]),
            "peak_context_pct": average([item.get("peak_context_pct") for item in items]),
            "context_growth_pct": average([item.get("context_growth_pct") for item in items]),
            "five_hour_delta_pct": average([item.get("five_hour_delta_pct") for item in items]),
            "seven_day_delta_pct": average([item.get("seven_day_delta_pct") for item in items]),
            "assistant_output_tokens_est": average([item.get("assistant_output_tokens_est") for item in items]),
            "tool_output_tokens_blocked_est": average([item.get("tool_output_tokens_blocked_est") for item in items]),
            "memory_saved_pct": average([item.get("memory_saved_pct") for item in items]),
            "failed_tool_calls": average([item.get("failed_tool_calls") for item in items]),
            "retry_loops": average([item.get("retry_loops") for item in items]),
            "compactions": average([item.get("compactions") for item in items]),
            "wall_minutes": average([item.get("wall_minutes") for item in items]),
            "quality_score_0_10": average([item.get("quality_score_0_10") for item in items]),
            "requirements_coverage": average([item.get("requirements_coverage") for item in items]),
            "critical_errors": average([item.get("critical_errors") for item in items]),
            "unplanned_files_changed": average([item.get("unplanned_files_changed") for item in items]),
            "human_interventions": average([item.get("human_interventions") for item in items]),
        }
    return summary


def print_overall(summary: dict[str, dict[str, float | None]]) -> None:
    print("# Benchmark Summary")
    print("")
    print("| Condition | Runs | Success | Quality | Req coverage | Peak ctx | Ctx growth | 5h delta | Output toks | Tool toks blocked | Memory saved | Failed tools | Retry loops | Critical errors | Human fixes | Compactions | Minutes |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for condition in sorted(summary):
        item = summary[condition]
        print(
            "| "
            + " | ".join(
                [
                    condition,
                    fmt(item.get("runs"), precision=0),
                    fmt(percent(item.get("success_rate")), "%"),
                    fmt(item.get("quality_score_0_10")),
                    fmt(percent(item.get("requirements_coverage")), "%"),
                    fmt(item.get("peak_context_pct"), "%"),
                    fmt(item.get("context_growth_pct"), "%"),
                    fmt(item.get("five_hour_delta_pct"), "%"),
                    fmt(item.get("assistant_output_tokens_est"), precision=0),
                    fmt(item.get("tool_output_tokens_blocked_est"), precision=0),
                    fmt(item.get("memory_saved_pct"), "%"),
                    fmt(item.get("failed_tool_calls")),
                    fmt(item.get("retry_loops")),
                    fmt(item.get("critical_errors")),
                    fmt(item.get("human_interventions")),
                    fmt(item.get("compactions")),
                    fmt(item.get("wall_minutes")),
                ]
            )
            + " |"
        )


def percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100


def print_pairwise(summary: dict[str, dict[str, float | None]], left: str, right: str) -> None:
    if left not in summary or right not in summary:
        return
    print("")
    print(f"# {right} vs {left}")
    print("")
    print("| Metric | Lower Is Better? | Difference |")
    print("|---|---:|---:|")
    metrics = [
        ("peak_context_pct", True, "%"),
        ("context_growth_pct", True, "%"),
        ("five_hour_delta_pct", True, "%"),
        ("assistant_output_tokens_est", True, ""),
        ("failed_tool_calls", True, ""),
        ("compactions", True, ""),
        ("wall_minutes", True, ""),
        ("success_rate", False, "%"),
        ("quality_score_0_10", False, ""),
        ("requirements_coverage", False, "%"),
        ("critical_errors", True, ""),
        ("retry_loops", True, ""),
        ("unplanned_files_changed", True, ""),
        ("human_interventions", True, ""),
    ]
    for metric, lower_is_better, suffix in metrics:
        left_value = summary[left].get(metric)
        right_value = summary[right].get(metric)
        if left_value is None or right_value is None:
            diff_text = "-"
        else:
            diff = right_value - left_value
            if metric in {"success_rate", "requirements_coverage"}:
                diff *= 100
            diff_text = fmt(diff, suffix)
        print(f"| {metric} | {'yes' if lower_is_better else 'no'} | {diff_text} |")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Governor/Caveman benchmark CSV results")
    parser.add_argument("csv_path", nargs="?", type=Path, default=Path("benchmarks/run-sheet.csv"))
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Benchmark CSV not found: {args.csv_path}")
        print("Copy benchmarks/run-sheet.csv, fill one row per run, then rerun this command.")
        return 1

    rows = load_rows(args.csv_path)
    if not rows:
        print(f"No benchmark rows found in {args.csv_path}.")
        print("Fill one row per task/run/condition, then rerun this command.")
        return 0

    summary = summarize(rows)
    print_overall(summary)
    print_pairwise(summary, "caveman", "governor-compressed")
    print_pairwise(summary, "control", "governor-compressed")
    print("")
    print("Interpretation: lower context, five-hour delta, retries, compactions, and wall time are good only if task success stays equal or improves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
