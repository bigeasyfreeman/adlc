from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import install, skill_compiler  # noqa: E402


def bundle(provider="claude"):
    return skill_compiler.compile_bundle(ROOT / "skill", provider)


def test_install_is_owned_verified_and_idempotent(tmp_path):
    first = install.install_bundle(bundle(), tmp_path, source_version="test")
    second = install.install_bundle(bundle(), tmp_path, source_version="test")
    assert first["status"] == "installed"
    assert second["status"] == "unchanged"
    assert install.doctor(tmp_path, "claude")["status"] == "pass"
    manifest = json.loads((tmp_path / ".adlc/install-manifests/claude.json").read_text())
    schema = json.loads((ROOT / "docs/schemas/install-manifest.schema.json").read_text())
    jsonschema.validate(manifest, schema)
    assert manifest["ownership"] == "adlc-managed"
    assert manifest["source_version"] == "test"
    assert manifest["provider"] == "claude"


def test_unmanaged_collision_is_blocked_and_untouched(tmp_path):
    collision = tmp_path / ".claude/skills/adlc/SKILL.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("mine\n", encoding="utf-8")
    with pytest.raises(install.InstallBlocked, match="unmanaged collision") as error:
        install.install_bundle(bundle(), tmp_path, source_version="test")
    assert collision.read_text() == "mine\n"
    assert "SKILL.md" in error.value.diff


def test_unmanaged_symlink_collision_is_not_followed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret"
    secret.write_text("untouched\n", encoding="utf-8")
    collision = tmp_path / ".claude/skills/adlc"
    collision.parent.mkdir(parents=True)
    collision.symlink_to(outside, target_is_directory=True)
    with pytest.raises(install.InstallBlocked) as error:
        install.install_bundle(bundle(), tmp_path, source_version="test")
    assert error.value.diff == ["<symlink>"]
    assert secret.read_text() == "untouched\n"


def test_update_and_rollback_restore_previous_bytes(tmp_path):
    original = bundle()
    install.install_bundle(original, tmp_path, source_version="one")
    changed_files = dict(original.files)
    changed_files["SKILL.md"] += b"\nchanged\n"
    changed = skill_compiler.bundle_from_files("claude", changed_files)
    updated = install.update_bundle(changed, tmp_path, source_version="two")
    assert updated["status"] == "updated"
    assert (tmp_path / ".claude/skills/adlc/SKILL.md").read_bytes().endswith(b"changed\n")
    rolled_back = install.rollback(tmp_path, "claude")
    assert rolled_back["status"] == "rolled_back"
    assert (tmp_path / ".claude/skills/adlc/SKILL.md").read_bytes() == original.files["SKILL.md"]


def test_interrupted_update_restores_previous_install(tmp_path, monkeypatch):
    original = bundle()
    install.install_bundle(original, tmp_path, source_version="one")
    changed_files = dict(original.files)
    changed_files["SKILL.md"] += b"\nchanged\n"
    changed = skill_compiler.bundle_from_files("claude", changed_files)
    monkeypatch.setattr(install, "_write_manifest_atomic", lambda *_: (_ for _ in ()).throw(OSError("interrupt")))
    with pytest.raises(OSError, match="interrupt"):
        install.update_bundle(changed, tmp_path, source_version="two")
    assert (tmp_path / ".claude/skills/adlc/SKILL.md").read_bytes() == original.files["SKILL.md"]
    assert not any((tmp_path / ".adlc/rollbacks/claude").iterdir())


def test_uninstall_refuses_drift_then_removes_only_owned_bundle(tmp_path):
    install.install_bundle(bundle(), tmp_path, source_version="test")
    managed = tmp_path / ".claude/skills/adlc/SKILL.md"
    managed.write_text("user edit\n", encoding="utf-8")
    with pytest.raises(install.InstallBlocked, match="managed files drifted"):
        install.uninstall(tmp_path, "claude")
    assert managed.exists()
    managed.write_bytes(bundle().files["SKILL.md"])
    result = install.uninstall(tmp_path, "claude")
    assert result["status"] == "uninstalled"
    assert not (tmp_path / ".claude/skills/adlc").exists()


def test_link_is_manifest_owned_and_doctor_verified(tmp_path):
    result = install.link_bundle(bundle("codex"), tmp_path, source_version="dev")
    target = tmp_path / ".agents/skills/adlc"
    assert result["status"] == "linked"
    assert target.is_symlink()
    assert install.doctor(tmp_path, "codex")["status"] == "pass"


def test_interrupted_link_leaves_no_target_or_cache(tmp_path, monkeypatch):
    compiled = bundle("codex")
    monkeypatch.setattr(install, "_write_manifest_atomic", lambda *_: (_ for _ in ()).throw(OSError("interrupt")))
    with pytest.raises(OSError, match="interrupt"):
        install.link_bundle(compiled, tmp_path, source_version="dev")
    assert not (tmp_path / ".agents/skills/adlc").exists()
    assert not (tmp_path / ".adlc/links/codex" / compiled.bundle_digest).exists()


def test_benchmark_install_1000_files(tmp_path):
    files = {f"reference/{index:04}.md": b"x\n" for index in range(1000)}
    files["SKILL.md"] = b"---\nname: adlc\n---\n"
    result = install.install_bundle(skill_compiler.bundle_from_files("claude", files), tmp_path, source_version="bench")
    assert result["status"] == "installed"
