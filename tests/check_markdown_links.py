#!/usr/bin/env python3
"""Fail when a repository-local Markdown link points at a missing file."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".adlc", ".claude", "graphify-out"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    failures: list[str] = []
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for relative in listed:
        path = ROOT / relative
        if not path.is_file() or SKIP_PARTS.intersection(path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            file_target = target.split("#", 1)[0]
            if not file_target:
                continue
            resolved = (
                ROOT / file_target.lstrip("/")
                if file_target.startswith("/")
                else path.parent / file_target
            ).resolve()
            if not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)}: {target}")
    if failures:
        print("Missing repository-local Markdown links:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("markdown links: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
