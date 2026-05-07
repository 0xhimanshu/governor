#!/usr/bin/env python3
"""Shared helpers for Governor V2 benchmark fixtures and scoring."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import governor


BENCHMARKS_DIR = Path(__file__).resolve().parent.parent / "benchmarks"
FIXTURES_DIR = BENCHMARKS_DIR / "fixtures"
CAPTURED_DIR = BENCHMARKS_DIR / "captured"
CAVEMAN_SKILL_PATH = Path.home() / ".claude" / "plugins" / "marketplaces" / "caveman" / "caveman" / "SKILL.md"
CLAUDE_BOOL = {
    "yes": 1.0,
    "true": 1.0,
    "preserved": 1.0,
    "no": 0.0,
    "false": 0.0,
    "lost": 0.0,
}


@dataclass(frozen=True)
class MaterializedCondition:
    fixture_id: str
    condition: str
    text: str
    tokens: int
    source_mode: str
    filtered: bool | None = None
    filter_reason: str | None = None
    hook_ms: float | None = None
    details: dict[str, Any] | None = None


def build_noisy_pytest_ssrf_tail() -> dict[str, Any]:
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
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -vv tests/test_export.py"},
        "tool_response": {"stdout": "\n".join(lines), "stderr": "", "exit_code": 1},
        "duration_ms": 18420,
    }


def build_tsc_warning_root_cause() -> dict[str, Any]:
    lines = ["Files: 281", "Lines: 49321", "Warnings compiling design-system package"]
    for index in range(1, 260):
        lines.append(
            f"node_modules/some-lib/{index}/index.d.ts({index},4): warning TS6385: Deprecated API usage remains for compat layer {index}"
        )
    lines.extend(
        [
            "src/layout/nav.tsx(12,7): error TS6133: 'Link' is declared but its value is never read.",
            'src/settings/theme.ts(84,19): error TS2322: Type \'"compact"\' is not assignable to type \'Density\'.',
            "Found 2 errors in 2 files.",
        ]
    )
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "pnpm exec tsc --noEmit"},
        "tool_response": {"stdout": "\n".join(lines), "stderr": "", "exit_code": 2},
        "duration_ms": 11780,
    }


def build_burp_proxy_history_ssrf() -> dict[str, Any]:
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
    return {
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


def build_playwright_network_auth_redirect() -> dict[str, Any]:
    requests = []
    for index in range(1, 85):
        requests.append(
            {
                "url": f"https://app.example.com/assets/chunk-{index}.js",
                "status": 200,
                "resource_type": "script",
            }
        )
    requests.extend(
        [
            {
                "url": "https://app.example.com/api/admin/export",
                "status": 302,
                "resource_type": "fetch",
                "location": "/login?next=%2Fapi%2Fadmin%2Fexport",
            },
            {
                "url": "https://app.example.com/login?next=%2Fapi%2Fadmin%2Fexport",
                "status": 200,
                "resource_type": "document",
            },
        ]
    )
    return {
        "tool_name": "mcp__playwright__browser_network_requests",
        "tool_input": {"tool": "mcp__playwright__browser_network_requests"},
        "tool_response": {
            "output": {
                "summary": {"request_count": len(requests), "redirects": 1, "auth_failures": 1},
                "console_errors": ["Authorization header missing after redirect replay"],
                "selected_request": {
                    "url": "https://app.example.com/api/admin/export",
                    "status": 302,
                    "location": "/login?next=%2Fapi%2Fadmin%2Fexport",
                    "notes": "Authorization header stripped after redirect; export flow re-enters login.",
                },
                "requests": requests,
            },
            "status": "success",
        },
        "duration_ms": 1540,
    }


def build_large_read_source() -> dict[str, Any]:
    source = [
        "// Debug note: keep full source visible. helper_1, helper_250, and helper_499 differ in ways that matter for the bug.",
        "function helper_1() { return config.cache['item_1']; }",
    ]
    for index in range(2, 250):
        source.append(f"function helper_{index}() {{ return config.cache['item_{index}']; }}")
    source.append("function helper_250() { return config.cache['item_250'] ?? fallbackCache['item_250']; }")
    for index in range(251, 499):
        source.append(f"function helper_{index}() {{ return config.cache['item_{index}']; }}")
    source.append("function helper_499() { return normalizeLegacyKey(config.cache['item_499']); }")
    return {
        "tool_name": "Read",
        "tool_input": {"file_path": "/repo/src/app.js"},
        "tool_response": {"output": "\n".join(source)},
        "duration_ms": 41,
    }


RECIPE_BUILDERS = {
    "noisy_pytest_ssrf_tail": build_noisy_pytest_ssrf_tail,
    "tsc_warning_root_cause": build_tsc_warning_root_cause,
    "burp_proxy_history_ssrf": build_burp_proxy_history_ssrf,
    "playwright_network_auth_redirect": build_playwright_network_auth_redirect,
    "large_read_source": build_large_read_source,
}


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_path"] = str(path)
    return data


def list_fixture_paths(fixtures_dir: Path = FIXTURES_DIR) -> list[Path]:
    return sorted(
        path
        for path in fixtures_dir.glob("*.json")
        if path.is_file() and path.name != "schema.json"
    )


def raw_input_from_spec(spec: dict[str, Any]) -> Any:
    kind = spec.get("kind")
    if kind == "text":
        return str(spec.get("content") or "")
    if kind == "tool_event":
        return spec.get("payload") or {}
    if kind == "tool_event_recipe":
        recipe = str(spec.get("recipe") or "")
        builder = RECIPE_BUILDERS.get(recipe)
        if builder is None:
            raise KeyError(f"Unknown fixture recipe: {recipe}")
        return builder()
    raise ValueError(f"Unsupported fixture input kind: {kind}")


def raw_text_for_fixture(fixture: dict[str, Any]) -> str:
    spec = fixture["input"]
    raw = raw_input_from_spec(spec)
    if spec.get("kind") == "text":
        return str(raw)
    snapshot = governor.build_tool_snapshot(raw)
    if snapshot.raw_text:
        return snapshot.raw_text
    return governor.stringify_response(raw)


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return BENCHMARKS_DIR.parent / path


def capture_path_for_model(base_path: Path, model: str) -> Path:
    if model == "sonnet":
        return base_path
    return base_path.with_name(f"{base_path.stem}.{model}{base_path.suffix}")


def capture_candidate_paths(base_path: Path, model: str | None) -> list[Path]:
    if not model:
        return [base_path]
    model_path = capture_path_for_model(base_path, model)
    if model_path == base_path:
        return [base_path]
    return [model_path, base_path]


def load_capture_text(path: Path) -> tuple[str, dict[str, Any]]:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("text") or ""), payload
    return path.read_text(encoding="utf-8"), {}


def fixture_capture_fingerprint(fixture: dict[str, Any]) -> str:
    payload = {
        "id": fixture.get("id"),
        "category": fixture.get("category"),
        "raw_text": raw_text_for_fixture(fixture),
        "required_items": fixture.get("required_items") or [],
        "decision_prompt": fixture.get("decision_prompt"),
        "correct_action_signals": fixture.get("correct_action_signals") or [],
        "wrong_action_signals": fixture.get("wrong_action_signals") or [],
    }
    return governor.stable_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def materialize_governor_tool_hook(fixture: dict[str, Any], condition_spec: dict[str, Any]) -> MaterializedCondition:
    payload = raw_input_from_spec(fixture["input"])
    snapshot = governor.build_tool_snapshot(payload)
    failed = bool(condition_spec.get("use_failure_hook", governor.exit_is_failure(snapshot.exit_code)))
    started = time.perf_counter()
    should_filter, reason = governor.should_filter_snapshot(snapshot, failed=failed)
    text = governor.summarize_output(snapshot) if should_filter else (snapshot.raw_text or governor.stringify_response(payload))
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return MaterializedCondition(
        fixture_id=fixture["id"],
        condition="governor",
        text=text,
        tokens=governor.estimate_tokens(text),
        source_mode="live_governor_tool_hook",
        filtered=should_filter,
        filter_reason=reason,
        hook_ms=elapsed_ms,
        details={"payload_kind": snapshot.payload_kind, "confidence": snapshot.confidence},
    )


def materialize_condition(fixture: dict[str, Any], condition: str, model: str | None = None) -> MaterializedCondition:
    if condition == "control":
        text = raw_text_for_fixture(fixture)
        return MaterializedCondition(
            fixture_id=fixture["id"],
            condition="control",
            text=text,
            tokens=governor.estimate_tokens(text),
            source_mode="raw",
        )

    condition_spec = (fixture.get("conditions") or {}).get(condition)
    if condition_spec is None:
        raise KeyError(f"Fixture {fixture['id']} has no condition named {condition}")

    source = condition_spec.get("source")
    if source == "inline":
        captured_path = condition_spec.get("captured_path")
        if captured_path:
            base_path = resolve_repo_path(str(captured_path))
            expected_fingerprint = fixture_capture_fingerprint(fixture)
            for path in capture_candidate_paths(base_path, model):
                if not path.exists():
                    continue
                text, metadata = load_capture_text(path)
                actual_fingerprint = metadata.get("fixture_fingerprint")
                capture_model = str(metadata.get("model") or "")
                if actual_fingerprint != expected_fingerprint:
                    continue
                if model and capture_model and capture_model != model:
                    continue
                return MaterializedCondition(
                    fixture_id=fixture["id"],
                    condition=condition,
                    text=text,
                    tokens=governor.estimate_tokens(text),
                    source_mode="captured_file",
                    details={"capture_path": str(path), **metadata},
                )
        text = str(condition_spec.get("content") or "")
        return MaterializedCondition(
            fixture_id=fixture["id"],
            condition=condition,
            text=text,
            tokens=governor.estimate_tokens(text),
            source_mode="reference_inline",
        )
    if source == "governor_tool_hook":
        return materialize_governor_tool_hook(fixture, condition_spec)
    if source == "raw":
        text = raw_text_for_fixture(fixture)
        return MaterializedCondition(
            fixture_id=fixture["id"],
            condition=condition,
            text=text,
            tokens=governor.estimate_tokens(text),
            source_mode="raw",
        )
    raise ValueError(f"Unsupported condition source: {source}")


def _aliases(item: dict[str, Any]) -> list[str]:
    aliases = item.get("aliases")
    if isinstance(aliases, list) and aliases:
        return [str(alias) for alias in aliases if str(alias).strip()]
    text = item.get("text") or item.get("id") or ""
    return [str(text)] if str(text).strip() else []


def match_required_item(text: str, item: dict[str, Any]) -> bool:
    haystack = text.lower()
    if item.get("regex"):
        return re.search(str(item["regex"]), text, re.IGNORECASE | re.MULTILINE) is not None
    return any(alias.lower() in haystack for alias in _aliases(item))


def score_required_items(fixture: dict[str, Any], text: str) -> dict[str, Any]:
    items = fixture.get("required_items") or []
    missing: list[str] = []
    found = 0
    for item in items:
        item_id = str(item.get("id") or item.get("text") or f"item-{found+1}")
        if match_required_item(text, item):
            found += 1
        else:
            missing.append(item_id)
    total = len(items)
    lost = total - found
    vclr = (lost / total) if total else 0.0
    return {
        "required_items_total": total,
        "required_items_found": found,
        "required_items_lost": lost,
        "missing_item_ids": missing,
        "vclr": vclr,
    }


def capture_prompt_for_fixture(fixture: dict[str, Any]) -> str:
    category = str(fixture.get("category") or "")
    guidance_by_category = {
        "tool_log": (
            "Preserve the real failing test, error code, endpoint, host, and the one next-action clue that should guide debugging. "
            "Ignore warning spam unless it changes the next action."
        ),
        "structured_tool": (
            "Preserve the urgent finding, severity, affected endpoint, critical host or URL, and the investigation clue. "
            "Do not waste space on repetitive history rows or asset noise."
        ),
        "memory": (
            "Preserve exact commands, tests, file paths, feature flags, dates, warnings, and non-negotiable constraints. "
            "Do not weaken safety or architecture rules."
        ),
        "intent": (
            "Preserve the approved contract, scope boundaries, planned files, and any explicit rejection of hero or landing-page drift. "
            "Make the correct next decision obvious."
        ),
        "safety": (
            "If the raw context is source code or a safety-sensitive read, do not over-summarize it. "
            "Preserve the structure needed for correct debugging decisions."
        ),
    }
    guidance = guidance_by_category.get(category, "Preserve the exact clues that change the next action.")
    return (
        "You are preparing a compressed context snippet for a coding agent.\n"
        "Compress the raw context aggressively, but keep the technical details that affect the next decision.\n"
        f"{guidance}\n"
        "Return only the compressed context snippet.\n\n"
        "Raw context starts below:\n"
        "-----\n"
        f"{raw_text_for_fixture(fixture)}\n"
        "-----\n"
    )


def load_caveman_system_prompt() -> str:
    return CAVEMAN_SKILL_PATH.read_text(encoding="utf-8")


def load_governor_system_prompt() -> str:
    return (
        "You are generating a Governor benchmark comparator output.\n"
        + governor.governor_response_context("compact")
        + "\nPreserve required details and make the next action obvious. Output only the compacted context snippet."
    )


def build_decision_prompt(fixture: dict[str, Any], candidate_text: str) -> str:
    return (
        "You are evaluating whether a compressed context preserved enough signal for the next decision.\n"
        "Read the candidate context below and answer the task using only that context.\n\n"
        f"Task:\n{fixture.get('decision_prompt', 'What is the correct next action?')}\n\n"
        "Return strict JSON only with this shape:\n"
        '{"next_action":"short answer","evidence":["item1","item2"],"confidence":"low|medium|high"}\n\n'
        "Candidate context starts below:\n"
        "-----\n"
        f"{candidate_text}\n"
        "-----\n"
    )


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def score_decision_answer(fixture: dict[str, Any], answer: str) -> dict[str, Any]:
    answer_lower = answer.lower()
    correct = [signal for signal in fixture.get("correct_action_signals") or [] if str(signal).lower() in answer_lower]
    wrong = [signal for signal in fixture.get("wrong_action_signals") or [] if str(signal).lower() in answer_lower]
    threshold = int(fixture.get("correct_action_threshold") or 1)
    decision_preserved = len(correct) >= threshold and not wrong
    wrong_decision = bool(wrong) or (not decision_preserved and bool(fixture.get("correct_action_signals")))
    return {
        "correct_action_hits": correct,
        "wrong_action_hits": wrong,
        "decision_preserved": 1.0 if decision_preserved else 0.0,
        "wrong_decision": 1.0 if wrong_decision else 0.0,
    }


def run_claude_decision_eval(
    fixture: dict[str, Any],
    materialized: MaterializedCondition,
    model: str = "sonnet",
    timeout_s: int = 45,
) -> dict[str, Any]:
    prompt = build_decision_prompt(fixture, materialized.text)
    cmd = [
        "claude",
        "-p",
        "--settings",
        '{"hooks":{}}',
        "--model",
        model,
        prompt,
    ]
    started = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(materialized.details.get("cwd")) if materialized.details and materialized.details.get("cwd") else None,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return {"decision_eval_status": "claude-not-installed"}
    except subprocess.TimeoutExpired:
        return {"decision_eval_status": "timeout"}

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        status = "claude-error"
        if "Invalid API key" in stderr or "/login" in stderr:
            status = "claude-auth-unavailable"
        return {
            "decision_eval_status": status,
            "decision_eval_ms": elapsed_ms,
            "decision_eval_stderr": stderr[:800],
        }

    payload = extract_json_object(result.stdout)
    if payload is None:
        return {
            "decision_eval_status": "parse-error",
            "decision_eval_ms": elapsed_ms,
            "decision_eval_stdout": result.stdout[:800],
        }

    answer = str(payload.get("next_action") or "")
    score = score_decision_answer(fixture, answer)
    return {
        "decision_eval_status": "ok",
        "decision_eval_ms": elapsed_ms,
        "decision_answer": answer,
        "decision_evidence": payload.get("evidence"),
        "decision_confidence": payload.get("confidence"),
        **score,
    }


def capture_condition_with_claude(
    fixture: dict[str, Any],
    condition: str,
    model: str = "sonnet",
    timeout_s: int = 60,
) -> dict[str, Any]:
    if condition == "caveman":
        try:
            system_prompt = load_caveman_system_prompt()
        except FileNotFoundError:
            return {"capture_status": "caveman-skill-missing"}
        system_source = str(CAVEMAN_SKILL_PATH)
    elif condition == "governor":
        system_prompt = load_governor_system_prompt()
        system_source = "generated:governor_response_context"
    else:
        raise ValueError(f"Unsupported captured condition: {condition}")

    prompt = capture_prompt_for_fixture(fixture)
    cmd = [
        "claude",
        "-p",
        "--append-system-prompt",
        system_prompt,
        "--model",
        model,
        prompt,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return {"capture_status": "claude-not-installed"}
    except subprocess.TimeoutExpired:
        return {"capture_status": "timeout"}

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        combined = (stderr or stdout).lower()
        if "invalid api key" in combined or "/login" in combined:
            return {"capture_status": "claude-auth-unavailable", "stderr": stderr or stdout}
        return {"capture_status": f"claude-error-{result.returncode}", "stderr": stderr or stdout}

    return {
        "capture_status": "ok",
        "text": stdout,
        "model": model,
        "system_source": system_source,
        "fixture_fingerprint": fixture_capture_fingerprint(fixture),
        "prompt": prompt,
    }
