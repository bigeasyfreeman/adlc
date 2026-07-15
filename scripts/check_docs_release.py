#!/usr/bin/env python3
"""Fail closed when a documentation release tag does not match source versions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = pyproject.split("[project]", 1)[1].split("[", 1)[0]
    package_match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if not package_match:
        raise ValueError("pyproject project.version is missing")
    package = package_match.group(1)
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    docs = str(config["extra"]["adlc_version"])
    tag_match = re.fullmatch(r"v(\d+\.\d+\.\d+)", args.tag)
    tag_version = tag_match.group(1) if tag_match else None
    status = "pass" if tag_version == package == docs else "blocked"
    payload = {
        "status": status,
        "tag": args.tag,
        "tag_version": tag_version,
        "package_version": package,
        "docs_version": docs,
        "deployment_authorized": False,
        "approval_required": "github-pages environment",
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"docs release alignment: {status} ({args.tag}; package={package}; docs={docs})")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
