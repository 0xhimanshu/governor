#!/usr/bin/env python3
"""Capture benchmark condition outputs with Claude CLI for later replay."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import benchmark_lib


def default_capture_path(fixture_id: str, condition: str, model: str) -> Path:
    base = benchmark_lib.CAPTURED_DIR / condition / f"{fixture_id}.json"
    return benchmark_lib.capture_path_for_model(base, model)


def existing_capture_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    metadata: dict[str, str] = {}
    fingerprint = payload.get("fixture_fingerprint")
    model = payload.get("model")
    if fingerprint:
        metadata["fixture_fingerprint"] = str(fingerprint)
    if model:
        metadata["model"] = str(model)
    return metadata


def condition_spec_for_fixture(fixture: dict[str, object], condition: str) -> dict[str, object] | None:
    conditions = fixture.get("conditions") or {}
    if not isinstance(conditions, dict):
        return None
    spec = conditions.get(condition)
    return spec if isinstance(spec, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture fixture condition outputs with Claude CLI")
    parser.add_argument("--fixtures-dir", type=Path, default=benchmark_lib.FIXTURES_DIR)
    parser.add_argument("--fixtures", help="comma-separated fixture ids; default is all fixtures")
    parser.add_argument("--condition", default="caveman", choices=["caveman", "governor"])
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--force", action="store_true", help="overwrite existing capture files")
    parser.add_argument("--write-summary", type=Path, help="write a JSON capture summary to this path")
    args = parser.parse_args()

    fixture_filter = {item.strip() for item in (args.fixtures or "").split(",") if item.strip()}
    fixtures = [benchmark_lib.load_fixture(path) for path in benchmark_lib.list_fixture_paths(args.fixtures_dir)]
    if fixture_filter:
        fixtures = [fixture for fixture in fixtures if fixture["id"] in fixture_filter]

    if not fixtures:
        print("No fixtures matched.", file=sys.stderr)
        return 1

    benchmark_lib.CAPTURED_DIR.mkdir(parents=True, exist_ok=True)
    success = 0
    skipped = 0
    failures = 0
    stopped_early = False
    rows: list[dict[str, str]] = []

    for fixture in fixtures:
        spec = condition_spec_for_fixture(fixture, args.condition)
        if spec is None:
            print(f"skip {fixture['id']}: no {args.condition} condition defined")
            skipped += 1
            rows.append({"fixture_id": fixture["id"], "status": "skipped", "output_path": ""})
            continue
        if args.condition == "governor" and spec.get("source") != "inline":
            print(f"skip {fixture['id']}: governor condition already generated live")
            skipped += 1
            rows.append({"fixture_id": fixture["id"], "status": "skipped-live", "output_path": ""})
            continue

        output_path = default_capture_path(fixture["id"], args.condition, args.model)
        current_fingerprint = benchmark_lib.fixture_capture_fingerprint(fixture)
        if output_path.exists() and not args.force:
            saved_metadata = existing_capture_metadata(output_path)
            saved_fingerprint = saved_metadata.get("fixture_fingerprint")
            saved_model = saved_metadata.get("model")
            if saved_fingerprint == current_fingerprint and saved_model == args.model:
                print(f"skip {fixture['id']}: capture already up to date at {output_path}")
                skipped += 1
                rows.append({"fixture_id": fixture["id"], "status": "skipped", "output_path": str(output_path)})
                continue

        result = benchmark_lib.capture_condition_with_claude(fixture, args.condition, model=args.model)
        status = result.get("capture_status")
        if status != "ok":
            print(f"fail {fixture['id']}: {status}", file=sys.stderr)
            if result.get("stderr"):
                print(result["stderr"], file=sys.stderr)
            failures += 1
            rows.append({"fixture_id": fixture["id"], "status": str(status), "output_path": str(output_path)})
            if status == "claude-auth-unavailable":
                stopped_early = True
                break
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fixture_id": fixture["id"],
            "condition": args.condition,
            "model": result["model"],
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "system_source": result["system_source"],
            "fixture_fingerprint": result["fixture_fingerprint"],
            "text": result["text"],
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"ok {fixture['id']}: {output_path}")
        success += 1
        rows.append({"fixture_id": fixture["id"], "status": "ok", "output_path": str(output_path)})

    summary = {
        "condition": args.condition,
        "model": args.model,
        "fixtures_requested": len(fixtures),
        "captured": success,
        "skipped": skipped,
        "failed": failures,
        "stopped_early": stopped_early,
        "rows": rows,
    }
    if args.write_summary:
        args.write_summary.parent.mkdir(parents=True, exist_ok=True)
        args.write_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nCaptured: {success} ok, {skipped} skipped, {failures} failed.")
    if stopped_early:
        print("Stopped early after Claude CLI auth failure; remaining fixtures were not attempted.", file=sys.stderr)
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
