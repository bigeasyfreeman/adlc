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
        "max_bytes": 10_000,
        "per_file_bytes": 400,
    }
    first = context.build_context_manifest(**kwargs)
    second = context.build_context_manifest(**kwargs)

    assert first == second
    jsonschema.validate(first, json.loads(SCHEMA_PATH.read_text()))
    assert first["contract_version"] == "1.0.0"
    assert first["command"] == "fix"
    assert first["selected_reference"] == "skill/reference/command-fix.md"
    assert first["reference_status"] == "available"
    assert first["totals"]["manifest_bytes"] <= 10_000
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
        tmp_path, "shape", max_bytes=3_000, per_file_bytes=80
    )
    record = manifest["sources"][0]
    record["excerpt"].encode("utf-8")
    assert record["truncated"] is True
    assert record["excerpt_bytes"] <= 80
    assert manifest["warnings"]
    rendered = context.render_context_manifest(manifest).encode("utf-8")
    assert len(rendered) == manifest["totals"]["manifest_bytes"]
    assert len(rendered) <= 3_000


def test_emitted_manifest_not_only_excerpts_respects_byte_cap(tmp_path):
    context = load_context_module()
    (tmp_path / "README.md").write_text("é\n\"" * 50_000)
    manifest = context.build_context_manifest(
        tmp_path, "shape", max_bytes=12_000, per_file_bytes=100_000
    )
    emitted = context.render_context_manifest(manifest).encode("utf-8")
    assert len(emitted) <= 12_000
    assert len(emitted) == manifest["totals"]["manifest_bytes"]


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


def test_unrelated_sibling_instructions_do_not_consume_target_context(tmp_path):
    context = load_context_module()
    (tmp_path / "AGENTS.md").write_text("root")
    target = tmp_path / "src" / "service"
    target.mkdir(parents=True)
    (tmp_path / "src" / "AGENTS.md").write_text("applicable")
    sibling = tmp_path / "other"
    sibling.mkdir()
    (sibling / "AGENTS.md").write_text("unrelated")
    manifest = context.build_context_manifest(tmp_path, "fix", target=target)
    paths = {record["path"] for record in manifest["sources"]}
    assert paths == {"AGENTS.md", "src/AGENTS.md"}
    assert manifest["conflicts"][0]["paths"] == ["src/AGENTS.md", "AGENTS.md"]


def test_byte_pressure_preserves_discovered_conflicts_and_missing_truth(tmp_path):
    context = load_context_module()
    target = tmp_path / "src" / "service"
    target.mkdir(parents=True)
    (tmp_path / "AGENTS.md").write_text("root\n" + "r" * 1_500)
    (tmp_path / "src" / "AGENTS.md").write_text("nested\n" + "n" * 1_500)
    (tmp_path / ".adlc").mkdir()
    for relative in ("PROJECT.md", "ENGINEERING.md"):
        (tmp_path / ".adlc" / relative).write_text(relative + "\n" + "x" * 2_000)
    (tmp_path / ".adlc" / "config.json").write_text('{"value": "' + "x" * 2_000 + '"}')

    manifest = context.build_context_manifest(
        tmp_path, "fix", target=target, max_bytes=2_200, per_file_bytes=2_200
    )

    assert manifest["missing_decisions"] == []
    assert manifest["conflicts"][0]["paths"] == ["src/AGENTS.md", "AGENTS.md"]
    assert manifest["totals"]["manifest_bytes"] <= 2_200


def test_performance_is_bounded_at_two_hundred_candidates(tmp_path):
    context = load_context_module()
    target = tmp_path
    for index in range(200):
        target = target / "d"
        target.mkdir()
        (target / "AGENTS.md").write_text(f"instruction {index}")
    manifest = context.build_context_manifest(
        tmp_path, "status", target=target, max_files=20, max_bytes=100_000
    )
    assert manifest["totals"]["source_count"] == 20
    assert any("file limit" in warning for warning in manifest["warnings"])


def test_performance_hard_discovery_limit_reports_truncation(tmp_path):
    context = load_context_module()
    for index in range(2_001):
        directory = tmp_path / f"p{index:04d}"
        directory.mkdir()
        (directory / "AGENTS.md").write_text(str(index))
    manifest = context.build_context_manifest(tmp_path, "status")
    assert manifest["totals"]["discovered_count"] == 0
    assert any("2000-candidate safety limit" in warning for warning in manifest["warnings"])
