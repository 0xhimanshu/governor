#!/usr/bin/env python3
"""Claude Code Governor helper.

Local, deterministic pieces for the plugin:
- session ledger and savings estimates
- context-file audit and protected-span validation
- safe noisy Bash output summarization for hooks
- soft prompt-risk suggestions
- basic implementation-contract drift checks
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
import time
from pathlib import Path
from typing import Any


PLUGIN_NAME = "governor"
MAX_CAPTURE_CHARS = 160_000
TOOL_FILTER_THRESHOLD = 16_000
SUMMARY_HEAD_LINES = 30
SUMMARY_TAIL_LINES = 40
CONTEXT_TARGET_LINES = 200
COMPRESSION_LEVELS = {"light", "medium", "aggressive"}
GOVERNOR_MODES = {"compact", "normal", "off"}

DEFAULT_MEMORY_FILES = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".claude/CLAUDE.md",
    ".claude/rules",
    ".cursor/rules",
    ".windsurf/rules",
)

NOISY_COMMAND_RE = re.compile(
    r"\b(test|pytest|vitest|jest|mocha|rspec|cargo\s+test|go\s+test|npm\s+test|pnpm\s+test|yarn\s+test|"
    r"build|tsc|eslint|ruff|mypy|grep|rg|find|ls|cat|tail|docker|kubectl|journalctl)\b",
    re.IGNORECASE,
)

HIGH_RISK_PROMPT_RE = re.compile(
    r"\b("
    r"fix (it|errors?|bugs?|everything)|"
    r"make (it|this) better|"
    r"review (everything|this repo|all)|"
    r"build (me )?(an? )?(?:[\w-]+\s+){0,6}(app|game|website|site)|"
    r"implement (everything|the whole thing)|"
    r"refactor (everything|the repo|all)"
    r")\b",
    re.IGNORECASE,
)

FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r"https?://[^\s)>\"]+")
PATH_RE = re.compile(r"(?:\./|\../|/|[A-Za-z]:\\)[\w./\\~:@%+=,-]+")
ENV_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
VERSION_RE = re.compile(r"\b(?:v?\d+\.\d+(?:\.\d+)?|\d{4}-\d{2}-\d{2}|#[0-9]+)\b")
HEADING_RE = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)
COMMAND_RE = re.compile(
    r"`([^`\n]*(?:npm|pnpm|yarn|python3?|node|git|cargo|go|uv|pip|docker|kubectl|make|npx|bun|claude)[^`\n]*)`"
)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):", re.MULTILINE)
WARNING_RE = re.compile(r"^.*\b(?:warning|danger|critical|destructive|irreversible|do not)\b.*$", re.I | re.M)


@dataclasses.dataclass(frozen=True)
class ProtectedSpan:
    kind: str
    value: str


@dataclasses.dataclass(frozen=True)
class PositionedSpan:
    kind: str
    value: str
    start: int
    end: int


def data_dir() -> Path:
    raw = os.environ.get("CLAUDE_PLUGIN_DATA")
    if raw:
        path = Path(raw)
    else:
        path = Path.home() / ".claude" / "plugins" / PLUGIN_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def ledger_path() -> Path:
    return data_dir() / "ledger.jsonl"


def contracts_dir() -> Path:
    path = data_dir() / "contracts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def overrides_path() -> Path:
    return data_dir() / "overrides.json"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    words = re.findall(r"\S+", text)
    return max(1, round(max(len(words) * 1.25, len(text) / 4)))


def token_estimate_label(tokens: int) -> str:
    return f"~{tokens} tokens (approx)"


def slugify(text: str, default: str = "task", max_length: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        slug = default
    return slug[:max_length].strip("-") or default


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        if len(raw) > MAX_CAPTURE_CHARS:
            raw = raw[:MAX_CAPTURE_CHARS]
        return {"raw_stdin": raw}


def write_json(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def append_ledger(event: str, payload: dict[str, Any]) -> None:
    record = {
        "ts": round(time.time(), 3),
        "event": event,
        "session_id": payload.get("session_id") or payload.get("sessionId"),
        "cwd": payload.get("cwd") or os.getcwd(),
        "payload": payload,
    }
    with ledger_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_ledger(limit: int | None = None) -> list[dict[str, Any]]:
    path = ledger_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if limit:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def load_overrides() -> dict[str, Any]:
    path = overrides_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_overrides(overrides: dict[str, Any]) -> None:
    overrides_path().write_text(json.dumps(overrides, indent=2) + "\n", encoding="utf-8")


def default_governor_mode() -> str:
    raw = os.environ.get("GOVERNOR_DEFAULT_MODE", "compact").strip().lower()
    return raw if raw in GOVERNOR_MODES else "compact"


def get_governor_mode() -> str:
    overrides = load_overrides()
    mode = str(overrides.get("mode") or default_governor_mode()).strip().lower()
    return mode if mode in GOVERNOR_MODES else "compact"


def set_governor_mode(mode: str, quiet: bool = False) -> int:
    mode = mode.strip().lower()
    if mode not in GOVERNOR_MODES:
        if not quiet:
            print(f"Invalid Governor mode: {mode}. Use compact, normal, or off.")
        return 2
    overrides = load_overrides()
    overrides["mode"] = mode
    overrides["mode_updated_at"] = timestamp()
    save_overrides(overrides)
    if not quiet:
        print(f"Governor mode: {mode}")
    return 0


def governor_response_context(mode: str | None = None) -> str:
    mode = mode or get_governor_mode()
    if mode == "off":
        return ""
    if mode == "normal":
        return (
            "GOVERNOR MODE ACTIVE — normal. Be professional and avoid filler, but do not force terse answers. "
            "Still preserve tool-output hygiene, planning discipline, and exact safety warnings."
        )
    return (
        "GOVERNOR MODE ACTIVE — compact professional output. Applies every response. "
        "Start with the answer/result. Skip pleasantries, restating the request, and process narration. "
        "For direct technical explanations, target 90-160 words unless the user asks for depth. "
        "Use 3-6 high-signal bullets or short paragraphs; compact tables for comparisons; cause -> fix -> verify for debugging. "
        "Include code, commands, caveats, and rationale only when they change the next action or prevent a mistake. "
        "No caveman, pirate, leet, emoji-compression, or novelty dialect."
    )


def session_start_context() -> str:
    mode = get_governor_mode()
    if mode == "off":
        return "Governor mode off. Hooks still track telemetry and tool-output filtering when configured."
    return (
        f"GOVERNOR MODE ACTIVE — {mode}\n\n"
        + governor_response_context(mode)
        + "\n\n"
        "Quota rules: keep context overhead tiny; label estimates; report exact Governor ledger numbers when available. "
        "Use soft suggestions for vague, broad, or retry-prone prompts. "
        "Do not expose internal compression prepare/finalize steps to the user during /governor:compress unless manual fallback is required."
    )


def set_full_output(count: int = 1) -> int:
    count = max(1, count)
    overrides = load_overrides()
    overrides["full_output_remaining"] = count
    save_overrides(overrides)
    print(f"Governor full-output override enabled for next {count} Bash command(s).")
    return 0


def consume_full_output_override() -> bool:
    overrides = load_overrides()
    remaining = int(overrides.get("full_output_remaining") or 0)
    if remaining <= 0:
        return False
    if remaining == 1:
        overrides.pop("full_output_remaining", None)
    else:
        overrides["full_output_remaining"] = remaining - 1
    save_overrides(overrides)
    return True


def positioned_spans(text: str) -> list[PositionedSpan]:
    spans: list[PositionedSpan] = []
    for regex, kind in (
        (FENCED_CODE_RE, "fenced code block"),
        (INLINE_CODE_RE, "inline code"),
        (URL_RE, "URL"),
        (PATH_RE, "path"),
        (ENV_RE, "env/API token"),
        (VERSION_RE, "number/date/version"),
        (HEADING_RE, "heading"),
        (WARNING_RE, "warning constraint"),
    ):
        spans.extend(PositionedSpan(kind, match.group(0), match.start(), match.end()) for match in regex.finditer(text))

    for match in COMMAND_RE.finditer(text):
        spans.append(PositionedSpan("command", match.group(1), match.start(1), match.end(1)))

    frontmatter = FRONTMATTER_RE.search(text)
    if frontmatter:
        for match in FRONTMATTER_KEY_RE.finditer(frontmatter.group(1)):
            start = frontmatter.start(1) + match.start(1)
            end = frontmatter.start(1) + match.end(1)
            spans.append(PositionedSpan("frontmatter key", match.group(1), start, end))

    spans.sort(key=lambda span: (-(span.end - span.start), span.start))
    selected: list[PositionedSpan] = []
    occupied: list[tuple[int, int]] = []
    for span in spans:
        if any(not (span.end <= start or span.start >= end) for start, end in occupied):
            continue
        selected.append(span)
        occupied.append((span.start, span.end))
    selected.sort(key=lambda span: span.start)
    return selected


def protected_spans(text: str) -> list[ProtectedSpan]:
    spans = [ProtectedSpan(span.kind, span.value) for span in positioned_spans(text)]

    seen: set[tuple[str, str]] = set()
    unique: list[ProtectedSpan] = []
    for span in spans:
        key = (span.kind, span.value)
        if key not in seen:
            seen.add(key)
            unique.append(span)
    return unique


def mark_protected(source: Path, dest: Path | None = None, quiet: bool = False) -> int:
    text = source.read_text(encoding="utf-8", errors="replace")
    spans = positioned_spans(text)
    if dest is None:
        dest = source.with_suffix(source.suffix + ".protected")

    parts: list[str] = []
    cursor = 0
    for index, span in enumerate(spans, start=1):
        parts.append(text[cursor:span.start])
        digest = stable_hash(span.value)
        kind = span.kind.replace('"', "")
        parts.append(f'<protect id="{index}" kind="{kind}" sha="{digest}">')
        parts.append(span.value)
        parts.append("</protect>")
        cursor = span.end
    parts.append(text[cursor:])
    marked = "".join(parts)
    dest.write_text(marked, encoding="utf-8")

    before = estimate_tokens(text)
    after = estimate_tokens(marked)
    if not quiet:
        print(f"Marked protected spans: {len(spans)}")
        print(f"Source estimate: {token_estimate_label(before)}")
        print(f"Marked estimate: {token_estimate_label(after)}")
        print(f"Wrote: {dest}")
    return 0


def strip_protect(source: Path, dest: Path | None = None) -> int:
    text = source.read_text(encoding="utf-8", errors="replace")
    stripped = re.sub(r'<protect\b[^>]*>(.*?)</protect>', lambda match: match.group(1), text, flags=re.DOTALL)
    if dest is None:
        dest = source.with_suffix(source.suffix + ".stripped")
    dest.write_text(stripped, encoding="utf-8")
    print(f"Removed protect markers: {text.count('<protect ')}")
    print(f"Wrote: {dest}")
    return 0


def recover_protected(original: Path, candidate: Path, output: Path | None = None) -> int:
    original_text = original.read_text(encoding="utf-8", errors="replace")
    candidate_text = candidate.read_text(encoding="utf-8", errors="replace")
    original_spans = protected_spans(original_text)
    candidate_spans = positioned_spans(candidate_text)

    if output is None:
        output = candidate
    if not original_spans:
        if output != candidate:
            shutil.copyfile(candidate, output)
        print("No protected spans found in original.")
        return 0
    if len(candidate_spans) < len(original_spans):
        print(
            "Automatic recovery refused: compressed file has fewer protected-span positions "
            f"({len(candidate_spans)}) than original ({len(original_spans)})."
        )
        print("Restore the backup or rerun compression with lighter changes.")
        return 2

    parts: list[str] = []
    cursor = 0
    replacements = 0
    for original_span, candidate_span in zip(original_spans, candidate_spans):
        parts.append(candidate_text[cursor:candidate_span.start])
        if candidate_span.value != original_span.value:
            replacements += 1
        parts.append(original_span.value)
        cursor = candidate_span.end
    parts.append(candidate_text[cursor:])
    recovered = "".join(parts)
    output.write_text(recovered, encoding="utf-8")

    print(f"Recovered protected spans: {replacements}")
    print(f"Wrote: {output}")
    return validate_file(original, output)


def compression_prompt(level: str) -> str:
    return f"""You are compressing a Claude Code memory/instructions file to reduce recurring context usage.

