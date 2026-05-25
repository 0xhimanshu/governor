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
MAX_STRUCTURED_LINES = 80
MAX_STRUCTURED_ITEMS = 8
MAX_STRUCTURED_STRING = 240
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
SIGNAL_KEY_RE = re.compile(
    r"(error|warning|fail|exception|trace|stack|message|reason|status|code|"
    r"path|file|line|column|test|summary|detail|selected|request|finding|"
    r"endpoint|url|severity|title|evidence|auth|authorization|location)",
    re.IGNORECASE,
)
BULK_KEY_RE = re.compile(r"(stdout|stderr|output|content|body|text|items|results|entries|logs?)", re.IGNORECASE)
NEVER_REWRITE_TOOL_RE = re.compile(
    r"^(Read|Write|Edit|MultiEdit|NotebookEdit|TodoWrite|TaskOutput|AskUserQuestion|ExitPlanMode|mcp__playwright__browser_evaluate)$"
)
TOOL_FILTER_ALLOW_RE = re.compile(r"^(Bash|Grep|Glob|LS|Task|WebFetch|WebSearch|mcp__.*)$")


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


@dataclasses.dataclass(frozen=True)
class ToolSnapshot:
    tool_name: str
    tool_label: str
    command: str
    exit_code: Any
    stdout: str
    stderr: str
    raw_text: str
    raw_chars: int
    raw_tokens_estimate: int
    payload_kind: str
    confidence: str
    structured_lines: tuple[str, ...]
    duration_ms: int | None


@dataclasses.dataclass(frozen=True)
class CompressionResult:
    rc: int
    payload: dict[str, Any]


def data_dir() -> Path:
    raw = os.environ.get("CLAUDE_PLUGIN_DATA")
    preferred = Path(raw) if raw else Path.home() / ".claude" / "plugins" / PLUGIN_NAME
    fallback = Path(os.environ.get("TMPDIR", "/tmp")) / f"{PLUGIN_NAME}-plugin-data"
    for path in (preferred, fallback):
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue
    return Path.cwd()


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


def compact_token_label(tokens: int) -> str:
    sign = "-" if tokens < 0 else ""
    value = abs(tokens)
    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{sign}{value / 1000:.1f}k"
    if value >= 1_000:
        return f"{sign}{value / 1000:.2f}k"
    return f"{sign}{value}"


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


def all_ledger_paths() -> list[Path]:
    """Return all known ledger files, including those written by plugin hooks via CLAUDE_PLUGIN_DATA."""
    seen: set[Path] = set()
    paths: list[Path] = []

    def _add(p: Path) -> None:
        resolved = p.resolve()
        if resolved not in seen and p.exists():
            seen.add(resolved)
            paths.append(p)

    _add(ledger_path())

    manual_fallback = Path.home() / ".claude" / "plugins" / PLUGIN_NAME / "ledger.jsonl"
    _add(manual_fallback)

    plugin_data_root = Path.home() / ".claude" / "plugins" / "data"
    try:
        if plugin_data_root.is_dir():
            for candidate in sorted(plugin_data_root.iterdir()):
                if not candidate.is_dir():
                    continue
                if not candidate.name.startswith(PLUGIN_NAME):
                    continue
                _add(candidate / "ledger.jsonl")
    except OSError:
        pass
    return paths


def persist_session_env(session_id: str | None, cwd: str | None) -> None:
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return

    exports: list[str] = []
    if session_id:
        exports.append(f"export CLAUDE_GOVERNOR_SESSION_ID={shlex.quote(str(session_id))}")
    if cwd:
        exports.append(f"export CLAUDE_GOVERNOR_SESSION_CWD={shlex.quote(str(cwd))}")
    if not exports:
        return

    try:
        with Path(env_file).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(exports) + "\n")
    except OSError:
        return


def load_ledger(limit: int | None = None) -> list[dict[str, Any]]:
    paths = all_ledger_paths()
    if not paths:
        return []
    records: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    records.sort(key=lambda r: r.get("ts", 0))
    if limit:
        records = records[-limit:]
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


def record_context_overhead(source: str, text: str, **payload: Any) -> int:
    tokens = estimate_tokens(text) if text else 0
    if tokens <= 0:
        return 0
    append_ledger(
        "context_overhead_injected",
        {
            **payload,
            "source": source,
            "tokens_estimate": tokens,
        },
    )
    return tokens


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


def caveman_enabled_in_settings() -> bool | None:
    settings = Path.home() / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    enabled = data.get("enabledPlugins") or {}
    if any("caveman" in str(name).lower() and bool(value) for name, value in enabled.items()):
        return True
    legacy_enabled = data.get("caveman@caveman")
    return bool(legacy_enabled)


def caveman_active() -> bool:
    if os.environ.get("GOVERNOR_IGNORE_CAVEMAN") == "1":
        return False

    configured_enabled = caveman_enabled_in_settings()
    if configured_enabled is not None:
        return configured_enabled

    marker = Path.home() / ".claude" / ".caveman-active"
    try:
        if marker.exists():
            raw = marker.read_text(encoding="utf-8", errors="replace").strip().lower()
            if raw and raw not in {"0", "false", "off", "disabled"}:
                return True
    except OSError:
        pass
    return False


