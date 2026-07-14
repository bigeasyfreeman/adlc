#!/usr/bin/env python3
"""Build a deterministic, bounded project-context manifest for the ADLC skill."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


CONTRACT_VERSION = "1.0.0"
COMMANDS = (
    "init",
    "shape",
    "build",
    "fix",
    "review",
    "harden",
    "ship",
    "status",
    "resume",
    "doctor",
    "learn",
)
INSTRUCTION_NAMES = ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md")
PACKAGE_NAMES = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod")
ADLC_PATHS = (
    ".adlc/PROJECT.md",
    ".adlc/ENGINEERING.md",
    ".adlc/config.json",
)
IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "vendor",
}
DEFAULT_MAX_FILES = 20
DEFAULT_MAX_BYTES = 100_000
DEFAULT_PER_FILE_BYTES = 12_000
HARD_MAX_BYTES = 100_000
DISCOVERY_HARD_LIMIT = 2_000


class ContextCollisionError(RuntimeError):
    """Raised when initialization would overwrite an existing ADLC file."""


def route_command(request):
    """Resolve an explicit ADLC command; route ambiguous work to Shape."""
    normalized = request.strip().lower()
    explicit = re.fullmatch(r"/?adlc\s+([a-z]+)", normalized)
    if explicit and explicit.group(1) in COMMANDS:
        return explicit.group(1)
    bare = normalized.removeprefix("/") if hasattr(str, "removeprefix") else normalized.lstrip("/")
    if bare in COMMANDS:
        return bare
    return "shape"


def _relative(workspace, path):
    return path.relative_to(workspace).as_posix()


def _target_scope(workspace, target):
    resolved = Path(target or workspace).resolve()
    try:
        relative = resolved.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("target must be inside workspace") from exc
    if resolved.is_file():
        relative = relative.parent
    return relative


def _precedence(relative_path, target_scope):
    parts = relative_path.parts
    parent = relative_path.parent
    if relative_path.as_posix() in ADLC_PATHS:
        return 200
    if relative_path.name in PACKAGE_NAMES:
        return 300 + len(parts)
    if parent == Path("."):
        return 100
    try:
        target_scope.relative_to(parent)
        distance = len(target_scope.parts) - len(parent.parts)
        return 10 + max(distance, 0)
    except ValueError:
        return 150 + len(parts)


def _kind(relative_path):
    rendered = relative_path.as_posix()
    if rendered in ADLC_PATHS:
        return "adlc"
    if relative_path.name in PACKAGE_NAMES:
        return "package"
    return "instruction"


def _is_applicable(relative_path, target_scope):
    if relative_path.as_posix() in ADLC_PATHS:
        return True
    try:
        target_scope.relative_to(relative_path.parent)
        return True
    except ValueError:
        return False


def _discover(workspace):
    candidates = [
        workspace / relative
        for relative in ADLC_PATHS
        if (workspace / relative).is_file() and not (workspace / relative).is_symlink()
    ]
    for root, directories, files in os.walk(workspace):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES and not directory.startswith(".")
        )
        root_path = Path(root)
        for filename in sorted(files):
            path = root_path / filename
            relative = path.relative_to(workspace)
            rendered = relative.as_posix()
            if path.is_symlink() or rendered in ADLC_PATHS:
                continue
            if (
                rendered in ADLC_PATHS
                or filename in INSTRUCTION_NAMES
                or filename in PACKAGE_NAMES
            ):
                candidates.append(path)
                if len(candidates) >= DISCOVERY_HARD_LIMIT:
                    return candidates, True
    return candidates, False


def _bounded_utf8(raw, limit):
    excerpt = raw[:limit]
    while excerpt:
        try:
            return excerpt.decode("utf-8"), len(excerpt)
        except UnicodeDecodeError:
            excerpt = excerpt[:-1]
    return "", 0


def render_context_manifest(manifest):
    """Render the canonical emitted form used for the manifest byte contract."""
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _set_manifest_bytes(manifest):
    for _ in range(8):
        measured = len(render_context_manifest(manifest).encode("utf-8"))
        if manifest["totals"]["manifest_bytes"] == measured:
            return measured
        manifest["totals"]["manifest_bytes"] = measured
    return len(render_context_manifest(manifest).encode("utf-8"))


def _refresh_manifest_totals(manifest):
    manifest["totals"]["source_count"] = len(manifest["sources"])
    manifest["totals"]["excerpt_bytes"] = sum(
        item["excerpt_bytes"] for item in manifest["sources"]
    )


def _fit_emitted_manifest(manifest, max_bytes):
    warned = any("byte limit" in warning for warning in manifest["warnings"])
    while _set_manifest_bytes(manifest) > max_bytes:
        record = next(
            (item for item in reversed(manifest["sources"]) if item["excerpt_bytes"]),
            None,
        )
        if record is None:
            if manifest["sources"]:
                manifest["sources"].pop()
                _refresh_manifest_totals(manifest)
                if not warned:
                    manifest["warnings"].append(
                        "Context byte limit omitted one or more discovered candidates."
                    )
                    warned = True
                continue
            raise ValueError("max_bytes is too small for manifest metadata")
        excess = manifest["totals"]["manifest_bytes"] - max_bytes
        raw = record["excerpt"].encode("utf-8")
        excerpt, excerpt_bytes = _bounded_utf8(
            raw, max(0, len(raw) - max(excess, 1))
        )
        record["excerpt"] = excerpt
        record["excerpt_bytes"] = excerpt_bytes
        record["truncated"] = excerpt_bytes < record["original_bytes"]
        record["omitted_bytes"] = record["original_bytes"] - excerpt_bytes
        _refresh_manifest_totals(manifest)
        if not warned:
            manifest["warnings"].append(
                "Context byte limit truncated one or more bounded excerpts."
            )
            warned = True
    _set_manifest_bytes(manifest)


def build_context_manifest(
    workspace,
    command,
    target=None,
    max_files=DEFAULT_MAX_FILES,
    max_bytes=DEFAULT_MAX_BYTES,
    per_file_bytes=DEFAULT_PER_FILE_BYTES,
):
    """Return a versioned context manifest without mutating the workspace."""
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing directory")
    if command not in COMMANDS:
        raise ValueError("command must be one of: " + ", ".join(COMMANDS))
    if max_files <= 0 or max_bytes <= 0 or per_file_bytes <= 0:
        raise ValueError("context budgets must be positive")
    if max_bytes > HARD_MAX_BYTES or per_file_bytes > HARD_MAX_BYTES:
        raise ValueError("context byte budgets cannot exceed 100000")

    target_scope = _target_scope(workspace, target)
    discovered, hard_limited = _discover(workspace)
    applicable = [
        path
        for path in discovered
        if _is_applicable(path.relative_to(workspace), target_scope)
    ]
    ordered = sorted(
        applicable,
        key=lambda path: (
            _precedence(path.relative_to(workspace), target_scope),
            _relative(workspace, path),
        ),
    )
    warnings = []
    if hard_limited:
        warnings.append(
            "Discovery reached the 2000-candidate safety limit; refine the target."
        )
    if len(ordered) > max_files:
        warnings.append(
            "Context file limit omitted {} candidate(s).".format(len(ordered) - max_files)
        )

    sources = []
    remaining = max_bytes
    for path in ordered[:max_files]:
        if remaining <= 0:
            break
        raw = path.read_bytes()
        allowance = min(per_file_bytes, remaining)
        excerpt, excerpt_bytes = _bounded_utf8(raw, allowance)
        truncated = excerpt_bytes < len(raw)
        relative = path.relative_to(workspace)
        if truncated:
            warnings.append(
                "Bounded excerpt truncated {} by {} byte(s).".format(
                    relative.as_posix(), len(raw) - excerpt_bytes
                )
            )
        sources.append(
            {
                "path": relative.as_posix(),
                "kind": _kind(relative),
                "precedence": _precedence(relative, target_scope),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "original_bytes": len(raw),
                "excerpt": excerpt,
                "excerpt_bytes": excerpt_bytes,
                "truncated": truncated,
                "omitted_bytes": len(raw) - excerpt_bytes,
            }
        )
        remaining -= excerpt_bytes

    if len(sources) < min(len(ordered), max_files):
        warnings.append("Context byte limit omitted one or more discovered candidates.")

    by_name = {}
    for path in ordered:
        relative = path.relative_to(workspace)
        if _kind(relative) == "instruction":
            by_name.setdefault(relative.name, []).append(relative.as_posix())
    conflicts = [
        {
            "subject": name,
            "paths": paths,
            "resolution": "Use the lowest precedence number; retain all sources as evidence.",
        }
        for name, paths in sorted(by_name.items())
        if len(paths) > 1
    ]

    available_paths = {path.relative_to(workspace).as_posix() for path in applicable}
    missing_decisions = [
        "Missing {}; record this decision before relying on it.".format(path)
        for path in ADLC_PATHS
        if path not in available_paths
    ]
    selected_reference = "skill/reference/command-{}.md".format(command)
    reference_path = Path(__file__).resolve().parents[1] / "reference" / (
        "command-{}.md".format(command)
    )
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "workspace": ".",
        "target": target_scope.as_posix() if target_scope.parts else ".",
        "command": command,
        "selected_reference": selected_reference,
        "reference_status": "available" if reference_path.is_file() else "pending",
        "budget": {
            "max_files": max_files,
            "max_bytes": max_bytes,
            "per_file_bytes": per_file_bytes,
        },
        "sources": sources,
        "totals": {
            "discovered_count": len(applicable),
            "source_count": len(sources),
            "excerpt_bytes": sum(record["excerpt_bytes"] for record in sources),
            "manifest_bytes": 0,
        },
        "warnings": warnings,
        "conflicts": conflicts,
        "missing_decisions": missing_decisions,
    }
    _fit_emitted_manifest(manifest, max_bytes)
    return manifest


def initialize_adlc_context(workspace):
    """Create ADLC-owned context stubs only when every target is absent."""
    workspace = Path(workspace).resolve()
    templates = {
        ".adlc/ENGINEERING.md": "# Engineering\n\nRecord test, quality, and delivery decisions here.\n",
        ".adlc/PROJECT.md": "# Project\n\nRecord product intent and constraints here.\n",
        ".adlc/config.json": "{\n  \"contract_version\": \"1.0.0\"\n}\n",
    }
    collisions = [relative for relative in templates if (workspace / relative).exists()]
    if collisions:
        raise ContextCollisionError(
            "refusing to overwrite existing ADLC context: " + ", ".join(collisions)
        )
    (workspace / ".adlc").mkdir(parents=True, exist_ok=True)
    for relative, content in templates.items():
        (workspace / relative).write_text(content, encoding="utf-8")
    return sorted(templates)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--target")
    parser.add_argument("--command", choices=COMMANDS, default="shape")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--per-file-bytes", type=int, default=DEFAULT_PER_FILE_BYTES)
    parser.add_argument("--output", help="write the manifest to this path")
    parser.add_argument("--init", action="store_true", help="create ADLC-owned stubs")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.init:
        print(json.dumps({"created": initialize_adlc_context(args.workspace)}, indent=2))
        return 0
    manifest = build_context_manifest(
        args.workspace,
        args.command,
        target=args.target,
        max_files=args.max_files,
        max_bytes=args.max_bytes,
        per_file_bytes=args.per_file_bytes,
    )
    rendered = render_context_manifest(manifest)
    if args.output:
        output = Path(args.output)
        if output.exists():
            raise ContextCollisionError("refusing to overwrite output: {}".format(output))
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
