from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import hooks, install, provider_targets, skill_compiler  # noqa: E402


def installed_target(tmp_path, provider="claude"):
    bundle = skill_compiler.compile_bundle(ROOT / "skill", provider)
    install.install_bundle(bundle, tmp_path, source_version="test")
    return bundle


def test_hooks_are_disabled_by_default(tmp_path):
    installed_target(tmp_path)
    manifest = json.loads((tmp_path / ".adlc/install-manifests/claude.json").read_text())
    assert manifest["hooks_enabled"] is False
    assert manifest["hook_paths"] == []
    assert not (tmp_path / ".claude/settings.local.json").exists()


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_hook_plan_is_visible_and_requires_exact_consent(tmp_path, provider):
    installed_target(tmp_path, provider)
    plan = install.plan_hooks(tmp_path, provider)
    assert plan["status"] == "consent_required"
    assert plan["consent_ref"].startswith("sha256:")
    assert all(item["operation"] == "add" for item in plan["diff"])
    with pytest.raises(install.InstallBlocked, match="explicit hook consent"):
        install.enable_hooks(tmp_path, provider, consent_ref="wrong")
    result = install.enable_hooks(tmp_path, provider, consent_ref=plan["consent_ref"])
    assert result["status"] == "hooks_enabled"
    assert install.doctor(tmp_path, provider)["status"] == "pass"


def test_claude_uses_exec_form_and_codex_uses_native_reviewed_command(tmp_path):
    claude = hooks.render_hook_artifacts("claude", tmp_path, sys.executable)
    claude_target = provider_targets.get_target("claude")
    claude_config = json.loads(claude[claude_target.hook_config_path].decode())
    handler = claude_config["hooks"]["SessionStart"][0]["hooks"][0]
    assert handler["command"] == sys.executable
    assert handler["args"][:3] == ["-m", "adlc_runtime.hooks", "run"]
    assert handler["timeout"] == hooks.HOOK_TIMEOUT_SECONDS

    codex = hooks.render_hook_artifacts("codex", tmp_path, sys.executable)
    codex_target = provider_targets.get_target("codex")
    codex_config = json.loads(codex[codex_target.hook_config_path].decode())
    handler = codex_config["hooks"]["SessionStart"][0]["hooks"][0]
    assert handler["type"] == "command"
    assert "adlc_runtime.hooks run" in handler["command"]
    assert handler["timeout"] == hooks.HOOK_TIMEOUT_SECONDS
    assert claude_target.hook_events == codex_target.hook_events == ("SessionStart",)


def test_update_preserves_enabled_and_user_disabled_status(tmp_path):
    original = installed_target(tmp_path)
    plan = install.plan_hooks(tmp_path, "claude")
    install.enable_hooks(tmp_path, "claude", consent_ref=plan["consent_ref"])
    changed_files = dict(original.files)
    changed_files["SKILL.md"] += b"\nupdate\n"
    install.update_bundle(skill_compiler.bundle_from_files("claude", changed_files), tmp_path, source_version="two")
    assert install.doctor(tmp_path, "claude")["hooks_enabled"] is True
    install.disable_hooks(tmp_path, "claude")
    changed_files["SKILL.md"] += b"again\n"
    install.update_bundle(skill_compiler.bundle_from_files("claude", changed_files), tmp_path, source_version="three")
    assert install.doctor(tmp_path, "claude")["hooks_enabled"] is False


def test_uninstall_removes_every_owned_hook(tmp_path):
    installed_target(tmp_path, "codex")
    plan = install.plan_hooks(tmp_path, "codex")
    install.enable_hooks(tmp_path, "codex", consent_ref=plan["consent_ref"])
    owned = [tmp_path / item["path"] for item in plan["diff"]]
    install.uninstall(tmp_path, "codex")
    assert all(not path.exists() for path in owned)


def test_timeout_returns_visible_bounded_failure(tmp_path, monkeypatch):
    installed_target(tmp_path)
    plan = install.plan_hooks(tmp_path, "claude")
    install.enable_hooks(tmp_path, "claude", consent_ref=plan["consent_ref"])

    def timeout(*_args, **_kwargs):
        import subprocess

        raise subprocess.TimeoutExpired(["fixed"], hooks.HOOK_TIMEOUT_SECONDS)

    monkeypatch.setattr(hooks.subprocess, "run", timeout)
    result = hooks.run_hook_payload("claude", "session_start", tmp_path, {"cwd": str(tmp_path), "hook_event_name": "SessionStart"})
    assert result["status"] == "failed"
    assert result["stop_reason"] == "timeout"
    assert "timed out" in result["system_message"]
