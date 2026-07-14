#!/usr/bin/env python3
"""Focused failure-mode tests for ADLC's atomic persistence boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adlc_runtime.cli import (
    atomic_write_text,
    new_workflow_state,
    read_json,
    record_label_waiver,
    write_artifact,
)


class AtomicWriteTests(unittest.TestCase):
    def test_replace_failure_preserves_previous_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("previous\n", encoding="utf-8")

            with patch("adlc_runtime.cli.os.replace", side_effect=OSError("injected replace failure")):
                with self.assertRaisesRegex(OSError, "injected replace failure"):
                    atomic_write_text(path, "replacement\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "previous\n")
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_schema_failure_happens_before_artifact_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "security-review.json"
            path.write_text("previous\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "security-review-output artifact failed schema validation"):
                write_artifact(path, {"label": "pass"}, "security-review-output")

            self.assertEqual(path.read_text(encoding="utf-8"), "previous\n")

    def test_label_override_waiver_is_audited_as_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            state = new_workflow_state(
                brief_id="ATOMIC-WAIVER",
                workspace=workspace,
                phase="plan_review",
            )

            artifact_ref = record_label_waiver(
                workspace,
                state,
                "plan_review",
                {
                    "rule": "label_override",
                    "who": "human:test",
                    "reason": "Exercise the audited override contract.",
                },
            )

            self.assertEqual(artifact_ref, ".adlc/permission_audit_trail.json")
            trail = read_json(workspace / artifact_ref)
            self.assertEqual(trail["entries"][0]["action"], "override_label")
            self.assertEqual(trail["entries"][0]["side_effect_profile"], "mutating")
            self.assertEqual(trail["entries"][0]["decided_by"], "human")


if __name__ == "__main__":
    unittest.main()
