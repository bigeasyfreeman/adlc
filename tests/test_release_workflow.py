from __future__ import annotations

import importlib.util
import json
import tarfile
from argparse import Namespace
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "scripts/release.py"
WORKFLOW = ROOT / ".github/workflows/release.yml"
DOCS_WORKFLOW = ROOT / ".github/workflows/docs.yml"
PACKET_SCHEMA = ROOT / "docs/schemas/release-approval-packet.schema.json"
GO_LIVE_SCHEMA = ROOT / "docs/schemas/go-live-validation.schema.json"


def load_release():
    spec = importlib.util.spec_from_file_location("adlc_release", RELEASE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_architecture_separates_prepare_from_publish():
    source = RELEASE.read_text(encoding="utf-8")
    assert 'subparsers.add_parser("prepare"' in source
    assert 'subparsers.add_parser("publish"' in source
    assert 'subparsers.add_parser("validate-go-live"' in source
    assert "prepare_release(args)" in source
    assert "publish_release(args)" in source
    assert "external publication remains approval-blocked" in source


def test_go_live_parser_requires_clean_checkout_and_independent_auditor():
    release = load_release()
    args = release.parser().parse_args(
        ["validate-go-live", "--tag", "v0.9.0", "--clean-checkout", "--independent-auditor", "--json"]
    )
    assert args.command == "validate-go-live"
    assert args.clean_checkout is True
    assert args.independent_auditor is True


def test_architecture_publish_requires_validated_human_approval():
    source = RELEASE.read_text(encoding="utf-8")
    assert "validate_human_approval" in source
    assert "--approval-record" in source
    assert "--confirm-external-publication" in source
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "environment: pypi" in workflow
    assert "environment: github-release" in workflow
    assert "id-token: write" in workflow
    assert "approval_record_json" in workflow
    assert workflow.count("scripts/release.py publish") == 3
    assert "--target pypi_upload" in workflow
    assert "--target github_release" in workflow
    assert "--target pages_deploy" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert 'NOTES_FILE="docs/release/$RELEASE_TAG.md"' in workflow
    docs_workflow = DOCS_WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" not in docs_workflow
    assert "actions/deploy-pages" not in docs_workflow


def test_architecture_runs_dependency_and_packet_secret_audits():
    source = RELEASE.read_text(encoding="utf-8")
    assert '"dependency-vulnerability-audit"' in source
    assert '"pip_audit"' in source
    assert "assert_publication_safe(packet" in source


def test_release_notes_are_versioned_and_publication_ready():
    notes = (ROOT / "docs/release/v0.9.0.md").read_text(encoding="utf-8")
    assert notes.startswith("# ADLC 0.9.0")
    assert "Unreleased" not in notes
    assert "No release has been tagged" not in notes
    assert "Publication boundary" in notes


def test_architecture_release_claims_come_from_conformance_evidence():
    release = load_release()
    claims = release.support_claims(ROOT / "docs/evidence/provider-conformance/support-matrix.json")
    source = json.loads((ROOT / "docs/evidence/provider-conformance/support-matrix.json").read_text())
    assert claims["source_sha256"] == release.sha256_path(
        ROOT / "docs/evidence/provider-conformance/support-matrix.json"
    )
    assert claims["configurations"] == source["configurations"]


def test_release_packet_schema_requires_reproducibility_rollback_and_pending_actions():
    schema = json.loads(PACKET_SCHEMA.read_text(encoding="utf-8"))
    required = schema["required"]
    assert "reproducibility" in required
    assert "rollback" in required
    assert "external_actions" in required
    assert schema["properties"]["status"]["const"] == "awaiting_human_approval"


def test_packet_fixture_is_schema_valid_and_external_actions_are_pending():
    release = load_release()
    packet = release.test_packet()
    schema = json.loads(PACKET_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(packet, schema)
    assert packet["status"] == "awaiting_human_approval"
    assert all(action["status"] == "pending_human_approval" for action in packet["external_actions"])


def test_sdist_normalization_removes_archive_timestamp_drift(tmp_path):
    release = load_release()
    source = tmp_path / "payload.txt"
    source.write_text("stable payload\n", encoding="utf-8")
    archives = []
    for index, mtime in enumerate((100, 200), start=1):
        archive_path = tmp_path / f"build-{index}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            info = archive.gettarinfo(str(source), arcname="adlc-0.9.0/payload.txt")
            info.mtime = mtime
            with source.open("rb") as payload:
                archive.addfile(info, payload)
        release.canonicalize_sdist(archive_path, 123456789)
        archives.append(archive_path)
    assert release.sha256_path(archives[0]) == release.sha256_path(archives[1])


def test_compare_builds_records_both_exact_digest_sets(tmp_path):
    release = load_release()
    first = tmp_path / "first"
    second = tmp_path / "second"
    artifacts = tmp_path / "artifacts"
    first.mkdir()
    second.mkdir()
    for directory in (first, second):
        (directory / "adlc-0.9.0-py3-none-any.whl").write_bytes(b"wheel")
        (directory / "adlc-0.9.0.tar.gz").write_bytes(b"sdist")
    published, reproducibility = release.compare_builds(first, second, artifacts, 123)
    assert len(published) == 2
    assert [item["build"] for item in reproducibility["build_digests"]] == [1, 2]
    assert reproducibility["build_digests"][0]["artifacts"] == reproducibility["build_digests"][1]["artifacts"]


def test_prepare_rejects_dirty_tree_before_creating_output(monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "project_version", lambda: "0.9.0")
    monkeypatch.setattr(release, "docs_version", lambda: "0.9.0")
    monkeypatch.setattr(release, "git", lambda *args: "M README.md")
    with pytest.raises(release.ReleaseBlocked, match="clean source checkout"):
        release.prepare_release(Namespace(tag="fixture-v0.9.0", repository="test"))


def test_prepare_rejects_tag_package_version_drift(monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "project_version", lambda: "0.9.1")
    monkeypatch.setattr(release, "docs_version", lambda: "0.9.0")
    with pytest.raises(release.ReleaseBlocked, match="version drift"):
        release.prepare_release(Namespace(tag="fixture-v0.9.0", repository="test"))


def test_go_live_rejects_fixture_tag_and_dirty_checkout(monkeypatch):
    release = load_release()
    args = Namespace(tag="fixture-v0.9.0", clean_checkout=True, independent_auditor=True)
    with pytest.raises(release.ReleaseBlocked, match="non-fixture"):
        release.validate_go_live(args)
    args.tag = "v0.9.0"
    monkeypatch.setattr(release, "detached_head", lambda: False)
    with pytest.raises(release.ReleaseBlocked, match="detached immutable tag checkout"):
        release.validate_go_live(args)
    monkeypatch.setattr(release, "detached_head", lambda: True)
    monkeypatch.setattr(release, "git", lambda *command: "M README.md" if command[0] == "status" else "")
    with pytest.raises(release.ReleaseBlocked, match="clean checkout"):
        release.validate_go_live(args)


def test_go_live_requires_specific_distinct_auditor_identity(monkeypatch):
    release = load_release()
    values = {
        "ADLC_EXECUTOR_ID": "release-executor",
        "ADLC_EXECUTOR_SESSION_ID": "session-a",
        "ADLC_AUDITOR_ID": "go-live-auditor",
        "ADLC_AUDITOR_SESSION_ID": "session-b",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    identity = release.required_auditor_identity()
    assert identity["basis"] == "separate_session"
    assert len(identity["identity_evidence_sha256"]) == 64
    monkeypatch.setenv("ADLC_AUDITOR_SESSION_ID", "session-a")
    with pytest.raises(release.ReleaseBlocked, match="session must differ"):
        release.required_auditor_identity()


def test_go_live_schema_requires_scoped_claims_and_pending_actions():
    schema = json.loads(GO_LIVE_SCHEMA.read_text(encoding="utf-8"))
    decision = schema["allOf"][0]
    assert decision["then"]["properties"]["contradicted_claims"]["minItems"] == 1
    assert decision["else"]["properties"]["contradicted_claims"]["maxItems"] == 0
    assert schema["properties"]["external_actions"]["items"]["properties"]["status"]["const"] == (
        "pending_human_approval"
    )
    assert decision["else"]["properties"]["clean_install_matrix"]["minItems"] == 2
    assert "scoped_beta" in schema["properties"]["recommendation"]["enum"]


def test_no_go_report_is_schema_valid_and_emits_named_artifacts(tmp_path):
    release = load_release()
    identity = {
        "executor_id": "release-executor",
        "executor_session_id": "session-a",
        "auditor_id": "go-live-auditor",
        "auditor_session_id": "session-b",
        "basis": "separate_session",
        "identity_evidence_sha256": "a" * 64,
    }
    payload = {
        "contract_version": "1.0.0",
        "status": "blocked",
        "release_tag": "v0.9.0",
        "source_commit": "b" * 40,
        "audited_at": "2026-07-15T00:00:00Z",
        "auditor": identity,
        "artifact_digests": [],
        "verified_claims": [],
        "unverified_claims": [],
        "contradicted_claims": [{"claim": "go_live_gate", "reason": "fixture failure"}],
        "accepted_risks": [],
        "support_scope": [],
        "clean_install_matrix": [],
        "rollback_result": {"status": "not_run", "reinstall_verified": False},
        "external_actions": release.external_actions(),
        "recommendation": "no_go",
        "report_artifacts": {
            "go_live_validation": "docs/evidence/releases/go-live-validation.json",
            "completion_audit": "docs/evidence/releases/completion-audit.json",
        },
        "doc_honesty_section": "Fixture no-go report.",
        "no_overclaim": "No go-live claim exists.",
        "limitations": ["Fixture only.", "No publication."],
    }
    refs = release.write_go_live_artifacts(payload, tmp_path)
    assert refs == payload["report_artifacts"]
    go_live = tmp_path / "evidence-export/docs/evidence/releases/go-live-validation.json"
    completion = tmp_path / "evidence-export/docs/evidence/releases/completion-audit.json"
    jsonschema.validate(json.loads(go_live.read_text()), json.loads(GO_LIVE_SCHEMA.read_text()))
    jsonschema.validate(
        json.loads(completion.read_text()),
        json.loads((ROOT / "docs/schemas/completion-audit-report.schema.json").read_text()),
    )
    assert json.loads(completion.read_text())["status"] == "blocked"


def test_release_log_redaction_removes_private_paths_and_secret_like_values():
    release = load_release()
    private_path = "/" + "Users/private/repo"
    value = release.redact(private_path + " password=supersecret sk-abcdefghijk")
    assert private_path not in value
    assert "supersecret" not in value
    assert "sk-abcdefghijk" not in value


def test_no_go_command_prints_schema_report_and_exits_nonzero(monkeypatch, capsys):
    release = load_release()
    monkeypatch.setattr(
        release,
        "validate_go_live",
        lambda args: {"status": "blocked", "recommendation": "no_go"},
    )
    result = release.main(
        ["validate-go-live", "--tag", "v0.9.0", "--clean-checkout", "--independent-auditor", "--json"]
    )
    assert result == 1
    assert json.loads(capsys.readouterr().out)["recommendation"] == "no_go"


def test_live_support_scope_is_derived_from_three_tag_bound_reports(tmp_path):
    release = load_release()
    commit = "c" * 40
    dimensions = {"installation": "pass", "invocation": "pass", "behavior": "pass", "end_to_end": "pass"}
    for index in range(3):
        report = {
            "provider": "codex",
            "provider_version": "0.137.0",
            "harness": "codex-cli-installed-skill",
            "model": "gpt-5.4",
            "loop": "fix",
            "fixture_sha256": "d" * 64,
            "run_id": f"tag-run-{index + 1}",
            "status": "pass",
            "source_commit": commit,
            "source_tree_clean": True,
            "dimensions": dimensions,
        }
        (tmp_path / f"run-{index + 1}.report.json").write_text(json.dumps(report) + "\n")
    scope = release.live_support_scope(tmp_path, commit)
    assert scope["source_commit"] == commit
    assert scope["validation_kind"] == "tag_live_rerun"
    assert scope["run_count"] == 3
    assert len(scope["validation_runs"]) == 3
    (tmp_path / "run-3.report.json").write_text(
        json.dumps({**scope["validation_runs"][2], "source_commit": "e" * 40}) + "\n"
    )
    with pytest.raises(release.ReleaseBlocked, match="audited commit"):
        release.live_support_scope(tmp_path, commit)
    (tmp_path / "run-3.report.json").write_text(
        json.dumps({**scope["validation_runs"][2], "model": "drifted-model"}) + "\n"
    )
    with pytest.raises(release.ReleaseBlocked, match="disagree on model"):
        release.live_support_scope(tmp_path, commit)
    (tmp_path / "run-3.report.json").write_text(
        json.dumps({**scope["validation_runs"][2], "dimensions": {"installation": "pass"}}) + "\n"
    )
    with pytest.raises(release.ReleaseBlocked, match="failed, dirty, or not bound"):
        release.live_support_scope(tmp_path, commit)


def test_release_approval_is_bound_to_packet_digest_and_publish_is_non_mutating(tmp_path):
    release = load_release()
    packet_path = tmp_path / "release-approval-packet.json"
    packet_path.write_text(json.dumps(release.test_packet()) + "\n", encoding="utf-8")
    approval_path = tmp_path / "approval.json"
    approval = {
        "contract_version": "1.0.0",
        "approval_id": "approval-abcdef123456",
        "gate_id": "release_publication",
        "decision": "approved",
        "reason": "Exact candidate packet and artifact digests reviewed.",
        "decided_by": "human",
        "timestamp": "2026-07-15T00:00:00Z",
        "brief_id": "ADLC-MIG-013",
        "run_id": "release-v0.9.0",
        "session_id": "human-release-owner",
        "artifact_ref": str(packet_path),
        "packet_sha256": release.sha256_path(packet_path),
    }
    approval_path.write_text(json.dumps(approval) + "\n", encoding="utf-8")
    result = release.publish_release(
        Namespace(
            packet=packet_path,
            approval_record=approval_path,
            target="pypi_upload",
            confirm_external_publication=True,
        )
    )
    assert result["external_action_performed"] is False
    packet_path.write_text(json.dumps({**release.test_packet(), "status": "awaiting_human_approval"}, indent=2) + "\n")
    with pytest.raises(release.ReleaseBlocked, match="digest does not match"):
        release.validate_human_approval(packet_path, approval_path)


def test_python_support_claim_is_tied_to_hosted_boundary_matrix():
    release = load_release()
    claim = release.python_support_policy()
    assert claim["requires_python"] == ">=3.9"
    assert claim["hosted_ci_versions"] == ["3.9", "3.13"]
