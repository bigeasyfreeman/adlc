"""Derive public provider support from versioned conformance reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/skill_behavior"))

from run import redact_payload  # noqa: E402

CONFORMANCE_DIMENSIONS = ("installation", "invocation", "behavior", "end_to_end")
DIMENSION_STATES = frozenset({"pass", "fail", "blocked", "not_run"})


def load_reports(directory: Path) -> list[Dict[str, Any]]:
    reports = []
    for path in sorted(directory.glob("*.report.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_evidence_ref"] = path.relative_to(ROOT).as_posix()
        reports.append(payload)
    return reports


def _validate_report(report: Mapping[str, Any]) -> None:
    dimensions = report.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(CONFORMANCE_DIMENSIONS):
        raise ValueError("conformance report dimension keys must match the four canonical dimensions")
    invalid = {value for value in dimensions.values() if value not in DIMENSION_STATES}
    if invalid:
        raise ValueError(f"invalid conformance dimension state: {sorted(invalid)}")
    for key in ("provider", "harness", "model", "provider_version", "loop", "run_id", "status", "credential_status"):
        if not isinstance(report.get(key), str) or not report[key]:
            raise ValueError(f"conformance report requires {key}")
    for key in ("source_commit", "fixture_sha256"):
        if not isinstance(report.get(key), str) or not report[key]:
            raise ValueError(f"conformance report requires {key}")


def _dimension_summary(reports: list[Mapping[str, Any]]) -> Dict[str, str]:
    summary = {}
    for dimension in CONFORMANCE_DIMENSIONS:
        values = [report["dimensions"][dimension] for report in reports]
        if any(value == "fail" for value in values):
            summary[dimension] = "fail"
        elif any(value == "blocked" for value in values):
            summary[dimension] = "blocked"
        elif all(value == "pass" for value in values):
            summary[dimension] = "pass"
        else:
            summary[dimension] = "not_run"
    return summary


def _evidence_ref(report: Mapping[str, Any]) -> str:
    return str(report.get("_evidence_ref") or f"run:{report['run_id']}")


def _aggregate(reports: list[Mapping[str, Any]]) -> Dict[str, Any]:
    durations = [int(report.get("duration_ms", 0)) for report in reports]
    costs = [report.get("cost", {}) for report in reports]
    dimensions = _dimension_summary(reports)
    failed_runs = sum(1 for report in reports if report.get("status") != "pass")
    return {
        "provider": reports[0]["provider"],
        "harness": reports[0]["harness"],
        "model": reports[0]["model"],
        "provider_version": reports[0]["provider_version"],
        "loop": reports[0]["loop"],
        "source_commit": reports[0]["source_commit"],
        "fixture_sha256": reports[0]["fixture_sha256"],
        "dimensions": dimensions,
        "run_count": len(reports),
        "failed_runs": failed_runs,
        "duration_ms": {"min": min(durations), "max": max(durations)},
        "cost": {
            "currency": "USD",
            "min": round(sum(float(cost.get("min", 0.0)) for cost in costs), 6),
            "max": round(sum(float(cost.get("max", 0.0)) for cost in costs), 6),
        },
        "evidence_refs": [_evidence_ref(report) for report in reports],
        "failures": [failure for report in reports for failure in report.get("failures", [])],
    }


def derive_support_matrix(reports: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[tuple[str, str, str, str, str, str, str], list[Mapping[str, Any]]] = {}
    for report in reports:
        _validate_report(report)
        key = (
            report["provider"],
            report["harness"],
            report["model"],
            report["provider_version"],
            report["loop"],
            report["source_commit"],
            report["fixture_sha256"],
        )
        grouped.setdefault(key, []).append(report)
    configurations = []
    excluded = []
    for key in sorted(grouped):
        run_reports = sorted(grouped[key], key=lambda item: item["run_id"])
        aggregate = _aggregate(run_reports)
        credentials_missing = any(report["credential_status"] == "missing" for report in run_reports)
        superseded = any(report.get("evidence_status") == "superseded_conformance" for report in run_reports)
        all_pass = aggregate["failed_runs"] == 0 and all(
            value == "pass" for value in aggregate["dimensions"].values()
        )
        if all_pass and not credentials_missing and not superseded:
            aggregate["label"] = "beta" if aggregate["run_count"] >= 3 else "experimental"
            configurations.append(aggregate)
        else:
            aggregate["reason"] = (
                "credentials_missing"
                if credentials_missing
                else "superseded_evidence"
                if superseded
                else "behavioral_failure"
                if aggregate["failed_runs"]
                else "incomplete_evidence"
            )
            if not aggregate["failures"]:
                aggregate["failures"] = [aggregate["reason"]]
            excluded.append(aggregate)
    return {
        "contract_version": "1.0.0",
        "dimensions": list(CONFORMANCE_DIMENSIONS),
        "configurations": configurations,
        "excluded": excluded,
        "source_report_count": sum(len(items) for items in grouped.values()),
        "no_overclaim": "Labels apply only to the named provider, harness, model, version, source commit, fixture, evidence, and dimensions.",
        "limitations": [
            "Experimental requires one passing run; beta requires at least three passing runs with no hidden failures.",
            "A report does not guarantee future provider or model behavior.",
        ],
    }


def publish_support_matrix(reports: Iterable[Mapping[str, Any]], output: Path, *, workspace: Path | None = None) -> Dict[str, Any]:
    redacted_reports = redact_payload(list(reports), workspace)
    matrix = derive_support_matrix(redacted_reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return matrix


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the ADLC provider support matrix from reports.")
    parser.add_argument("--reports", default=str(ROOT / "docs/evidence/provider-conformance"))
    parser.add_argument("--output", default=str(ROOT / "docs/evidence/provider-conformance/support-matrix.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    matrix = publish_support_matrix(load_reports(Path(args.reports)), Path(args.output), workspace=ROOT)
    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
