#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("paths", nargs="+")
    return parser.parse_args()


def collect_changed_lines(paths: list[str]) -> dict[str, set[int]]:
    diff_output = subprocess.check_output(
        ["git", "diff", "-U0", "--", *paths],
        text=True,
    )
    changed_lines: dict[str, set[int]] = {}
    current_path: str | None = None

    for line in diff_output.splitlines():
        if line.startswith("+++ "):
            current_path = line[4:]
            if current_path.startswith("b/"):
                current_path = current_path[2:]
            changed_lines.setdefault(current_path, set())
            continue

        if not line.startswith("@@") or current_path is None:
            continue

        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue

        start = int(match.group(1))
        length = int(match.group(2) or "1")
        changed_lines[current_path].update(range(start, start + length))

    return changed_lines


def build_summary(coverage_json: Path, changed_lines: dict[str, set[int]]) -> dict[str, object]:
    coverage_data = json.loads(coverage_json.read_text())
    files_cov = coverage_data.get("files", {})

    files_summary = []
    total_coverable = 0
    total_covered = 0

    for path in sorted(changed_lines):
        file_cov = files_cov.get(path)
        if not file_cov:
            continue

        executed = set(file_cov.get("executed_lines", []))
        missing = set(file_cov.get("missing_lines", []))
        coverable = executed | missing
        changed = sorted(changed_lines[path])
        coverable_changed = [line for line in changed if line in coverable]
        covered_changed = [line for line in coverable_changed if line in executed]

        total_coverable += len(coverable_changed)
        total_covered += len(covered_changed)

        files_summary.append(
            {
                "path": path,
                "changed_lines": changed,
                "changed_executable_lines": len(coverable_changed),
                "covered_changed_lines": len(covered_changed),
                "coverage_ratio": (
                    len(covered_changed) / len(coverable_changed)
                    if coverable_changed
                    else 0.0
                ),
            }
        )

    return {
        "files": files_summary,
        "totals": {
            "changed_executable_lines": total_coverable,
            "covered_changed_lines": total_covered,
            "coverage_ratio": (total_covered / total_coverable) if total_coverable else 0.0,
        },
    }


def main() -> int:
    args = parse_args()
    summary = build_summary(Path(args.coverage_json), collect_changed_lines(args.paths))
    output_path = Path(args.output)
    output_path.write_text(json.dumps(summary, indent=2))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
