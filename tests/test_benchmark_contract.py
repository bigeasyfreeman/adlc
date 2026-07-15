from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks" / "run.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("adlc_benchmark", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def passing_metrics():
    return {
        "task_completion": True,
        "verifier_validity": True,
        "resume_integrity": True,
        "claim_accuracy": True,
        "scope_control": True,
        "human_decisions": 1,
    }


def test_runner_preserves_every_attempt_and_raw_evidence_reference():
    runner = load_runner()
    attempts = [
        runner.attempt_record(1, "pass", passing_metrics(), ["runs/run-001/run-report.json"]),
        runner.attempt_record(2, "fail", passing_metrics(), ["runs/run-002/run-report.json"], failure="boom"),
        runner.attempt_record(3, "blocked", passing_metrics(), ["runs/run-003/run-report.json"], failure="gate"),
    ]
    report = runner.build_report(runner.test_metadata(), runner.test_plan(3), attempts)
    assert [item["attempt"] for item in report["attempts"]] == [1, 2, 3]
    assert report["summary"]["attempted"] == 3
    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["blocked"] == 1
    assert all(item["evidence_refs"] for item in report["attempts"])


def test_scoring_cannot_mark_blocked_or_missing_evidence_as_pass():
    runner = load_runner()
    assert runner.score_attempt("blocked", passing_metrics(), ["run-report.json"])["passed"] is False
    assert runner.score_attempt("pass", passing_metrics(), [])["passed"] is False
    missing = passing_metrics()
    missing["resume_integrity"] = False
    assert runner.score_attempt("pass", missing, ["run-report.json"])["passed"] is False


def test_schema_requires_versions_redaction_and_all_run_statuses():
    schema = json.loads((ROOT / "docs/schemas/benchmark-report.schema.json").read_text(encoding="utf-8"))
    runner = load_runner()
    report = runner.build_report(
        runner.test_metadata(),
        runner.test_plan(3),
        [runner.attempt_record(index, "pass", passing_metrics(), [f"runs/run-{index:03}/run-report.json"]) for index in range(1, 4)],
    )
    jsonschema.validate(report, schema)

    missing_redaction = json.loads(json.dumps(report))
    del missing_redaction["redaction"]
    errors = list(jsonschema.Draft7Validator(schema).iter_errors(missing_redaction))
    assert errors

    missing_version = json.loads(json.dumps(report))
    del missing_version["product_version"]
    errors = list(jsonschema.Draft7Validator(schema).iter_errors(missing_version))
    assert errors


def test_public_fixture_starting_commit_is_reproducible():
    runner = load_runner()
    fixture = runner.load_fixture(ROOT / "examples/fix-demo")
    assert runner.compute_starting_commit(fixture) == fixture["starting_commit"]


def test_runner_uses_live_resumable_codex_without_a_canned_repair():
    source = RUNNER.read_text(encoding="utf-8")
    assert '"codex",\n                    "exec",\n                    "resume"' in source
    assert 'resumed_session == executor_session' in source
    assert '"--sandbox",\n                    "read-only",\n                    "--ephemeral"' in source
    assert "solution_file" not in source
    assert "product_path.write" not in source


def test_publication_attestation_requires_independent_review_and_human_approval():
    schema = json.loads(
        (ROOT / "docs/schemas/benchmark-publication-attestation.schema.json").read_text(encoding="utf-8")
    )
    approval_required = schema["properties"]["approval"]["required"]
    assert "human_approval_ref" in approval_required
    assert schema["properties"]["reviewer"]["properties"]["basis"]["const"] == "separate_codex_session"
    assert schema["properties"]["redaction_review"]["properties"]["status"]["const"] == "pass"
