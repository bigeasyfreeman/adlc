#!/usr/bin/env python3
"""Contract tests for provider conformance evidence."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "docs/schemas/provider-conformance-report.schema.json").read_text(
        encoding="utf-8"
    )
)


def report(*, clean: bool = True) -> dict:
    return {
        "contract_version": "1.0.0",
        "evidence_status": (
            "current_conformance" if clean else "candidate_conformance"
        ),
        "runtime": "claude",
        "model": "claude-sonnet-test",
        "source_commit": "a" * 40,
        "source_tree_clean": clean,
        "adapter": {
            "path": "scripts/adlc_runtime/adapters/claude.sh",
            "sha256": "b" * 64,
        },
        "fixture_sha256": "c" * 64,
        "auth_path": "settings-file",
        "started_at": "2026-07-13T12:00:00Z",
        "finished_at": "2026-07-13T12:05:00Z",
        "stages": [
            {
                "name": "triage",
                "ok": True,
                "artifact": "tests/smoke/artifacts/triage.json",
                "duration_ms": 100,
            }
        ],
        "overall": "pass",
        "cost_estimate_tokens": 50000,
    }


class ProviderConformanceSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft7Validator(SCHEMA)

    def assert_valid(self, payload: dict) -> None:
        self.assertEqual([], list(self.validator.iter_errors(payload)))

    def assert_invalid(self, payload: dict) -> None:
        self.assertTrue(list(self.validator.iter_errors(payload)))

    def test_clean_and_dirty_passes_are_distinguished(self) -> None:
        self.assert_valid(report(clean=True))
        self.assert_valid(report(clean=False))

        mislabeled = report(clean=False)
        mislabeled["evidence_status"] = "current_conformance"
        self.assert_invalid(mislabeled)

    def test_passing_report_cannot_hide_a_failed_stage(self) -> None:
        payload = deepcopy(report())
        payload["stages"][0]["ok"] = False
        self.assert_invalid(payload)

    def test_failed_report_must_be_labeled_failed(self) -> None:
        payload = deepcopy(report())
        payload["overall"] = "fail"
        payload["evidence_status"] = "failed_conformance"
        payload["stages"][0]["ok"] = False
        self.assert_valid(payload)

        payload["evidence_status"] = "current_conformance"
        self.assert_invalid(payload)


if __name__ == "__main__":
    unittest.main()
