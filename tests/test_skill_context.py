import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "skill" / "scripts" / "context.py"
SCHEMA_PATH = ROOT / "docs" / "schemas" / "project-context-manifest.schema.json"


def load_context_module():
    spec = importlib.util.spec_from_file_location("adlc_skill_context", CONTEXT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path):
    (tmp_path / "AGENTS.md").write_text("Root convention: test before shipping.\n")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'fixture'\n\n[tool.pytest.ini_options]\naddopts = '-q'\n"
    )
    (tmp_path / "src" / "service").mkdir(parents=True)
    (tmp_path / "src" / "AGENTS.md").write_text(
        "Nested convention: service tests are mandatory.\n"
    )
    (tmp_path / "CLAUDE.md").write_text("Existing provider instruction remains authoritative.\n")
    (tmp_path / ".adlc").mkdir()
    (tmp_path / ".adlc" / "PROJECT.md").write_text("# Project\nShip safely.\n")
    return tmp_path


def test_manifest_is_schema_valid_deterministic_and_bounded(project):
    context = load_context_module()
    kwargs = {
        "workspace": project,
        "command": "fix",
        "target": project / "src" / "service",
        "max_files": 20,
        "max_bytes": 1_500,
        "per_file_bytes": 400,
    }
    first = context.build_context_manifest(**kwargs)
    second = context.build_context_manifest(**kwargs)

    assert first == second
    jsonschema.validate(first, json.loads(SCHEMA_PATH.read_text()))
    assert first["contract_version"] == "1.0.0"
    assert first["command"] == "fix"
    assert first["selected_reference"] == "skill/reference/command-fix.md"
    assert first["reference_status"] == "pending"
    assert first["totals"]["excerpt_bytes"] <= 1_500
    assert first["totals"]["source_count"] <= 20

    records = {record["path"]: record for record in first["sources"]}
    assert ".adlc/PROJECT.md" in records
    assert "CLAUDE.md" in records
    assert records["src/AGENTS.md"]["precedence"] < records["AGENTS.md"]["precedence"]
    raw = (project / "src" / "AGENTS.md").read_bytes()
    assert records["src/AGENTS.md"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert first["conflicts"]
    assert "ENGINEERING.md" in " ".join(first["missing_decisions"])


def test_excerpts_are_utf8_safe_and_report_truncation(tmp_path):
    context = load_context_module()
    (tmp_path / "README.md").write_text("é" * 1_000)
    manifest = context.build_context_manifest(
        tmp_path, "shape", max_bytes=128, per_file_bytes=80
    )
    record = manifest["sources"][0]
    record["excerpt"].encode("utf-8")
    assert record["truncated"] is True
    assert record["excerpt_bytes"] <= 80
    assert manifest["warnings"]


def test_secret_like_files_are_never_discovered(tmp_path):
    context = load_context_module()
    (tmp_path / "README.md").write_text("safe")
    (tmp_path / ".env").write_text("TOKEN=secret")
    (tmp_path / "credentials.json").write_text('{"password": "secret"}')
    manifest = context.build_context_manifest(tmp_path, "review")
    paths = {record["path"] for record in manifest["sources"]}
    assert paths == {"README.md"}
    assert "secret" not in json.dumps(manifest)


def test_initialization_refuses_collisions_atomically_and_preserves_instructions(tmp_path):
    context = load_context_module()
    agents = tmp_path / "AGENTS.md"
    agents.write_text("owned by the project")
    (tmp_path / ".adlc").mkdir()
    existing = tmp_path / ".adlc" / "PROJECT.md"
    existing.write_text("unmanaged")
    before = hashlib.sha256(agents.read_bytes()).hexdigest()

    with pytest.raises(context.ContextCollisionError):
        context.initialize_adlc_context(tmp_path)

    assert hashlib.sha256(agents.read_bytes()).hexdigest() == before
    assert existing.read_text() == "unmanaged"
    assert not (tmp_path / ".adlc" / "ENGINEERING.md").exists()


def test_initialization_creates_only_adlc_owned_files(tmp_path):
    context = load_context_module()
    created = context.initialize_adlc_context(tmp_path)
    assert created == [
        ".adlc/ENGINEERING.md",
        ".adlc/PROJECT.md",
        ".adlc/config.json",
    ]
    assert not (tmp_path / "AGENTS.md").exists()


def test_invalid_command_and_budget_are_rejected(tmp_path):
    context = load_context_module()
    with pytest.raises(ValueError):
        context.build_context_manifest(tmp_path, "deploy")
    with pytest.raises(ValueError):
        context.build_context_manifest(tmp_path, "shape", max_bytes=0)
    with pytest.raises(ValueError):
        context.build_context_manifest(tmp_path, "shape", max_bytes=100_001)


def test_symlinked_context_is_not_read(tmp_path):
    context = load_context_module()
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret")
    (tmp_path / "README.md").symlink_to(outside)
    manifest = context.build_context_manifest(tmp_path, "review")
    assert manifest["sources"] == []
    assert "secret" not in json.dumps(manifest)


def test_performance_is_bounded_at_two_hundred_candidates(tmp_path):
    context = load_context_module()
    for index in range(200):
        directory = tmp_path / f"package-{index:03d}"
        directory.mkdir()
        (directory / "AGENTS.md").write_text(f"instruction {index}")
    manifest = context.build_context_manifest(
        tmp_path, "status", max_files=20, max_bytes=10_000
    )
    assert manifest["totals"]["source_count"] == 20
    assert any("file limit" in warning for warning in manifest["warnings"])