**Compression level:** {level}

**Goal:** Make the rewritten file materially shorter while preserving meaning.

**Style:**
- Professional, dense, and readable; no novelty dialect
- Prefer compact bullets and semicolon-separated facts over narrative paragraphs
- Keep useful headings, but make section bodies much shorter
- Remove filler, background story, repetition, hedging, and obvious rationale
- Do not add new examples, introductions, summaries, or explanatory commentary

**Strict rules (never break these):**
- Do NOT edit, delete, summarize, or modify anything inside `<protect>...</protect>` blocks
- Do NOT remove or weaken any warnings or "do not" rules
- Do NOT invent new rules
- Keep protected blocks in their relative order

**Level guidelines:**
- light: Remove filler/repetition; target 15-30% fewer tokens outside protected blocks
- medium (default): Collapse paragraphs into decision bullets; target 35-55% fewer tokens outside protected blocks
- aggressive: Keep only operational rules, facts, commands, risks, and decisions; target 50-70% fewer tokens outside protected blocks

**Compression tactics:**
- Replace meeting/story prose with `Decision`, `Why`, `Risks`, `Next` bullets
- Convert long explanations into compact cause -> action chains
- Preserve names/dates only when they affect ownership, chronology, or behavior
- Keep concrete decisions, constraints, warnings, commands, paths, APIs, versions, and tests
- Drop phrases like "after extensive discussion", "the team decided", "one concern raised", and "we expect"

