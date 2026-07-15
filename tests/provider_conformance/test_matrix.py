from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tests/skill_behavior"))

import matrix  # noqa: E402
import run_live  # noqa: E402


def report(provider, model, dimensions, *, status="pass", credential_status="available", run_id="run-1", duration_ms=100):
    return {
        "contract_version": "1.0.0",
        "provider": provider,
        "harness": f"{provider}-cli",
        "model": model,
        "provider_version": "1.0.0",
        "loop": "fix",
        "run_id": run_id,
        "status": status,
        "credential_status": credential_status,
        "dimensions": dimensions,
        "duration_ms": duration_ms,
        "cost": {"currency": "USD", "min": 0.01, "max": 0.02},
        "trace": [{"event": "provider_result", "status": status}],
        "failures": [] if status == "pass" else ["behavior_failed"],
        "no_overclaim": "Named configuration only.",
        "limitations": ["Fixture report."],
        "evidence_status": "current_conformance",
        "source_commit": "a" * 40,
        "fixture_sha256": "b" * 64,
    }


def test_architecture_dimensions_are_distinct():
    assert matrix.CONFORMANCE_DIMENSIONS == ("installation", "invocation", "behavior", "end_to_end")


def test_architecture_support_is_derived_not_configured():
    source = inspect.getsource(matrix.derive_support_matrix)
    assert "configured_label" not in source
    assert "report[\"support\"]" not in source
    reports = [
        report("codex", "gpt-5.4", {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS}, run_id=f"run-{index}")
        for index in range(3)
    ]
    support = matrix.derive_support_matrix(reports)
    assert support["configurations"][0]["label"] == "beta"
    assert support["configurations"][0]["loop"] == "fix"
    assert support["configurations"][0]["run_count"] == 3


def test_architecture_redaction_happens_before_publication(tmp_path):
    dirty = report("codex", "gpt-5.4", {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS})
    dirty["trace"][0]["secret"] = "Bearer abcdefghijklmnop"
    output = tmp_path / "published.json"
    matrix.publish_support_matrix([dirty], output, workspace=tmp_path)
    assert "abcdefghijklmnop" not in output.read_text()


def test_missing_credentials_are_not_passing_or_downgraded():
    missing = report(
        "claude",
        "claude-sonnet",
        {dimension: "not_run" for dimension in matrix.CONFORMANCE_DIMENSIONS},
        status="blocked",
        credential_status="missing",
    )
    support = matrix.derive_support_matrix([missing])
    assert support["configurations"] == []
    assert support["excluded"][0]["reason"] == "credentials_missing"
    assert support["excluded"][0]["failures"]


def test_provider_results_never_infer_across_providers():
    codex = report("codex", "gpt-5.4", {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS})
    claude = report("claude", "claude-sonnet", {dimension: "not_run" for dimension in matrix.CONFORMANCE_DIMENSIONS}, status="blocked")
    support = matrix.derive_support_matrix([codex, claude])
    assert [item["provider"] for item in support["configurations"]] == ["codex"]
    assert support["excluded"][0]["provider"] == "claude"


def test_failures_variance_timing_cost_and_raw_traces_remain_visible():
    reports = [
        report("codex", "gpt-5.4", {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS}, run_id="pass", duration_ms=100),
        report("codex", "gpt-5.4", {"installation": "pass", "invocation": "pass", "behavior": "fail", "end_to_end": "fail"}, status="fail", run_id="fail", duration_ms=400),
    ]
    support = matrix.derive_support_matrix(reports)
    excluded = support["excluded"][0]
    assert excluded["run_count"] == 2
    assert excluded["failed_runs"] == 1
    assert excluded["duration_ms"] == {"min": 100, "max": 400}
    assert excluded["cost"]["max"] >= excluded["cost"]["min"]
    assert len(excluded["evidence_refs"]) == 2