def governor_response_context(mode: str | None = None) -> str:
    mode = mode or get_governor_mode()
    if mode == "off":
        return ""
    quality_floor = (
        "Quality floor: compactness applies to final wording, not to correctness. "
        "For coding or review tasks, inspect the relevant code, preserve explicit constraints, "
        "make the smallest correct change, run the most relevant available verification, and state if verification was not run. "
        "Do not skip needed tests, examples, edge cases, or rationale merely to save tokens. "
        "Never claim a check passed unless it actually ran."
    )
    if mode == "normal":
        return (
            "GOVERNOR MODE ACTIVE — normal. Be professional and avoid filler, but do not force terse answers. "
            "Still preserve tool-output hygiene, planning discipline, and exact safety warnings. "
            + quality_floor
        )
    if caveman_active():
        return ""
    return (
        "GOVERNOR COMPACT MODE. Preserve the user's requested format exactly; no extra sections. "
        "Answer first; skip pleasantries, restating the task, and process narration. "
        "Use the shortest complete final response that preserves requirements, warnings, code, commands, and requested edge cases. "
        "Do not add caveats, examples, tests, or rationale unless requested or needed for correctness. "
        "Use bullets/tables only when shorter. Debugging: bug -> fix -> verify. "
        "No novelty dialect. "
        + quality_floor
    )


def session_start_context() -> str:
    mode = get_governor_mode()
    if mode == "off":
        return "Governor mode off. Hooks still track telemetry and tool-output filtering when configured."
    if mode == "compact" and caveman_active():
        return (
            "Governor compact response reinforcement paused because Caveman appears active. "
            "Governor still runs telemetry, memory compression, tool-output filtering, prompt guidance, and drift guardrails."
        )
    return (
        f"GOVERNOR MODE ACTIVE — {mode}\n\n"
        + governor_response_context(mode)
        + "\n\n"
        "Quota rules: keep context overhead tiny; label estimates; report exact Governor ledger numbers when available. "
        "Quality rule: token savings are a regression if they reduce task success, requirement coverage, or verification quality. "
        "Use soft suggestions for vague, broad, or retry-prone prompts. "
        "Do not expose internal compression prepare/finalize steps to the user during /governor:compress unless manual fallback is required."
    )


def set_full_output(count: int = 1) -> int:
    count = max(1, count)
    overrides = load_overrides()
    overrides["full_output_remaining"] = count
    save_overrides(overrides)
    print(f"Governor full-output override enabled for next {count} tool call(s).")
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


def strip_protect(source: Path, dest: Path | None = None, quiet: bool = False) -> int:
    text = source.read_text(encoding="utf-8", errors="replace")
    stripped = re.sub(r'<protect\b[^>]*>(.*?)</protect>', lambda match: match.group(1), text, flags=re.DOTALL)
    if dest is None:
        dest = source.with_suffix(source.suffix + ".stripped")
    dest.write_text(stripped, encoding="utf-8")
    if not quiet:
        print(f"Removed protect markers: {text.count('<protect ')}")
        print(f"Wrote: {dest}")
    return 0


def recover_protected(original: Path, candidate: Path, output: Path | None = None, quiet: bool = False) -> int:
    original_text = original.read_text(encoding="utf-8", errors="replace")
    candidate_text = candidate.read_text(encoding="utf-8", errors="replace")
    original_spans = protected_spans(original_text)
    candidate_spans = positioned_spans(candidate_text)

    if output is None:
        output = candidate
    if not original_spans:
        if output != candidate:
            shutil.copyfile(candidate, output)
        if not quiet:
            print("No protected spans found in original.")
        return 0
    if len(candidate_spans) < len(original_spans):
        if not quiet:
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

    if not quiet:
        print(f"Recovered protected spans: {replacements}")
        print(f"Wrote: {output}")
    return validate_file(original, output, quiet=quiet)


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


def stronger_compression_level(level: str) -> str | None:
    if level == "light":
        return "medium"
    if level == "medium":
        return "aggressive"
    return None


