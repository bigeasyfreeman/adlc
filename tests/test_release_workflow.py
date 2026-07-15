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
PACKET_SCHEMA = ROOT / "docs/schemas/release-approval-packet.schema.json"


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
    assert "prepare_release(args)" in source
    assert "publish_release(args)" in source
    assert "external publication remains approval-blocked" in source


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


def test_architecture_runs_dependency_and_packet_secret_audits():
    source = RELEASE.read_text(encoding="utf-8")
    assert '"dependency-vulnerability-audit"' in source
    assert '"pip_audit"' in source
    assert "assert_publication_safe(packet" in source


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