def test_historical_failure_does_not_poison_fixed_source_cohort():
    failed = report(
        "codex",
        "gpt-5.4",
        {"installation": "pass", "invocation": "pass", "behavior": "fail", "end_to_end": "fail"},
        status="fail",
        run_id="old-fail",
    )
    current = [
        report(
            "codex",
            "gpt-5.4",
            {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS},
            run_id=f"current-{index}",
        )
        for index in range(3)
    ]
    for item in current:
        item["source_commit"] = "c" * 40
        item["fixture_sha256"] = "d" * 64
    support = matrix.derive_support_matrix([failed, *current])
    assert support["configurations"][0]["label"] == "beta"
    assert support["configurations"][0]["source_commit"] == "c" * 40
    assert support["excluded"][0]["failed_runs"] == 1


def test_superseded_passing_cohort_is_visible_but_not_active_support():
    reports = [
        report(
            "codex",
            "gpt-5.4",
            {dimension: "pass" for dimension in matrix.CONFORMANCE_DIMENSIONS},
            run_id=f"old-{index}",
        )
        for index in range(3)
    ]
    for item in reports:
        item["evidence_status"] = "superseded_conformance"
    support = matrix.derive_support_matrix(reports)
    assert support["configurations"] == []
    assert support["excluded"][0]["reason"] == "superseded_evidence"


def test_invalid_dimension_value_fails_closed():
    invalid = report("codex", "gpt-5.4", {"installation": "pass"})
    with pytest.raises(ValueError, match="dimension"):
        matrix.derive_support_matrix([invalid])


def test_live_analysis_grades_trace_diff_and_verifier_not_self_report(tmp_path):
    target = tmp_path / "target"
    (target / "app").mkdir(parents=True)
    (target / "app/calculator.py").write_text("return sum(values)\n")
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=target, check=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "red"], cwd=target, check=True)
    (target / "app/calculator.py").write_text("return sum(values) / len(values)\n")
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "python3 -m unittest discover -s tests", "exit_code": 1}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "python3 -m unittest discover -s tests", "exit_code": 0}},
        {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}},
    ]
    result = run_live.analyze_run(returncode=0, events=events, target=target, red_returncode=1, green_returncode=0)
    assert result["status"] == "pass"
    assert result["assertions"]["bounded_diff"] is True
    assert result["provider_test_exit_codes"] == [1, 0]


def test_live_analysis_ignores_search_terms_and_requires_same_verifier(tmp_path):
    target = tmp_path / "target"
    (target / "app").mkdir(parents=True)
    (target / "app/calculator.py").write_text("return sum(values)\n")
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=target, check=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "red"], cwd=target, check=True)
    (target / "app/calculator.py").write_text("return sum(values) / len(values)\n")
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "rg -n 'pytest|unittest' .", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "/bin/zsh -lc 'pytest -q'", "exit_code": 2}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "/bin/zsh -lc 'PYTHONPATH=. pytest -q tests/test_calculator.py'", "exit_code": 0}},
        {"type": "turn.completed", "usage": {}},
    ]
    result = run_live.analyze_run(returncode=0, events=events, target=target, red_returncode=1, green_returncode=0)
    assert result["status"] == "fail"
    assert result["provider_test_exit_codes"] == [2, 0]
    assert result["assertions"]["provider_test_trace"] is False


def test_live_plan_requires_explicit_execute():
    parser = run_live.build_parser()
    args = parser.parse_args(["--plan", "--repetitions", "3"])
    assert args.execute is False
    assert args.repetitions == 3


def test_committed_support_matrix_is_generated_from_committed_reports():
    evidence = ROOT / "docs/evidence/provider-conformance"
    reports = matrix.load_reports(evidence)
    expected = matrix.derive_support_matrix(reports)
    committed = json.loads((evidence / "support-matrix.json").read_text())
    assert committed == expected


def test_live_report_shape_validates_provider_conformance_schema():
    schema = json.loads((ROOT / "docs/schemas/provider-conformance-report.schema.json").read_text())
    assert schema["properties"]["dimensions"]["required"] == list(matrix.CONFORMANCE_DIMENSIONS)
    assert schema["properties"]["loop"]["minLength"] == 1
