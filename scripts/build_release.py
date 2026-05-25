#!/usr/bin/env python3
"""Build a lean Governor release package for GitHub Releases and Claude plugin submission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"

DEFAULT_INCLUDE = (
    ".claude-plugin",
    "assets",
    "bin",
    "commands",
    "hooks",
    "rules",
    "scripts",
    "skills",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "install.sh",
)

EXCLUDE_NAMES = {
    ".DS_Store",
    "build_release.py",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".log",
}

EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".claude",
    "marketing",
    "benchmarks",
}


def load_manifest() -> dict:
    return json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))


def iter_release_files(include_benchmarks: bool = False):
    include_roots = list(DEFAULT_INCLUDE)
    if include_benchmarks:
        include_roots.append("benchmarks")

    seen: set[Path] = set()
    for relative in include_roots:
        path = ROOT / relative
        if not path.exists():
            continue
        if path.is_file():
            if path not in seen:
                seen.add(path)
                yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_dir():
                continue
            rel = child.relative_to(ROOT)
            if any(part in EXCLUDE_PARTS for part in rel.parts):
                continue
            if child.name in EXCLUDE_NAMES:
                continue
            if child.suffix in EXCLUDE_SUFFIXES:
                continue
            if child not in seen:
                seen.add(child)
                yield child


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_zip(destination: Path, version: str, include_benchmarks: bool = False) -> list[Path]:
    archive_root = f"governor-v{version}"
    files = list(iter_release_files(include_benchmarks=include_benchmarks))
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for source in files:
            rel = source.relative_to(ROOT)
            arcname = f"{archive_root}/{rel.as_posix()}"
            info = zipfile.ZipInfo.from_file(source, arcname=arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            stat = source.stat()
            mode = stat.st_mode & 0xFFFF
            info.external_attr = mode << 16
            with source.open("rb") as handle:
                bundle.writestr(info, handle.read())
    return files


def build_release(output_dir: Path, include_benchmarks: bool = False) -> int:
    manifest = load_manifest()
    version = str(manifest.get("version") or "0.0.0")
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"governor-v{version}.zip"
    files = write_zip(zip_path, version, include_benchmarks=include_benchmarks)
    digest = sha256sum(zip_path)

    checksum_path = output_dir / f"governor-v{version}.sha256"
    checksum_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    manifest_path = output_dir / f"governor-v{version}-release.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": manifest.get("name"),
                "version": version,
                "zip": zip_path.name,
                "sha256": digest,
                "file_count": len(files),
                "includes_benchmarks": include_benchmarks,
                "files": [str(path.relative_to(ROOT)) for path in files],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Built release package: {zip_path}")
    print(f"Checksum: {checksum_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Files included: {len(files)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Governor release zip.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--include-benchmarks", action="store_true")
    args = parser.parse_args()
    return build_release(args.output_dir, include_benchmarks=args.include_benchmarks)


if __name__ == "__main__":
    raise SystemExit(main())