def compress_auto_command(target: Path, level: str) -> str:
    return " ".join(
        shlex.quote(part)
        for part in (
            "python3",
            str(Path(__file__).resolve()),
            "compress",
            str(target),
            "--level",
            level,
            "--auto",
        )
    )


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
    next_level = stronger_compression_level(level)
    payload = {
        "mode": "governor_compress_auto",
        "instruction": "Rewrite marked_content using prompt. Save only rewritten file content to draft_path, then run finalize_command_json. If finalization returns status=quality_guard_failed and next_level is present, rerun retry_auto_command once. Do not show internal paths to the user unless manual fallback or failure occurs.",
        "target": manifest["target"],
        "level": manifest["level"],
        "backup_path": manifest["backup"],
        "draft_path": manifest["draft"],
        "prompt_path": manifest["prompt"],
        "prompt": prompt,
        "marked_content": marked_content,
        "finalize_command": finalize_command(Path(manifest["target"]), Path(manifest["draft"])),
        "finalize_command_json": finalize_command(Path(manifest["target"]), Path(manifest["draft"])) + " --json",
        "next_level": next_level,
        "retry_auto_command": compress_auto_command(Path(manifest["target"]), next_level) if next_level else None,
        "quality_guard_min_savings_percent": compression_min_savings(level, int(manifest["original_tokens_estimate"])),
        "original_tokens_estimate": manifest["original_tokens_estimate"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def print_compression_result(payload: dict[str, Any], json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status = payload.get("status")
    if status == "success":
        print("Governor compression finalized.")
    elif status == "quality_guard_failed":
        print("Governor compression rejected by quality guard.")
    else:
        print("Governor compression failed; original backup restored.")
    print(f"- Target: {payload.get('target')}")
    print(f"- Compressed estimate: {token_estimate_label(int(payload.get('compressed_tokens_estimate') or 0))}")
    print(f"- Memory saved: {float(payload.get('memory_saved_percent') or 0):.1f}%")
    print(f"- Recovery used: {'yes' if payload.get('recovery_used') else 'no'}")
    print(f"- Backup restored: {'yes' if payload.get('backup_restored') else 'no'}")
    print(f"- Quality guard: {'failed' if payload.get('quality_guard_failed') else 'passed'}")
    if payload.get("recommended_retry_command"):
        print(f"- Recommended retry: {payload['recommended_retry_command']}")


def compress_finalize(target: Path, draft: Path | None = None, json_output: bool = False) -> int:
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

    strip_protect(draft, target, quiet=json_output)
    rc = validate_file(backup, target, quiet=json_output)
    recovered = False
    restored = False
    quality_guard_failed = False
    if rc != 0:
        if not json_output:
            print("Validation failed; attempting automatic protected-span recovery.")
        rc = recover_protected(backup, target, target, quiet=json_output)
        recovered = rc == 0
    if rc != 0:
        shutil.copyfile(backup, target)
        restored = True
        if not json_output:
            print("Recovery failed. Restored original backup to target.")

    after_tokens = estimate_tokens(target.read_text(encoding="utf-8", errors="replace"))
    before_tokens = int(manifest.get("original_tokens_estimate") or 0)
    saved = 100 * (before_tokens - after_tokens) / before_tokens if before_tokens else 0
    level = str(manifest.get("level") or "medium")
    min_savings = compression_min_savings(level, before_tokens)
    next_level = stronger_compression_level(level)
    if rc == 0 and min_savings and saved < min_savings and os.environ.get("GOVERNOR_ALLOW_LOW_SAVINGS") != "1":
        quality_guard_failed = True
        shutil.copyfile(backup, target)
        restored = True
        rc = 3
        if not json_output:
            print(
                f"Quality guard failed: {saved:.1f}% savings is below the "
                f"{min_savings:.0f}% minimum for {level} compression."
            )
            print("Restored original backup. Rerun with a stronger level or set GOVERNOR_ALLOW_LOW_SAVINGS=1 to keep low-savings output.")

    status = "success" if rc == 0 else ("quality_guard_failed" if quality_guard_failed else "failed")
    retry_command = compress_auto_command(Path(manifest["target"]), next_level) if quality_guard_failed and next_level else None
    payload = {
        "status": status,
        "target": str(target),
        "level": level,
        "original_tokens_estimate": before_tokens,
        "compressed_tokens_estimate": after_tokens,
        "memory_saved_percent": round(saved, 1),
        "recovery_used": recovered,
        "backup_restored": restored,
        "quality_guard_failed": quality_guard_failed,
        "min_savings_percent": min_savings,
        "backup_path": str(backup),
        "next_level": next_level,
        "recommended_retry_command": retry_command,
    }

    append_ledger(
        "memory_compression_finalized",
        {
            "target": str(target),
            "level": level,
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
    print_compression_result(payload, json_output=json_output)
    return rc


def compress_info(target: Path) -> int:
    manifest_path = compression_workspace(target) / "latest.json"
    if not manifest_path.exists():
        print(f"No compression manifest found for {target}. Run compress --prepare first.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps(manifest, indent=2))
    return 0


def compress_command(
    target: Path,
    level: str,
    prepare: bool,
    finalize: bool,
    auto: bool,
    draft: Path | None,
    json_output: bool,
) -> int:
    if auto:
        return compress_auto(target, level)
    if finalize:
        return compress_finalize(target, draft, json_output=json_output)
    return compress_prepare(target, level)


def validate_file(original: Path, compressed: Path, quiet: bool = False) -> int:
    before = original.read_text(encoding="utf-8", errors="replace")
    after = compressed.read_text(encoding="utf-8", errors="replace")
    missing = [span for span in protected_spans(before) if span.value not in after]
    before_tokens = estimate_tokens(before)
    after_tokens = estimate_tokens(after)
    saved = 100 * (before_tokens - after_tokens) / before_tokens if before_tokens else 0

    if not quiet:
        print(f"Original estimate: {token_estimate_label(before_tokens)}")
        print(f"Compressed estimate: {token_estimate_label(after_tokens)}")
        print(f"Memory saved: {saved:.1f}%")
    if missing:
        if not quiet:
            print("Validation failed. Missing protected spans:")
            for span in missing[:80]:
                value = span.value.replace("\n", "\\n")
                if len(value) > 160:
                    value = value[:157] + "..."
                print(f"- {span.kind}: {value}")
            if len(missing) > 80:
                print(f"- ... {len(missing) - 80} more")
        return 2
    if not quiet:
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


def aggregate_governor_accounting(records: list[dict[str, Any]]) -> dict[str, Any]:
    tool_blocked = 0
    memory_saved = 0
    prompt_suggestions = 0
    failures = 0
    compactions = 0
    by_command: dict[str, int] = {}
    latest_statusline: dict[str, Any] | None = None

    for record in records:
        event = record.get("event")
        payload = record.get("payload", {})
        if event in {"tool_output_filtered", "tool_failure_summary"}:
            blocked = int(payload.get("tokens_blocked_estimate") or 0)
            tool_blocked += blocked
            source = str(payload.get("command") or payload.get("tool_name") or "unknown").split()[0]
            by_command[source] = by_command.get(source, 0) + blocked
        elif event == "memory_compression_finalized" and payload.get("success"):
            original = int(payload.get("original_tokens_estimate") or 0)
            compressed = int(payload.get("compressed_tokens_estimate") or 0)
            memory_saved += max(0, original - compressed)
        elif event == "prompt_risk_suggested":
            prompt_suggestions += 1
        elif event == "tool_failure":
            failures += 1
        elif event == "pre_compact":
            compactions += 1
        elif event == "statusline_snapshot" and any(value is not None for value in payload.values()):
            latest_statusline = payload

    tokens_saved = tool_blocked + memory_saved
    return {
        "tool_blocked": tool_blocked,
        "memory_saved": memory_saved,
        "tokens_saved": tokens_saved,
        "prompt_suggestions": prompt_suggestions,
        "failures": failures,
        "compactions": compactions,
        "by_command": by_command,
        "latest_statusline": latest_statusline,
    }


def current_session_records(
    records: list[dict[str, Any]],
    current_cwd: str | None = None,
    current_session_id: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not records:
        return [], "empty"

    cwd = current_cwd or os.getcwd()

    session_id = current_session_id
    if not session_id:
        for record in reversed(records):
            if record.get("cwd") != cwd:
                continue
            session_id = record.get("session_id")
            if session_id:
                break
    if session_id:
        return [record for record in records if record.get("session_id") == session_id], "session_id"

    start_ts = None
    for record in reversed(records):
        if record.get("cwd") == cwd and record.get("event") == "session_start":
            start_ts = record.get("ts")
            break
    if start_ts is not None:
        scoped = [
            record
            for record in records
            if record.get("cwd") == cwd and float(record.get("ts") or 0) >= float(start_ts)
        ]
        if scoped:
            return scoped, "cwd_since_session_start"

    cwd_records = [record for record in records if record.get("cwd") == cwd]
    if cwd_records:
        return cwd_records[-500:], "cwd_recent"

    return records[-500:], "global_recent"


def status() -> int:
    lifetime_records = load_ledger()
    current_session_id = os.environ.get("CLAUDE_GOVERNOR_SESSION_ID")
    records, session_scope = current_session_records(
        lifetime_records,
        current_cwd=os.getcwd(),
        current_session_id=current_session_id,
    )
    if not records:
        print("Claude Code Governor: no ledger events yet.")
        print("Run a session with the plugin enabled, then use /governor:status again.")
        return 0

    session = aggregate_governor_accounting(records)
    lifetime = aggregate_governor_accounting(lifetime_records)

    print("Claude Code Governor status")
    print(f"- Mode: {get_governor_mode()}")
    print(f"- Caveman detected: {'yes; compact response reinforcement paused' if caveman_active() else 'no'}")
    print(f"- Session events: {len(records)}")
    print(f"- Session tokens saved: ~{session['tokens_saved']}")
    print(f"- Session tool failures observed: {session['failures']}")
    print(f"- Session compactions: {session['compactions']}")
    print(f"- Session prompt suggestions: {session['prompt_suggestions']}")
    print(f"- Lifetime tokens saved: ~{lifetime['tokens_saved']}")
    print(f"- Lifetime tool failures observed: {lifetime['failures']}")
    print(f"- Lifetime compactions: {lifetime['compactions']}")
    print(f"- Lifetime prompt suggestions: {lifetime['prompt_suggestions']}")
    if session["latest_statusline"]:
        print("- Latest live statusline:")
        latest_statusline = session["latest_statusline"]
        fields = latest_statusline if "five_hour" in latest_statusline or "context" in latest_statusline else compact_statusline_fields(latest_statusline)
        for label, value in fields.items():
            if value is not None:
                print(f"  - {label}: {value}")
    if session["by_command"]:
        print("- Session waste heat map:")
        for command, tokens in sorted(session["by_command"].items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"  - {command}: ~{tokens} tokens blocked")
    print("")
    if session_scope != "session_id":
        print(f"Note: current-session scope inferred via `{session_scope}` because a live Claude session id was not available in this command context.")
    print("Cached tokens can reduce billing/limits but still occupy context. Governor reports context and usage separately when statusline data is available.")
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
        "five_hour": nested_get(data, "rate_limits.five_hour.used_percentage", "rate_limits.five_hour.percent_used", "five_hour_usage"),
        "seven_day": nested_get(data, "rate_limits.seven_day.used_percentage", "rate_limits.seven_day.percent_used", "seven_day_usage"),
    }


def statusline() -> int:
    data = read_stdin_json()
    fields = compact_statusline_fields(data)
    session_id = nested_get(data, "session.id", "session_id", "sessionId") or os.environ.get("CLAUDE_GOVERNOR_SESSION_ID")
    cwd = str(data.get("cwd") or os.getcwd())
    append_ledger("statusline_snapshot", {**fields, "session_id": session_id, "cwd": cwd})
    records = load_ledger()
    session_records, _ = current_session_records(records, current_cwd=cwd, current_session_id=str(session_id) if session_id else None)
    accounting = aggregate_governor_accounting(session_records)

    pieces = ["Governor"]
    mode = get_governor_mode()
    if mode != "off":
        pieces.append(mode)
    tokens_saved = int(accounting["tokens_saved"])
    if tokens_saved > 0:
        pieces.append(f"saved ~{compact_token_label(tokens_saved)}")
    if fields.get("context") is not None:
        ctx = fields["context"]
        if isinstance(ctx, dict):
            total = sum(ctx.get(k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            pieces.append(f"ctx {compact_token_label(total)}")
        else:
            pieces.append(f"ctx {ctx}")
    elif fields.get("context_tokens") is not None:
        pieces.append(f"ctxTok {fields['context_tokens']}")
    if fields.get("five_hour") is not None:
        pieces.append(f"5h {fields['five_hour']}%")
    if fields.get("seven_day") is not None:
        pieces.append(f"7d {fields['seven_day']}%")
    if accounting["tool_blocked"]:
        pieces.append(f"blocked ~{compact_token_label(int(accounting['tool_blocked']))}")
    print(" | ".join(str(piece) for piece in pieces))
    return 0


def looks_like_json_text(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def safe_json_loads(text: str) -> Any | None:
    if not text or not looks_like_json_text(text):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def clip_inline(value: Any, max_chars: int = MAX_STRUCTURED_STRING) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def signal_key(key: str) -> bool:
    return bool(SIGNAL_KEY_RE.search(key))


def bulk_key(key: str) -> bool:
    return bool(BULK_KEY_RE.search(key))


def container_preview(value: Any) -> str:
    if isinstance(value, dict):
        return f"object ({len(value)} keys)"
    if isinstance(value, list):
        return f"list ({len(value)} items)"
    return type(value).__name__


def collect_structured_lines(value: Any, path: str = "", lines: list[str] | None = None, budget: int = MAX_STRUCTURED_LINES) -> list[str]:
    if lines is None:
        lines = []
    if len(lines) >= budget:
        return lines

    if isinstance(value, dict):
        keys = list(value.keys())
        ordered = sorted(keys, key=lambda key: (not signal_key(str(key)), str(key).lower()))
        for key in ordered[: MAX_STRUCTURED_ITEMS * 2]:
            child = value[key]
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(child, (str, int, float, bool)) or child is None:
                if bulk_key(str(key)) and isinstance(child, str) and len(child) > MAX_STRUCTURED_STRING:
                    lines.append(f"{child_path}: {len(child)} chars")
                else:
                    lines.append(f"{child_path}: {clip_inline(child)}")
            elif isinstance(child, (dict, list)):
                lines.append(f"{child_path}: {container_preview(child)}")
                if signal_key(str(key)) or len(lines) < MAX_STRUCTURED_ITEMS:
                    collect_structured_lines(child, child_path, lines, budget)
            else:
                lines.append(f"{child_path}: {clip_inline(child)}")
            if len(lines) >= budget:
                break
        return lines

    if isinstance(value, list):
        lines.append(f"{path or 'items'}: list ({len(value)} items)")
        for index, child in enumerate(value[:MAX_STRUCTURED_ITEMS]):
            child_path = f"{path}[{index}]" if path else f"items[{index}]"
            if isinstance(child, (dict, list)):
                lines.append(f"{child_path}: {container_preview(child)}")
                collect_structured_lines(child, child_path, lines, budget)
            else:
                lines.append(f"{child_path}: {clip_inline(child)}")
            if len(lines) >= budget:
                break
        return lines

    lines.append(f"{path or 'value'}: {clip_inline(value)}")
    return lines


def stringify_response(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, (dict, list)):
        try:
            return json.dumps(response, ensure_ascii=False, indent=2)
        except TypeError:
            return str(response)
    return str(response)


def normalize_tool_response(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if response is None:
        return {}
    if isinstance(response, str):
        return {"output": response}
    if isinstance(response, (list, tuple)):
        return {"output": list(response)}
    return {"output": response}


def tool_name_from_event(data: dict[str, Any], tool_input: dict[str, Any]) -> str:
    return str(
        data.get("tool_name")
        or data.get("tool")
        or tool_input.get("tool")
        or tool_input.get("name")
        or ("Bash" if tool_input.get("command") or tool_input.get("cmd") else "Tool")
    )


def build_tool_snapshot(data: dict[str, Any]) -> ToolSnapshot:
    tool_input = data.get("tool_input") or {}
    response = normalize_tool_response(data.get("tool_response"))
    tool_name = tool_name_from_event(data, tool_input)
    command = str(tool_input.get("command") or tool_input.get("cmd") or "")
    stdout = response.get("stdout")
    stderr = response.get("stderr")
    output = response.get("output")
    exit_code = response.get("exit_code", response.get("status", "unknown"))

    structured_value = None
    confidence = "low"
    payload_kind = "text"

    if isinstance(output, (dict, list)):
        structured_value = output
        payload_kind = "structured"
        confidence = "high"
    elif isinstance(output, str):
        parsed = safe_json_loads(output)
        if isinstance(parsed, (dict, list)):
            structured_value = parsed
            payload_kind = "json-text"
            confidence = "medium"
    elif isinstance(response, dict) and any(isinstance(response.get(key), (dict, list)) for key in ("result", "data", "payload")):
        for key in ("result", "data", "payload"):
            candidate = response.get(key)
            if isinstance(candidate, (dict, list)):
                structured_value = candidate
                payload_kind = f"response-{key}"
                confidence = "high"
                break
    elif isinstance(response, dict):
        response_view = {
            key: value
            for key, value in response.items()
            if key not in {"stdout", "stderr", "output", "interrupted", "isImage"}
        }
        if response_view and any(isinstance(value, (dict, list)) for value in response_view.values()):
            structured_value = response_view
            payload_kind = "response-object"
            confidence = "medium"

    raw_parts = []
    if isinstance(stdout, str) and stdout:
        raw_parts.append(stdout)
    if isinstance(stderr, str) and stderr:
        raw_parts.append(stderr)
    if output and not isinstance(output, str):
        raw_parts.append(stringify_response(output))
    elif isinstance(output, str) and output and output not in raw_parts:
        raw_parts.append(output)
    raw_text = "\n".join(part for part in raw_parts if part)

    structured_lines: tuple[str, ...] = ()
    if structured_value is not None:
        structured_lines = tuple(collect_structured_lines(structured_value))

    tool_label = f"{tool_name}: {command}" if command else tool_name
    return ToolSnapshot(
        tool_name=tool_name,
        tool_label=tool_label,
        command=command,
        exit_code=exit_code,
        stdout=stdout if isinstance(stdout, str) else "",
        stderr=stderr if isinstance(stderr, str) else "",
        raw_text=raw_text,
        raw_chars=len(raw_text),
        raw_tokens_estimate=estimate_tokens(raw_text),
        payload_kind=payload_kind,
        confidence=confidence,
        structured_lines=structured_lines,
        duration_ms=data.get("duration_ms"),
    )


def exit_is_failure(exit_code: Any) -> bool:
    return str(exit_code).lower() not in {"0", "success", "true", "none"}


def should_filter_snapshot(snapshot: ToolSnapshot, failed: bool = False) -> tuple[bool, str]:
    if NEVER_REWRITE_TOOL_RE.match(snapshot.tool_name):
        return False, "tool-blocklist"

    structured_heavy = bool(snapshot.structured_lines) and (
        snapshot.confidence in {"high", "medium"} and len(snapshot.structured_lines) >= 8
    )
    raw_heavy = snapshot.raw_chars >= TOOL_FILTER_THRESHOLD
    very_heavy = snapshot.raw_chars >= TOOL_FILTER_THRESHOLD * 4
    noisy_command = bool(snapshot.command and NOISY_COMMAND_RE.search(snapshot.command))
    allowlisted_tool = bool(TOOL_FILTER_ALLOW_RE.match(snapshot.tool_name))
    tool_failure = exit_is_failure(snapshot.exit_code)
    medium_heavy = snapshot.raw_chars >= TOOL_FILTER_THRESHOLD // 2

    if failed and (raw_heavy or structured_heavy):
        return True, "failure-summary"
    if very_heavy:
        return True, "very-large"
    if snapshot.tool_name.startswith("mcp__") and (raw_heavy or (structured_heavy and medium_heavy)):
        return True, "mcp-structured"
    if structured_heavy and raw_heavy:
        return True, "structured-heavy"
    if allowlisted_tool and raw_heavy:
        return True, "allowlisted-large"
    if noisy_command and (raw_heavy or (tool_failure and medium_heavy)):
        return True, "noisy-command"
    return False, "below-threshold"


def updated_tool_output(snapshot: ToolSnapshot, response: dict[str, Any], summary: str) -> dict[str, Any]:
    if snapshot.stdout or snapshot.stderr or snapshot.command:
        return {
            "stdout": summary,
            "stderr": "",
            "interrupted": bool(response.get("interrupted", False)),
            "isImage": bool(response.get("isImage", False)),
        }
    return {"output": summary}


def summarize_output(snapshot: ToolSnapshot) -> str:
    combined = []
    if snapshot.stdout:
        combined.append(("stdout", snapshot.stdout))
    if snapshot.stderr:
        combined.append(("stderr", snapshot.stderr))

    error_lines = []
    prioritized_error_lines: list[tuple[int, str]] = []
    failure_markers = re.compile(
        r"(error|failed|failure|exception|traceback|panic|assert|expected|received|"
        r"\bFAIL\b|\bFAILED\b|✕|×|[\w./-]+:\d+(?::\d+)?)",
        re.IGNORECASE,
    )

    def error_priority(line: str) -> int:
        lowered = line.lower()
        score = 0
        if "error ts" in lowered or ": error " in lowered:
            score += 20
        if any(token in lowered for token in ("not assignable", "type", "cannot", "missing", "undefined", "traceback", "runtimeerror", "assertion", "panic")):
            score += 35
        if any(token in lowered for token in ("failed", "failure", "exception", "blocked")):
            score += 20
        if any(token in lowered for token in ("unused", "never read", "declared but its value is never read")):
            score -= 25
        if "warning" in lowered or "deprecated" in lowered:
            score -= 20
        if lowered.startswith("stdout: found ") and " errors " in lowered:
            score -= 5
        return score

    total_failure_lines = 0
    for label, text in combined:
        for line in text.splitlines():
            if failure_markers.search(line):
                total_failure_lines += 1
                if len(error_lines) >= 80:
                    continue
                tagged_line = f"{label}: {line}"
                error_lines.append(tagged_line)
                prioritized_error_lines.append((error_priority(tagged_line), tagged_line))

    prioritized_error_lines.sort(key=lambda item: item[0], reverse=True)
    ordered_error_lines = [line for _, line in prioritized_error_lines]
    prioritization_note = None
    lowered_lines = [line.lower() for line in ordered_error_lines]
    if any("never read" in line or "unused" in line for line in lowered_lines) and any(
        token in line for line in lowered_lines for token in ("not assignable", "type", "cannot", "missing", "undefined")
    ):
        prioritization_note = "Prioritize blocking type or semantic errors before cleanup-only issues like unused imports."

    def clipped_lines(text: str, head: int, tail: int, prefer_tail: bool = False) -> list[str]:
        lines = text.splitlines()
        if len(lines) <= head + tail:
            return lines
        if prefer_tail:
            tail_window = min(tail, 12)
            return [f"... clipped {len(lines) - tail_window} lines ..."] + lines[-tail_window:]
        return lines[:head] + [f"... clipped {len(lines) - head - tail} lines ..."] + lines[-tail:]

    summary = [
        "Claude Code Governor compacted tool output.",
        f"Tool: `{snapshot.tool_label}`",
        f"Exit code/status: {snapshot.exit_code}",
        f"Payload type: {snapshot.payload_kind} ({snapshot.confidence} confidence)",
        f"Raw size: {token_estimate_label(snapshot.raw_tokens_estimate)}",
        f"Failure/error lines detected: {total_failure_lines}",
        "If the clue is missing, run `/governor:full` before repeating the step.",
        "Full raw output remains available in the terminal/transcript.",
        "",
    ]
    if snapshot.duration_ms is not None:
        summary.insert(4, f"Duration: {snapshot.duration_ms} ms")
    if snapshot.structured_lines:
        summary.append("Structured fields:")
        summary.extend(f"- {line}" for line in snapshot.structured_lines[:MAX_STRUCTURED_LINES])
        summary.append("")
    if ordered_error_lines:
        summary.append("Highest-priority failure/error lines:")
        summary.extend(f"- {line}" for line in ordered_error_lines[:12])
        if prioritization_note:
            summary.append(f"- Note: {prioritization_note}")
        summary.append("")

    if snapshot.stdout:
        stdout_lines = snapshot.stdout.splitlines()
        warning_heavy_head = sum(
            1
            for line in stdout_lines[:SUMMARY_HEAD_LINES]
            if "warning" in line.lower() or "deprecated" in line.lower()
        )
        prefer_tail_excerpt = bool(ordered_error_lines) and len(stdout_lines) > SUMMARY_TAIL_LINES and warning_heavy_head >= 10
        summary.append("Stdout excerpt:")
        summary.extend(clipped_lines(snapshot.stdout, SUMMARY_HEAD_LINES, SUMMARY_TAIL_LINES, prefer_tail=prefer_tail_excerpt))
        summary.append("")
    if snapshot.stderr:
        summary.append("Stderr excerpt:")
        summary.extend(clipped_lines(snapshot.stderr, SUMMARY_HEAD_LINES, SUMMARY_TAIL_LINES))

    return "\n".join(summary).strip()


def hook_prompt(data: dict[str, Any]) -> int:
    prompt = str(data.get("prompt") or data.get("user_prompt") or data.get("message") or "")
    prompt_lower = prompt.strip().lower()
    session_id = data.get("session_id")
    cwd = data.get("cwd")

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
        record_context_overhead(
            "prompt_reinforcement",
            response_context,
            session_id=session_id,
            cwd=cwd,
            mode=get_governor_mode(),
        )

    if prompt and HIGH_RISK_PROMPT_RE.search(prompt):
        append_ledger("prompt_risk_suggested", {"prompt_hash": stable_hash(prompt), "cwd": cwd, "session_id": session_id})
        suggestion = (
            "Governor prompt-risk suggestion: this prompt can trigger broad scanning or retry loops. "
            "Offer a quick choice instead of blocking: "
            "(a) make a compact plan first, "
            "(b) narrow to likely files/tests first, or "
            "(c) proceed as-is for speed. "
            "If the user already gave enough scope, proceed normally."
        )
        contexts.append(suggestion)
        record_context_overhead(
            "prompt_risk_suggestion",
            suggestion,
            session_id=session_id,
            cwd=cwd,
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
    session_id = data.get("session_id")
    cwd = data.get("cwd")
    mode = get_governor_mode()
    persist_session_env(str(session_id) if session_id else None, str(cwd) if cwd else None)
    append_ledger("session_start", {"session_id": session_id, "cwd": cwd, "mode": mode})
    context = session_start_context()
    if context:
        record_context_overhead(
            "session_start",
            context,
            session_id=session_id,
            cwd=cwd,
            mode=mode,
        )
    sys.stdout.write(context)
    return 0


def hook_post_tool(data: dict[str, Any], failed: bool = False) -> int:
    snapshot = build_tool_snapshot(data)
    response = normalize_tool_response(data.get("tool_response"))
    session_id = data.get("session_id")
    cwd = data.get("cwd")
    if consume_full_output_override():
        append_ledger(
            "full_output_override_used",
            {
                "session_id": session_id,
                "cwd": cwd,
                "tool_name": snapshot.tool_name,
                "command": snapshot.command,
                "raw_chars": snapshot.raw_chars,
                "raw_tokens_estimate": snapshot.raw_tokens_estimate,
            },
        )
        return 0

    event_payload = {
        "session_id": session_id,
        "cwd": cwd,
        "tool_name": snapshot.tool_name,
        "tool_label": snapshot.tool_label,
        "command": snapshot.command,
        "exit_code": snapshot.exit_code,
        "raw_chars": snapshot.raw_chars,
        "raw_tokens_estimate": snapshot.raw_tokens_estimate,
        "payload_kind": snapshot.payload_kind,
        "confidence": snapshot.confidence,
        "structured_lines": len(snapshot.structured_lines),
    }
    if failed:
        append_ledger("tool_failure", event_payload)

    should_filter, reason = should_filter_snapshot(snapshot, failed=failed)
    if failed:
        if snapshot.raw_chars or snapshot.structured_lines:
            summary = summarize_output(snapshot)
            summary_tokens = estimate_tokens(summary)
            blocked = max(0, snapshot.raw_tokens_estimate - summary_tokens)
            additional_context = (
                f"Governor summarized failed tool output for `{snapshot.tool_name}` "
                f"and blocked ~{blocked} tokens while preserving failure signals."
            )
            additional_context_tokens = estimate_tokens(additional_context)
            if blocked <= 0 and snapshot.raw_tokens_estimate < 200:
                return 0
            append_ledger(
                "tool_failure_summary",
                {
                    **event_payload,
                    "filter_reason": reason,
                    "summary_tokens_estimate": summary_tokens,
                    "tokens_blocked_estimate": blocked,
                    "additional_context_tokens_estimate": additional_context_tokens,
                },
            )
            record_context_overhead(
                "tool_filter_context",
                additional_context,
                session_id=session_id,
                cwd=cwd,
                tool_name=snapshot.tool_name,
                command=snapshot.command,
                failed=True,
            )
            write_json(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUseFailure",
                        "updatedToolOutput": updated_tool_output(snapshot, response, summary),
                        "additionalContext": additional_context,
                    }
                }
            )
        return 0

    if not should_filter:
        return 0

    summary = summarize_output(snapshot)
    summary_tokens = estimate_tokens(summary)
    blocked = max(0, snapshot.raw_tokens_estimate - summary_tokens)
    if blocked <= 0:
        return 0
    additional_context = (
        f"Governor blocked ~{blocked} low-value tool-output tokens from `{snapshot.tool_name}` "
        f"using {snapshot.payload_kind} ({snapshot.confidence} confidence, reason: {reason})."
    )
    additional_context_tokens = estimate_tokens(additional_context)
    append_ledger(
        "tool_output_filtered",
        {
            **event_payload,
            "filter_reason": reason,
            "summary_tokens_estimate": summary_tokens,
            "tokens_blocked_estimate": blocked,
            "additional_context_tokens_estimate": additional_context_tokens,
        },
    )
    record_context_overhead(
        "tool_filter_context",
        additional_context,
        session_id=session_id,
        cwd=cwd,
        tool_name=snapshot.tool_name,
        command=snapshot.command,
        failed=False,
    )
    write_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": updated_tool_output(snapshot, response, summary),
                "additionalContext": additional_context,
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
    compress_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON for supported compression modes")

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
        return compress_command(
            args.target,
            args.level,
            prepare=prepare,
            finalize=args.finalize,
            auto=args.auto,
            draft=args.draft,
            json_output=args.json,
        )
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
