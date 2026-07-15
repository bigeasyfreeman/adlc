from __future__ import annotations

import importlib.util
import hashlib
import json
import shutil
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


def test_redaction_replaces_unrelated_private_provider_paths():
    runner = load_runner()
    private_temp = "/" + "var/folders/ab/codex/output"
    private_home = "/" + "Users/example/work"
    value = f"read {private_temp} and {private_home} without publishing either"
    redacted = runner.redact(value, [])
    assert redacted == "read <PRIVATE_TEMP> and <USER_HOME>/work without publishing either"
    runner.ensure_redacted(redacted)


def test_verifier_scoring_ignores_commands_that_only_embed_the_verifier():
    runner = load_runner()
    verifier = "python3 -m unittest discover -s tests -v"
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": verifier, "exit_code": 0}},
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"adlc completion-audit --claim '{verifier}'",
                "exit_code": 2,
            },
        },
    ]
    assert runner.verifier_exit_codes(events, verifier) == [0]


def copy_published_bundle(tmp_path, monkeypatch, runner):
    source = ROOT / "docs/evidence/benchmarks/v0.1.0"
    destination = tmp_path / "docs/evidence/benchmarks/v0.1.0"
    shutil.copytree(source, destination)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    return destination


def test_checked_in_publication_bundle_verifies_jointly():
    runner = load_runner()
    result = runner.verify_published_bundle(
        ROOT / "docs/evidence/benchmarks/v0.1.0/publication-attestation.json"
    )
    assert result["status"] == "pass"
    assert result["reports"] == 2
    assert result["attempts"] == 6
    assert result["evidence_files"] == 56


def test_bundle_verification_fails_when_an_attested_report_hash_drifts(tmp_path, monkeypatch):
    runner = load_runner()
    bundle = copy_published_bundle(tmp_path, monkeypatch, runner)
    primary = bundle / "benchmark-report.json"
    primary.write_text(primary.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    try:
        runner.verify_published_bundle(bundle / "publication-attestation.json")
    except runner.BenchmarkError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("bundle verification accepted a drifted report hash")


def test_bundle_verification_fails_when_reports_diverge(tmp_path, monkeypatch):
    runner = load_runner()
    bundle = copy_published_bundle(tmp_path, monkeypatch, runner)
    replay_path = bundle / "independent-replay/benchmark-report.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    replay["fixture"]["id"] = "divergent-fixture"
    replay_path.write_text(json.dumps(replay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attestation_path = bundle / "publication-attestation.json"
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation["independent_replay"]["sha256"] = hashlib.sha256(replay_path.read_bytes()).hexdigest()
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        runner.verify_published_bundle(attestation_path)
    except runner.BenchmarkError as exc:
        assert "diverge on fixture" in str(exc)
    else:
        raise AssertionError("bundle verification accepted divergent reports")


def test_bundle_verification_rejects_one_report_aliased_as_independent_replay(tmp_path, monkeypatch):
    runner = load_runner()
    bundle = copy_published_bundle(tmp_path, monkeypatch, runner)
    attestation_path = bundle / "publication-attestation.json"
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation["independent_replay"] = dict(attestation["primary_report"])
    attestation["redaction_review"]["files_reviewed"] = 28
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        runner.verify_published_bundle(attestation_path)
    except runner.BenchmarkError as exc:
        assert "must be distinct paths" in str(exc)
    else:
        raise AssertionError("bundle verification accepted one report in both publication roles")


def test_bundle_verification_compares_ordered_attempt_invariants(tmp_path, monkeypatch):
    runner = load_runner()
    bundle = copy_published_bundle(tmp_path, monkeypatch, runner)
    primary_path = bundle / "benchmark-report.json"
    replay_path = bundle / "independent-replay/benchmark-report.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    first = "a" * 64
    second = "b" * 64
    for attempt, value in zip(primary["attempts"], [first, second, first]):
        attempt["invariant_sha256"] = value
    for attempt, value in zip(replay["attempts"], [second, first, first]):
        attempt["invariant_sha256"] = value
    primary_path.write_text(json.dumps(primary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    replay_path.write_text(json.dumps(replay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attestation_path = bundle / "publication-attestation.json"
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation["primary_report"]["sha256"] = hashlib.sha256(primary_path.read_bytes()).hexdigest()
    attestation["independent_replay"]["sha256"] = hashlib.sha256(replay_path.read_bytes()).hexdigest()
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        runner.verify_published_bundle(attestation_path)
    except runner.BenchmarkError as exc:
        assert "diverge on calculated invariants" in str(exc)
    else:
        raise AssertionError("bundle verification accepted reordered attempt invariants")
