"""Deterministically compile the canonical ADLC skill into provider bundles."""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping

from adlc_runtime.provider_targets import get_target


@dataclass(frozen=True)
class CompiledBundle:
    provider: str
    files: Mapping[str, bytes]
    digests: Mapping[str, str]
    bundle_digest: str


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _installed_content(relative: str, content: bytes) -> bytes:
    """Translate repository-relative canonical paths into bundle-relative paths."""
    if relative in {"SKILL.src.md", "scripts/context.py"}:
        content = content.replace(b"skill/scripts/", b"scripts/")
        content = content.replace(b"skill/reference/", b"reference/")
    if relative == "SKILL.src.md":
        content = content.replace(
            b"# ADLC\n\n",
            b"# ADLC\n\nResolve every `scripts/`, `reference/`, and `loops/` path below "
            b"relative to the directory containing this `SKILL.md`, never from the target "
            b"repository root.\n\n",
            1,
        )
    if relative in {
        "reference/command-build.md",
        "reference/command-fix.md",
        "reference/command-review.md",
    }:
        content = content.replace(b"docs/loop-library/", b"loops/")
    if relative in {
        "loops/public-build.json",
        "loops/public-fix.json",
        "loops/public-review.json",
    }:
        content = content.replace(b"docs/loop-library/", b"<skill-root>/loops/")
    return content


def bundle_from_files(provider: str, files: Mapping[str, bytes]) -> CompiledBundle:
    get_target(provider)
    for path in files:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts or not path or "\\" in path:
            raise ValueError(f"unsafe bundle path: {path!r}")
    ordered = {path: files[path] for path in sorted(files)}
    if "SKILL.md" not in ordered:
        raise ValueError("compiled bundle requires SKILL.md")
    digests = {path: _digest(content) for path, content in ordered.items()}
    aggregate = hashlib.sha256()
    for path, digest in digests.items():
        aggregate.update(path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
    return CompiledBundle(provider, ordered, digests, aggregate.hexdigest())


def compile_bundle(source_root: Path, provider: str) -> CompiledBundle:
    target = get_target(provider)
    source_root = source_root.resolve()
    canonical = source_root / "SKILL.src.md"
    if not canonical.is_file():
        raise ValueError(f"canonical skill source missing: {canonical}")
    files: Dict[str, bytes] = {}
    for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
        relative = source.relative_to(source_root).as_posix()
        if any(part.startswith(".") or part == "__pycache__" for part in Path(relative).parts):
            continue
        output = target.skill_filename if relative == "SKILL.src.md" else relative
        files[output] = _installed_content(relative, source.read_bytes())
    return bundle_from_files(provider, files)


def write_bundle(bundle: CompiledBundle, output_root: Path) -> Path:
    destination = output_root / bundle.provider / "adlc"
    for relative, content in bundle.files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    verify_bundle_path(bundle, destination)
    return destination


def verify_bundle_path(bundle: CompiledBundle, root: Path) -> None:
    actual = {
        path.relative_to(root).as_posix(): _digest(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    if actual != dict(bundle.digests):
        raise ValueError("staged provider bundle digest verification failed")


def default_source_root() -> Path:
    override = os.environ.get("ADLC_SKILL_SOURCE")
    candidates = [
        Path(override).expanduser() if override else None,
        Path(__file__).resolve().parents[2] / "skill",
        Path(sys.prefix) / "share" / "adlc" / "skill",
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "SKILL.src.md").is_file():
            return candidate.resolve()
    raise FileNotFoundError("canonical ADLC skill source is unavailable")
