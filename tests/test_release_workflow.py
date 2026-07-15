from __future__ import annotations

import importlib.util
import json
import tarfile
from pathlib import Path

import jsonschema


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