Before final output, self-check: if the result is not clearly shorter than the input, rewrite it again more compactly.

Output **only** the full rewritten file content. No explanations, no extra text.

Now rewrite the file:
"""


def compression_workspace(target: Path) -> Path:
    return data_dir() / "compression" / slugify(str(target.resolve()), "target")


def compression_min_savings(level: str, original_tokens: int) -> float:
    if original_tokens < 500:
        return 0.0
    if level == "light":
        return 10.0
    if level == "aggressive":
        return 35.0
    return 25.0


def create_compression_manifest(target: Path, level: str = "medium", quiet: bool = False) -> tuple[int, dict[str, Any] | None]:
    if level not in COMPRESSION_LEVELS:
        print(f"Invalid compression level: {level}. Use one of: {', '.join(sorted(COMPRESSION_LEVELS))}.")
        return 2, None
    if not target.exists() or not target.is_file():
        print(f"Compression target not found: {target}")
        return 1, None

    workspace = compression_workspace(target)
    workspace.mkdir(parents=True, exist_ok=True)
    stamp = timestamp()
    suffix = target.suffix or ".txt"
    backup = workspace / f"{target.stem}.governor-backup.{stamp}{suffix}"
    marked = workspace / f"{target.stem}.governor-marked.{stamp}{suffix}"
    draft = workspace / f"{target.stem}.governor-draft.{stamp}{suffix}"
    prompt_path = workspace / f"{target.stem}.compress-prompt.{stamp}.txt"

    shutil.copyfile(target, backup)
    mark_protected(backup, marked, quiet=quiet)
    shutil.copyfile(marked, draft)
    prompt_path.write_text(compression_prompt(level), encoding="utf-8")

    before_tokens = estimate_tokens(target.read_text(encoding="utf-8", errors="replace"))
    manifest = {
        "target": str(target),
        "level": level,
        "backup": str(backup),
        "marked": str(marked),
        "draft": str(draft),
        "prompt": str(prompt_path),
        "created_at": stamp,
        "original_tokens_estimate": before_tokens,
    }
    (workspace / "latest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0, manifest


def compress_prepare(target: Path, level: str = "medium") -> int:
    rc, manifest = create_compression_manifest(target, level)
    if rc != 0 or manifest is None:
        return rc

    print("Governor compression prepared.")
    print(f"- Target: {manifest['target']}")
    print(f"- Level: {manifest['level']}")
    print(f"- Backup: {manifest['backup']}")
    print(f"- Marked source: {manifest['marked']}")
    print(f"- Draft to edit: {manifest['draft']}")
    print(f"- Prompt: {manifest['prompt']}")
    print(f"- Original estimate: {token_estimate_label(int(manifest['original_tokens_estimate']))}")
    print("")
    print("Automatic mode: rewrite the draft using the prompt, preserve every <protect> block exactly, then run finalize.")
    print(f"Then run: {finalize_command(Path(manifest['target']), Path(manifest['draft']))}")
    return 0


def finalize_command(target: Path, draft: Path) -> str:
    return " ".join(
        shlex.quote(part)
        for part in (
            "python3",
            str(Path(__file__).resolve()),
            "compress",
            str(target),
            "--finalize",
            "--draft",
            str(draft),
        )
    )


def compress_auto(target: Path, level: str = "medium") -> int:
    rc, manifest = create_compression_manifest(target, level, quiet=True)
    if rc != 0 or manifest is None:
        return rc

    prompt = Path(manifest["prompt"]).read_text(encoding="utf-8", errors="replace")
    marked_content = Path(manifest["draft"]).read_text(encoding="utf-8", errors="replace")
    payload = {
        "mode": "governor_compress_auto",
        "instruction": "Rewrite marked_content using prompt. Save only rewritten file content to draft_path, then run finalize_command. Do not show internal paths to the user unless manual fallback or failure occurs.",
        "target": manifest["target"],
        "level": manifest["level"],
        "backup_path": manifest["backup"],
        "draft_path": manifest["draft"],
        "prompt_path": manifest["prompt"],
        "prompt": prompt,
        "marked_content": marked_content,
        "finalize_command": finalize_command(Path(manifest["target"]), Path(manifest["draft"])),
        "original_tokens_estimate": manifest["original_tokens_estimate"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def compress_finalize(target: Path, draft: Path | None = None) -> int:
    workspace = compression_workspace(target)
    manifest_path = workspace / "latest.json"
    if not manifest_path.exists():
        print(f"No compression manifest found for {target}. Run compress --prepare first.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backup = Path(manifest["backup"])
    if draft is None:
        draft = Path(manifest["draft"])
    if not draft.exists():
        print(f"Compression draft not found: {draft}")
        return 1

    strip_protect(draft, target)
    rc = validate_file(backup, target)
    recovered = False
    restored = False
    quality_guard_failed = False
    if rc != 0:
        print("Validation failed; attempting automatic protected-span recovery.")
        rc = recover_protected(backup, target, target)
        recovered = rc == 0
    if rc != 0:
        shutil.copyfile(backup, target)
        restored = True
        print("Recovery failed. Restored original backup to target.")

    after_tokens = estimate_tokens(target.read_text(encoding="utf-8", errors="replace"))
    before_tokens = int(manifest.get("original_tokens_estimate") or 0)
    saved = 100 * (before_tokens - after_tokens) / before_tokens if before_tokens else 0
    min_savings = compression_min_savings(str(manifest.get("level") or "medium"), before_tokens)
    if rc == 0 and min_savings and saved < min_savings and os.environ.get("GOVERNOR_ALLOW_LOW_SAVINGS") != "1":
        quality_guard_failed = True
        shutil.copyfile(backup, target)
        restored = True
        rc = 3
        print(
            f"Quality guard failed: {saved:.1f}% savings is below the "
            f"{min_savings:.0f}% minimum for {manifest.get('level', 'medium')} compression."
        )
        print("Restored original backup. Rerun with a stronger level or set GOVERNOR_ALLOW_LOW_SAVINGS=1 to keep low-savings output.")

    append_ledger(
        "memory_compression_finalized",
        {
            "target": str(target),
            "level": manifest.get("level"),
            "original_tokens_estimate": before_tokens,
            "compressed_tokens_estimate": after_tokens,
            "memory_saved_percent": round(saved, 1),
            "recovery_used": recovered,
            "backup_restored": restored,
            "quality_guard_failed": quality_guard_failed,
            "min_savings_percent": min_savings,
            "success": rc == 0,
        },
    )
    if rc == 0:
        print("Governor compression finalized.")
    elif quality_guard_failed:
        print("Governor compression rejected by quality guard.")
    else:
        print("Governor compression failed; original backup restored.")
    print(f"- Target: {target}")
    print(f"- Compressed estimate: {token_estimate_label(after_tokens)}")
    print(f"- Memory saved: {saved:.1f}%")
    print(f"- Recovery used: {'yes' if recovered else 'no'}")
    print(f"- Backup restored: {'yes' if restored else 'no'}")
    print(f"- Quality guard: {'failed' if quality_guard_failed else 'passed'}")
    return rc


def compress_info(target: Path) -> int:
    manifest_path = compression_workspace(target) / "latest.json"
    if not manifest_path.exists():
        print(f"No compression manifest found for {target}. Run compress --prepare first.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps(manifest, indent=2))
    return 0


def compress_command(target: Path, level: str, prepare: bool, finalize: bool, auto: bool, draft: Path | None) -> int:
    if auto:
        return compress_auto(target, level)
    if finalize:
        return compress_finalize(target, draft)
    return compress_prepare(target, level)


def validate_file(original: Path, compressed: Path) -> int:
    before = original.read_text(encoding="utf-8", errors="replace")
    after = compressed.read_text(encoding="utf-8", errors="replace")
    missing = [span for span in protected_spans(before) if span.value not in after]
    before_tokens = estimate_tokens(before)
    after_tokens = estimate_tokens(after)
    saved = 100 * (before_tokens - after_tokens) / before_tokens if before_tokens else 0

    print(f"Original estimate: {token_estimate_label(before_tokens)}")
    print(f"Compressed estimate: {token_estimate_label(after_tokens)}")
    print(f"Memory saved: {saved:.1f}%")
    if missing:
        print("Validation failed. Missing protected spans:")
        for span in missing[:80]:
            value = span.value.replace("\n", "\\n")
            if len(value) > 160:
                value = value[:157] + "..."
            print(f"- {span.kind}: {value}")
        if len(missing) > 80:
            print(f"- ... {len(missing) - 80} more")
        return 2
    print("Validation passed. Protected spans preserved.")
    return 0


def discover_memory_paths(paths: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    raw_paths = paths or [Path(p) for p in DEFAULT_MEMORY_FILES]
    for path in raw_paths:
        if path.is_dir():
            candidates.extend(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in {".md", ".txt", ".mdx"}
            )
        elif path.is_file():
            candidates.append(path)
    return sorted(set(candidates))


def audit(paths: list[Path]) -> int:
    files = discover_memory_paths(paths)
    if not files:
        print("No memory/context files found. Pass paths such as CLAUDE.md or .claude/rules.")
        return 1

    rows = []
    total_tokens = 0
    for file in files:
        text = file.read_text(encoding="utf-8", errors="replace")
        tokens = estimate_tokens(text)
        total_tokens += tokens
        lines = text.count("\n") + 1 if text else 0
        protected = len(protected_spans(text))
        duplicate_lines = duplicate_line_count(text)
        severity = "ok"
        if lines > CONTEXT_TARGET_LINES or tokens > 3000:
            severity = "high"
        elif duplicate_lines > 8 or tokens > 1500:
            severity = "medium"
        rows.append((tokens, file, lines, duplicate_lines, protected, severity))

    rows.sort(reverse=True)
    print("Claude Code Governor audit")
    print(f"Total recurring-context estimate: {token_estimate_label(total_tokens)}")
    print("")
    for tokens, file, lines, dupes, protected, severity in rows:
        print(f"- {file}: {token_estimate_label(tokens)}, {lines} lines, {dupes} repeated lines, {protected} protected spans [{severity}]")

    print("")
    print("Prioritized recommendations:")
    print("1. Keep always-loaded CLAUDE.md/rules under ~200 dense lines when possible.")
    print("2. Move detailed runbooks/examples into on-demand skills or linked reference files.")
    print("3. Compress verbose preference prose at light/medium level before trying aggressive mode.")
    print("4. Keep warnings, commands, paths, API names, versions, and design tokens exact.")
    print("5. Use /governor:plan before broad app/game/site builds, then /governor:guard after edits.")
    return 0


def duplicate_line_count(text: str) -> int:
    normalized = []
    for line in text.splitlines():
        item = re.sub(r"\s+", " ", line.strip()).lower()
        if len(item) >= 24:
            normalized.append(item)
    seen: set[str] = set()
    duplicates = 0
    for item in normalized:
        if item in seen:
            duplicates += 1
        else:
            seen.add(item)
    return duplicates


def status() -> int:
    lifetime_records = load_ledger()
    records = lifetime_records[-500:]
    if not records:
        print("Claude Code Governor: no ledger events yet.")
        print("Run a session with the plugin enabled, then use /governor:status again.")
        return 0

    tool_blocked = 0
    prompt_suggestions = 0
    failures = 0
    compactions = 0
    by_command: dict[str, int] = {}
    latest_statusline: dict[str, Any] | None = None

    for record in records:
        event = record.get("event")
        payload = record.get("payload", {})
        if event == "tool_output_filtered":
            blocked = int(payload.get("tokens_blocked_estimate") or 0)
            tool_blocked += blocked
            command = (payload.get("command") or "unknown").split()[0]
            by_command[command] = by_command.get(command, 0) + blocked
        elif event == "prompt_risk_suggested":
            prompt_suggestions += 1
        elif event == "tool_failure":
            failures += 1
        elif event == "pre_compact":
            compactions += 1
        elif event == "statusline_snapshot" and any(value is not None for value in payload.values()):
            latest_statusline = payload

    lifetime_blocked = sum(
        int((record.get("payload") or {}).get("tokens_blocked_estimate") or 0)
        for record in lifetime_records
        if record.get("event") in {"tool_output_filtered", "tool_failure_summary"}
    )
    lifetime_prompt_suggestions = sum(1 for record in lifetime_records if record.get("event") == "prompt_risk_suggested")
    lifetime_compactions = sum(1 for record in lifetime_records if record.get("event") == "pre_compact")

    print("Claude Code Governor status")
    print(f"- Session window events: {len(records)}")
    print(f"- Session tool-output tokens blocked: ~{tool_blocked}")
    print(f"- Session soft prompt suggestions: {prompt_suggestions}")
    print(f"- Session Bash failures observed: {failures}")
    print(f"- Session compactions observed: {compactions}")
    print(f"- Estimated lifetime tokens blocked: ~{lifetime_blocked}")
    print(f"- Estimated lifetime prompt suggestions: {lifetime_prompt_suggestions}")
    print(f"- Estimated lifetime compactions observed: {lifetime_compactions}")
    if latest_statusline:
        print("- Latest live statusline:")
        fields = latest_statusline if "five_hour" in latest_statusline or "context" in latest_statusline else compact_statusline_fields(latest_statusline)
        for label, value in fields.items():
            if value is not None:
                print(f"  - {label}: {value}")
    if by_command:
        print("- Session waste heat map:")
        for command, tokens in sorted(by_command.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"  - {command}: ~{tokens} tokens blocked")
    print("")
    print("Note: cached tokens can reduce billing/limits but still occupy context. Governor reports context and usage separately when statusline data is available.")
    return 0


def nested_get(data: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = data
        found = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found:
            return current
    return None


def compact_statusline_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": nested_get(data, "model.display_name", "model.name", "model"),
        "context": nested_get(data, "context_window.current_usage", "context.current_usage", "context_percentage"),
        "context_tokens": nested_get(data, "context_window.current_tokens", "context.current_tokens", "tokens.context"),
        "session_tokens": nested_get(data, "session.total_tokens", "usage.total_tokens", "tokens.total"),
        "cache_read": nested_get(data, "tokens.cache_read", "cache_read_tokens", "usage.cache_read_tokens"),
        "cache_write": nested_get(data, "tokens.cache_write", "cache_write_tokens", "usage.cache_write_tokens"),
        "five_hour": nested_get(data, "rate_limits.five_hour.percent_used", "rate_limits.five_hour", "five_hour_usage"),
        "seven_day": nested_get(data, "rate_limits.seven_day.percent_used", "rate_limits.seven_day", "seven_day_usage"),
    }


def statusline() -> int:
    data = read_stdin_json()
    fields = compact_statusline_fields(data)
    append_ledger("statusline_snapshot", fields)
    records = load_ledger(limit=200)
    blocked = sum(
        int((record.get("payload") or {}).get("tokens_blocked_estimate") or 0)
        for record in records
        if record.get("event") == "tool_output_filtered"
    )

    pieces = ["Governor"]
    mode = get_governor_mode()
    if mode != "off":
        pieces.append(mode)
    if fields.get("context") is not None:
        pieces.append(f"ctx {fields['context']}")
    elif fields.get("context_tokens") is not None:
        pieces.append(f"ctxTok {fields['context_tokens']}")
    if fields.get("five_hour") is not None:
        pieces.append(f"5h {fields['five_hour']}")
    if fields.get("seven_day") is not None:
        pieces.append(f"7d {fields['seven_day']}")
    if blocked:
        pieces.append(f"blocked ~{blocked}t")
    print(" | ".join(str(piece) for piece in pieces))
    return 0


def summarize_output(command: str, stdout: str, stderr: str, exit_code: Any) -> str:
    combined = []
    if stdout:
        combined.append(("stdout", stdout))
    if stderr:
        combined.append(("stderr", stderr))

    error_lines = []
    failure_markers = re.compile(
        r"(error|failed|failure|exception|traceback|panic|assert|expected|received|"
        r"\bFAIL\b|\bFAILED\b|✕|×|[\w./-]+:\d+(?::\d+)?)",
        re.IGNORECASE,
    )
    total_failure_lines = 0
    for label, text in combined:
        for line in text.splitlines():
            if failure_markers.search(line):
                total_failure_lines += 1
                if len(error_lines) >= 80:
                    continue
                error_lines.append(f"{label}: {line}")

    def clipped_lines(text: str, head: int, tail: int) -> list[str]:
        lines = text.splitlines()
        if len(lines) <= head + tail:
            return lines
        return lines[:head] + [f"... clipped {len(lines) - head - tail} lines ..."] + lines[-tail:]

    summary = [
        "Claude Code Governor compacted noisy Bash output.",
        f"Command: `{command}`",
        f"Exit code: {exit_code}",
        f"Failure/error lines detected: {total_failure_lines}",
        "Full output is available in the terminal/transcript if needed.",
        "",
    ]
    if error_lines:
        summary.append("Relevant failure/error lines:")
        summary.extend(f"- {line}" for line in error_lines[:60])
        summary.append("")

    if stdout:
        summary.append("Stdout excerpt:")
        summary.extend(clipped_lines(stdout, SUMMARY_HEAD_LINES, SUMMARY_TAIL_LINES))
        summary.append("")
    if stderr:
        summary.append("Stderr excerpt:")
        summary.extend(clipped_lines(stderr, SUMMARY_HEAD_LINES, SUMMARY_TAIL_LINES))

    return "\n".join(summary).strip()


def hook_prompt(data: dict[str, Any]) -> int:
    prompt = str(data.get("prompt") or data.get("user_prompt") or data.get("message") or "")
    prompt_lower = prompt.strip().lower()

    if re.search(r"\b(stop|disable|deactivate|turn off)\b.*\bgovernor\b|\bnormal mode\b", prompt_lower):
        set_governor_mode("off", quiet=True)
    elif re.search(r"\b(activate|enable|turn on|start)\b.*\bgovernor\b", prompt_lower):
        set_governor_mode("compact", quiet=True)
    elif prompt_lower.startswith("/governor:off"):
        set_governor_mode("off", quiet=True)
    elif prompt_lower.startswith("/governor:on"):
        set_governor_mode("compact", quiet=True)

    contexts = []
    response_context = governor_response_context()
    if response_context:
        contexts.append(response_context)

    if prompt and HIGH_RISK_PROMPT_RE.search(prompt):
        append_ledger("prompt_risk_suggested", {"prompt_hash": stable_hash(prompt), "cwd": data.get("cwd"), "session_id": data.get("session_id")})
        contexts.append(
            "Governor prompt-risk suggestion: this prompt can trigger broad scanning or retry loops. "
            "Offer a quick choice instead of blocking: "
            "(a) make a compact plan first, "
            "(b) narrow to likely files/tests first, or "
            "(c) proceed as-is for speed. "
            "If the user already gave enough scope, proceed normally."
        )

    if not contexts:
        return 0

    write_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n\n".join(contexts),
            }
        }
    )
    return 0


def hook_session_start(data: dict[str, Any]) -> int:
    append_ledger("session_start", {"session_id": data.get("session_id"), "cwd": data.get("cwd"), "mode": get_governor_mode()})
    sys.stdout.write(session_start_context())
    return 0


def hook_post_tool(data: dict[str, Any], failed: bool = False) -> int:
    tool_input = data.get("tool_input") or {}
    response = data.get("tool_response") or {}
    command = str(tool_input.get("command") or tool_input.get("cmd") or "")
    stdout = str(response.get("stdout") or response.get("output") or "")
    stderr = str(response.get("stderr") or "")
    exit_code = response.get("exit_code", response.get("status", "unknown"))
    raw_chars = len(stdout) + len(stderr)
    raw_tokens = estimate_tokens(stdout + stderr)
    if consume_full_output_override():
        append_ledger(
            "full_output_override_used",
            {
                "session_id": data.get("session_id"),
                "cwd": data.get("cwd"),
                "command": command,
                "raw_chars": raw_chars,
                "raw_tokens_estimate": raw_tokens,
            },
        )
        return 0

    event_payload = {
        "session_id": data.get("session_id"),
        "cwd": data.get("cwd"),
        "command": command,
        "exit_code": exit_code,
        "raw_chars": raw_chars,
        "raw_tokens_estimate": raw_tokens,
    }
    if failed:
        append_ledger("tool_failure", event_payload)

    exit_is_failure = str(exit_code).lower() not in {"0", "success", "true", "none"}
    command_is_noisy = bool(NOISY_COMMAND_RE.search(command))
    should_filter = raw_chars >= TOOL_FILTER_THRESHOLD and (
        (command_is_noisy and exit_is_failure)
        or (command_is_noisy and raw_chars >= TOOL_FILTER_THRESHOLD * 2)
        or raw_chars >= TOOL_FILTER_THRESHOLD * 4
    )
    if failed:
        if raw_chars:
            summary = summarize_output(command, stdout, stderr, exit_code)
            summary_tokens = estimate_tokens(summary)
            blocked = max(0, raw_tokens - summary_tokens)
            append_ledger(
                "tool_failure_summary",
                {
                    **event_payload,
                    "summary_tokens_estimate": summary_tokens,
                    "tokens_blocked_estimate": blocked,
                },
            )
            write_json(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUseFailure",
                        "additionalContext": summary,
                    }
                }
            )
        return 0

    if not should_filter:
        return 0

    summary = summarize_output(command, stdout, stderr, exit_code)
    summary_tokens = estimate_tokens(summary)
    blocked = max(0, raw_tokens - summary_tokens)
    append_ledger(
        "tool_output_filtered",
        {
            **event_payload,
            "summary_tokens_estimate": summary_tokens,
            "tokens_blocked_estimate": blocked,
        },
    )
    write_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": {
                    "stdout": summary,
                    "stderr": "",
                    "interrupted": bool(response.get("interrupted", False)),
                    "isImage": bool(response.get("isImage", False)),
                },
                "additionalContext": f"Governor blocked ~{blocked} noisy tool-output tokens while preserving failure details.",
            }
        }
    )
    return 0


def hook_compact(data: dict[str, Any]) -> int:
    append_ledger("pre_compact", {"session_id": data.get("session_id"), "cwd": data.get("cwd")})
    return 0


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def guard(contract_path: Path | None = None) -> int:
    if contract_path is None:
        candidates = sorted(contracts_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("No implementation contract found. Run /governor:plan first or pass a contract JSON path.")
            return 1
        contract_path = candidates[0]

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Could not read contract: {contract_path} ({exc})")
        return 2

    changed, git_error = git_changed_files()
    planned = set(contract.get("planned_files") or [])
    tests = contract.get("acceptance_tests") or []
    requirements = contract.get("requirements") or []
    unexpected = [file for file in changed if planned and file not in planned]
    missing_planned = [file for file in planned if file not in changed]

    print(f"Governor drift guard: {contract_path}")
    if git_error:
        print(f"- Git status unavailable: {git_error}")
        print("- Drift check is limited to contract requirements and acceptance tests.")
    else:
        print(f"- Changed files: {len(changed)}")
    if planned:
        print(f"- Planned files: {len(planned)}")
        if unexpected:
            print("- Possible scope drift:")
            for file in unexpected[:30]:
                print(f"  - {file}")
        else:
            print("- No unplanned changed files detected.")
        if missing_planned:
            print("- Planned files not changed yet:")
            for file in missing_planned[:30]:
                print(f"  - {file}")
    if requirements:
        print("- Contract requirements to verify:")
        for item in requirements[:20]:
            print(f"  - {item}")
    if tests:
        print("- Acceptance tests to run/report:")
        for item in tests[:20]:
            print(f"  - {item}")
    print("- Smallest next step: run the listed acceptance tests, then fix only failures tied to contract requirements.")
    return 0


def git_changed_files() -> tuple[list[str], str | None]:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return [], str(exc)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "git status failed").strip()
        return [], message[:240]
    files = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files, None


def save_contract(path: Path, payload: str) -> int:
    try:
        contract = json.loads(payload)
    except json.JSONDecodeError as exc:
        print(f"Contract must be JSON. Parse error: {exc}")
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved contract: {path}")
    return 0


def contract_path_from_title(title: str) -> Path:
    return contracts_dir() / f"{slugify(title)}.json"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Claude Code Governor helper")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("paths", nargs="*", type=Path)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("original", type=Path)
    validate_parser.add_argument("compressed", type=Path)

    compress_parser = sub.add_parser("compress")
    compress_parser.add_argument("target", type=Path, nargs="?", default=Path("CLAUDE.md"))
    compress_parser.add_argument("--level", choices=sorted(COMPRESSION_LEVELS), default="medium")
    compress_mode = compress_parser.add_mutually_exclusive_group()
    compress_mode.add_argument("--auto", action="store_true", help="prepare and emit model rewrite payload as JSON")
    compress_mode.add_argument("--prepare", action="store_true", help="prepare backup, marked draft, and prompt")
    compress_mode.add_argument("--finalize", action="store_true", help="strip markers, validate, and recover if needed")
    compress_mode.add_argument("--info", action="store_true", help="print latest compression manifest")
    compress_parser.add_argument("--draft", type=Path, help="marked draft to finalize")

    mark_parser = sub.add_parser("mark-protected")
    mark_parser.add_argument("source", type=Path)
    mark_parser.add_argument("dest", nargs="?", type=Path)

    strip_parser = sub.add_parser("strip-protect")
    strip_parser.add_argument("source", type=Path)
    strip_parser.add_argument("dest", nargs="?", type=Path)

    recover_parser = sub.add_parser("recover-protected")
    recover_parser.add_argument("original", type=Path)
    recover_parser.add_argument("candidate", type=Path)
    recover_parser.add_argument("output", nargs="?", type=Path)

    sub.add_parser("status")
    sub.add_parser("statusline")
    mode_parser = sub.add_parser("mode")
    mode_parser.add_argument("mode", choices=sorted(GOVERNOR_MODES | {"status"}))
    full_parser = sub.add_parser("full")
    full_parser.add_argument("--count", type=int, default=1)

    hook_parser = sub.add_parser("hook")
    hook_parser.add_argument("event", choices=["session-start", "prompt", "post-tool-use", "post-tool-use-failure", "compact"])

    guard_parser = sub.add_parser("guard")
    guard_parser.add_argument("contract", nargs="?", type=Path)

    save_parser = sub.add_parser("save-contract")
    save_parser.add_argument("path", nargs="?", type=Path)
    save_parser.add_argument("--title", help="derive the contract path from a title")

    slug_parser = sub.add_parser("slug")
    slug_parser.add_argument("text")

    args = parser.parse_args(argv)
    if args.command == "audit":
        return audit(args.paths)
    if args.command == "validate":
        return validate_file(args.original, args.compressed)
    if args.command == "compress":
        if args.info:
            return compress_info(args.target)
        prepare = args.prepare or not args.finalize
        return compress_command(args.target, args.level, prepare=prepare, finalize=args.finalize, auto=args.auto, draft=args.draft)
    if args.command == "mark-protected":
        return mark_protected(args.source, args.dest)
    if args.command == "strip-protect":
        return strip_protect(args.source, args.dest)
    if args.command == "recover-protected":
        return recover_protected(args.original, args.candidate, args.output)
    if args.command == "status":
        return status()
    if args.command == "statusline":
        return statusline()
    if args.command == "mode":
        if args.mode == "status":
            print(f"Governor mode: {get_governor_mode()}")
            return 0
        return set_governor_mode(args.mode)
    if args.command == "full":
        return set_full_output(args.count)
    if args.command == "hook":
        data = read_stdin_json()
        if args.event == "session-start":
            return hook_session_start(data)
        if args.event == "prompt":
            return hook_prompt(data)
        if args.event == "post-tool-use":
            return hook_post_tool(data, failed=False)
        if args.event == "post-tool-use-failure":
            return hook_post_tool(data, failed=True)
        if args.event == "compact":
            return hook_compact(data)
    if args.command == "guard":
        return guard(args.contract)
    if args.command == "save-contract":
        if args.path:
            path = args.path
        elif args.title:
            path = contract_path_from_title(args.title)
        else:
            print("save-contract requires a path or --title.")
            return 2
        return save_contract(path, sys.stdin.read())
    if args.command == "slug":
        print(slugify(args.text))
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
