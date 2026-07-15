#!/usr/bin/env python3
"""Validate the public documentation information architecture and claims."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = [
    "docs/index.md",
    "docs/start/installation.md",
    "docs/start/first-fix.md",
    "docs/concepts/skills-loops-kernel.md",
    "docs/guides/build.md",
    "docs/guides/fix.md",
    "docs/guides/review.md",
    "docs/guides/resume.md",
    "docs/guides/provider-setup.md",
    "docs/reference/public-commands.md",
    "docs/reference/advanced-kernel.md",
    "docs/reference/configuration.md",
    "docs/reference/artifacts-and-schemas.md",
    "docs/reference/stop-reasons.md",
    "docs/trust/support-matrix.md",
    "docs/trust/security-privacy.md",
    "docs/trust/benchmark.md",
    "docs/trust/compatibility-deprecation.md",
    "docs/contribute/development.md",
    "docs/contribute/authoring.md",
    "docs/contribute/behavioral-scenarios.md",
    "docs/contribute/release-process.md",
    "docs/archive/README.md",
]
COMMUNITY = [
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "CHANGELOG.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
]
COMMANDS = ["init", "shape", "build", "fix", "review", "harden", "ship", "status", "resume", "doctor", "learn"]
COMMAND_FIELDS = [
    "## Purpose",
    "## Preconditions",
    "## Example",
    "## Procedure",
    "## Outputs",
    "## Stop states",
    "## Side effects",
    "## Approval points",
    "## Compatibility map",
    "## Troubleshooting",
    "## Honesty",
]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED_DOCS + COMMUNITY:
        path = ROOT / relative
        require(path.is_file() and bool(path.read_text(encoding="utf-8").strip()), f"missing or empty: {relative}", failures)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = [
        "## Install in 30 seconds",
        "## Run a five-minute Fix",
        "## Three evidence-bound loops",
        "## Current provider evidence",
        "## How it works",
        "## Safety and human approval",
        "## Proof, not promises",
        "## Documentation and community",
        "## Status and limitations",
    ]
    positions = [readme.find(heading) for heading in headings]
    require(all(position >= 0 for position in positions), "README is missing a required outcome-first section", failures)
    require(positions == sorted(positions), "README sections do not follow the product-contract order", failures)
    require(len(readme.splitlines()) < 220, "README has regressed into a deep operator manual", failures)
    require("bash tests/acceptance/run_readme_quickstart.sh" in readme, "README lacks the executable first-success command", failures)

    public_commands = (ROOT / "docs/reference/public-commands.md").read_text(encoding="utf-8")
    for command in COMMANDS:
        heading = f"## `/adlc {command}`"
        require(heading in public_commands, f"public command docs missing {command}", failures)
        if heading in public_commands:
            section = public_commands.split(heading, 1)[1].split("\n## ", 1)[0]
            for field in (
                "Purpose",
                "Preconditions",
                "Example",
                "Procedure",
                "Outputs",
                "Stop states",
                "Side effects",
                "Approval points",
                "Troubleshooting",
                "Compatibility",
                "Honesty",
            ):
                require(f"**{field}:**" in section, f"public command {command} missing {field}", failures)
        reference = ROOT / f"skill/reference/command-{command}.md"
        require(reference.is_file(), f"canonical command reference missing {command}", failures)
        if reference.is_file():
            text = reference.read_text(encoding="utf-8")
            for field in COMMAND_FIELDS:
                require(field in text, f"command-{command}.md missing {field}", failures)

    honesty_pages = [relative for relative in REQUIRED_DOCS if not relative.startswith("docs/contribute/") and relative != "docs/archive/README.md"]
    for relative in honesty_pages:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for field in ("doc_honesty_section", "no_overclaim", "limitations"):
            require(field in text, f"{relative} missing {field}", failures)

    renderer = subprocess.run(
        [sys.executable, "scripts/render_support_matrix.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    require(renderer.returncode == 0, renderer.stderr.strip() or "support matrix renderer check failed", failures)

    spec = importlib.util.spec_from_file_location("render_support_matrix", ROOT / "scripts/render_support_matrix.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((ROOT / "docs/evidence/provider-conformance/support-matrix.json").read_text(encoding="utf-8"))
    active, blocked = module.current_rows(data)
    rendered = module.readme_block(active, blocked)
    changed = dict(active)
    changed["provider_version"] = "claim-drift-fixture"
    require(rendered != module.readme_block(changed, blocked), "support renderer does not detect source claim drift", failures)

    for path in sorted((ROOT / "docs/archive").glob("*.md")):
        opening = "\n".join(path.read_text(encoding="utf-8").splitlines()[:12]).lower()
        require(
            bool(re.search(r"^> \*\*(?:archived|superseded):\*\*", opening, re.MULTILINE)),
            f"historical document lacks an explicit Archived or Superseded opening banner: {path.relative_to(ROOT)}",
            failures,
        )
    require("No release has been tagged yet." in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), "changelog overclaims a release", failures)

    if failures:
        print("docs contract failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"docs contract: pass ({len(REQUIRED_DOCS)} pages, {len(COMMANDS)} commands, generated claims current)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
