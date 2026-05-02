#!/usr/bin/env python3
"""Run Governor tool-filter benchmarks focused on signal preservation.

These cases are designed around the real objections users raised:
- does Governor preserve the clue hidden inside noisy logs?
- does it handle large structured/MCP-style payloads?
- does it avoid compacting risky tool outputs like file reads?
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import governor


ROOT = Path(__file__).resolve().parent
GOVERNOR = ROOT / "governor.py"


@dataclass(frozen=True)
class Case:
    case_id: str
    description: str
    payload: dict
    expect_filtered: bool
    expected_terms: tuple[str, ...]


def build_noisy_pytest_case() -> Case:
    lines = ["============================= test session starts ============================="]
    for index in range(1, 220):
        lines.append(f"tests/test_misc_{index}.py::test_case_{index} PASSED")
        if index % 13 == 0:
            lines.append("DeprecationWarning: pkg_resources is deprecated as an API")
    lines.extend(
        [
            "tests/test_export.py::test_metadata_endpoint_blocked FAILED",
            "__________________ test_metadata_endpoint_blocked __________________",
            "E   AssertionError: SSRF guard missing for metadata endpoint",
            "Traceback (most recent call last):",
            '  File "tests/test_export.py", line 88, in test_metadata_endpoint_blocked',
            '    client.get("/api/admin/export?target=http://169.254.169.254/latest/meta-data/iam/")',
            "RuntimeError: request to 169.254.169.254 should be blocked",
        ]
    )
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -vv tests/test_export.py"},
        "tool_response": {"stdout": "\n".join(lines), "stderr": "", "exit_code": 1},
        "duration_ms": 18420,
    }
    return Case(
        case_id="noisy-pytest",
        description="Large pytest log with the real failure buried near the tail.",
        payload=payload,
        expect_filtered=True,
        expected_terms=(
            "tests/test_export.py::test_metadata_endpoint_blocked",
            "169.254.169.254",
            "RuntimeError: request to 169.254.169.254 should be blocked",
        ),
    )


def build_burp_mcp_case() -> Case:
    history = []
    for index in range(1, 90):
        history.append(
            {
                "method": "GET" if index % 3 else "POST",
                "url": f"https://app.example.com/api/items/{index}?trace={index:04d}",
                "status": 200 if index % 11 else 401,
                "content_length": 2400 + index,
            }
        )
    findings = [
        {
            "id": "BURP-CRIT-17",
            "severity": "critical",
            "confidence": "high",
            "title": "SSRF via export target parameter",
            "affected_endpoint": "/api/admin/export",
            "evidence": "GET /api/admin/export?target=http://169.254.169.254/latest/meta-data/iam/",
            "notes": "Proxy history shows the metadata service is reachable from the server-side export worker.",
        },
        {
            "id": "BURP-MED-04",
            "severity": "medium",
            "confidence": "medium",
            "title": "Missing rate limit on invite endpoint",
            "affected_endpoint": "/api/invite",
        },
    ]
    payload = {
        "tool_name": "mcp__burp__proxy_history",
        "tool_input": {"tool": "mcp__burp__proxy_history", "message": "Summarize latest findings"},
        "tool_response": {
            "output": {
                "project": "customer-portal",
                "summary": {"critical": 1, "high": 0, "medium": 1, "history_items": len(history)},
                "history": history,
                "findings": findings,
                "selected_request": {
                    "method": "GET",
                    "url": "https://app.example.com/api/admin/export?target=http://169.254.169.254/latest/meta-data/iam/",
                    "response_status": 200,
                    "tags": ["ssrf", "metadata", "critical"],
                },
            },
            "status": "success",
        },
        "duration_ms": 2630,
    }
    return Case(
        case_id="burp-mcp-structured",
        description="Burp-style structured payload with huge history and one critical finding.",
        payload=payload,
        expect_filtered=True,
        expected_terms=(
            "critical",
            "/api/admin/export",
            "169.254.169.254",
            "SSRF via export target parameter",
        ),
    )


def build_large_read_case() -> Case:
    source = []
    for index in range(1, 500):
        source.append(f"function helper_{index}() {{ return config.cache['item_{index}']; }}")
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/repo/src/app.js"},
        "tool_response": {"output": "\n".join(source)},
        "duration_ms": 41,
    }
    return Case(
        case_id="large-read-safety",
        description="Large file read should remain untouched because compacting source can hide code.",
        payload=payload,
        expect_filtered=False,
        expected_terms=(),
    )


def cases() -> list[Case]:
    return [build_noisy_pytest_case(), build_burp_mcp_case(), build_large_read_case()]


def extract_summary(stdout: str) -> str:
    if not stdout.strip():
        return ""
    payload = json.loads(stdout)
    hook = payload.get("hookSpecificOutput") or {}
    updated = hook.get("updatedToolOutput") or {}
    if isinstance(updated, dict):
        if isinstance(updated.get("stdout"), str) and updated["stdout"]:
            return updated["stdout"]
        if isinstance(updated.get("output"), str) and updated["output"]:
            return updated["output"]
    return ""


def run_case(case: Case) -> dict[str, object]:
    snapshot = governor.build_tool_snapshot(case.payload)
    started = time.perf_counter()
    result = subprocess.run(
        ["python3", str(GOVERNOR), "hook", "post-tool-use"],
        input=json.dumps(case.payload),
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    summary = extract_summary(result.stdout)
    filtered = bool(summary)
    summary_tokens = governor.estimate_tokens(summary) if summary else snapshot.raw_tokens_estimate
    blocked_tokens = max(0, snapshot.raw_tokens_estimate - summary_tokens)
    terms_found = sum(1 for term in case.expected_terms if term.lower() in summary.lower())
    signal_preserved = terms_found == len(case.expected_terms) if filtered else not case.expect_filtered
    return {
        "case_id": case.case_id,
        "description": case.description,
        "tool_name": snapshot.tool_name,
        "filtered": filtered,
        "expected_filtered": case.expect_filtered,
        "filter_match": filtered == case.expect_filtered,
        "raw_tokens": snapshot.raw_tokens_estimate,
        "summary_tokens": summary_tokens if filtered else None,
        "blocked_tokens": blocked_tokens,
        "blocked_pct": (100 * blocked_tokens / snapshot.raw_tokens_estimate) if filtered and snapshot.raw_tokens_estimate else 0.0,
        "hook_ms": elapsed_ms,
        "expected_terms": len(case.expected_terms),
        "terms_found": terms_found,
        "signal_preserved": signal_preserved,
        "summary": summary,
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def render_markdown(results: list[dict[str, object]]) -> str:
    lines = [
        "# Governor Tool Filter Benchmarks",
        "",
        "Local deterministic v1.1 run. These cases test signal preservation, not just token reduction.",
        "",
        "Live Claude CLI evaluator runs are optional and were not included in this snapshot because",
        "the local Claude CLI auth currently returns `Invalid API key · Please run /login`.",
        "",
        "| Case | Tool | Filtered | Expected | Raw tokens | Summary tokens | Blocked | Hook ms | Terms | Signal preserved |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in results:
        summary_tokens = row["summary_tokens"] if row["summary_tokens"] is not None else "-"
        terms = f"{row['terms_found']}/{row['expected_terms']}"
        blocked = f"{row['blocked_pct']:.1f}%"
        lines.append(
            f"| {row['case_id']} | {row['tool_name']} | "
            f"{'yes' if row['filtered'] else 'no'} | "
            f"{'yes' if row['expected_filtered'] else 'no'} | "
            f"{row['raw_tokens']} | {summary_tokens} | {blocked} | {row['hook_ms']} | {terms} | "
            f"{'yes' if row['signal_preserved'] else 'no'} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Governor tool-filter benchmarks")
    parser.add_argument("--write-md", type=Path, help="optional markdown report path")
    parser.add_argument("--write-json", type=Path, help="optional JSON report path")
    args = parser.parse_args()

    results = [run_case(case) for case in cases()]
    report = render_markdown(results)
    print(report)
    print("")
    for row in results:
        print(f"## {row['case_id']}")
        print(row["description"])
        if row["stderr"]:
            print(f"- stderr: {row['stderr']}")
        if row["filtered"] and row["summary"]:
            print("- summary excerpt:")
            for line in str(row["summary"]).splitlines()[:18]:
                print(f"  {line}")
        print("")

    if args.write_md:
        args.write_md.write_text(report + "\n", encoding="utf-8")
    if args.write_json:
        args.write_json.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if any(not row["filter_match"] or not row["signal_preserved"] or int(row["returncode"]) != 0 for row in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
