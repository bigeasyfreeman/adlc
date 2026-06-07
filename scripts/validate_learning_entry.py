#!/usr/bin/env python3
"""Validate an ADLC docs/solutions learning entry."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/schemas/learning-entry.schema.json"
REQUIRED_SECTIONS = ("Context", "Learning", "Applicability", "Evidence", "Stale Conditions")
TRACK_SECTIONS = {
    "bugfix": ("Symptom", "Root Cause", "Fix", "Prevention"),
    "knowledge": ("Guidance", "Examples"),
}
SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            return [part.strip().strip("'\"") for part in value[1:-1].split(",") if part.strip()]
    return value


def parse_frontmatter(raw: str) -> tuple[Dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError("learning entry must start with YAML frontmatter")
    end = raw.find("\n---\n", 4)
    if end == -1:
        raise ValueError("learning entry frontmatter must close with ---")
    lines = raw[4:end].splitlines()
    body = raw[end + 5 :]
    parsed: Dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            parsed[key] = parse_scalar(raw_value)
            continue
        items: List[Any] = []
        mapping: Dict[str, Any] = {}
        while index < len(lines) and lines[index].startswith("  "):
            child = lines[index]
            index += 1
            stripped = child.strip()
            if stripped.startswith("- "):
                items.append(parse_scalar(stripped[2:]))
            elif ":" in stripped:
                child_key, child_value = stripped.split(":", 1)
                mapping[child_key.strip()] = parse_scalar(child_value)
            else:
                raise ValueError(f"invalid nested frontmatter line: {child}")
        parsed[key] = items if items else mapping
    return parsed, body


def validate_schema(frontmatter: Dict[str, Any]) -> List[str]:
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise RuntimeError("jsonschema is required. Install with: pip3 install jsonschema") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(frontmatter), key=lambda item: list(item.path))
    ]


def heading_exists(body: str, heading: str) -> bool:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    return bool(pattern.search(body))


def validate_body(frontmatter: Dict[str, Any], body: str) -> List[str]:
    errors: List[str] = []
    for heading in REQUIRED_SECTIONS:
        if not heading_exists(body, heading):
            errors.append(f"body: missing required section ## {heading}")
    for heading in TRACK_SECTIONS.get(str(frontmatter.get("track")), ()):
        if not heading_exists(body, heading):
            errors.append(f"body: missing {frontmatter.get('track')} section ## {heading}")
    if not body.strip():
        errors.append("body: empty learning entry")
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(body) or pattern.search(json.dumps(frontmatter, sort_keys=True)):
            errors.append("redaction: possible secret or private credential detected")
            break
    return errors


def validate_path(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw)
    return validate_schema(frontmatter) + validate_body(frontmatter, body)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_learning_entry.py <learning-entry.md>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"learning entry not found: {path}", file=sys.stderr)
        return 2
    try:
        errors = validate_path(path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
