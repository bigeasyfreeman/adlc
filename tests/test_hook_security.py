from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import cli, hooks, install, skill_compiler  # noqa: E402


def install_with_hooks(tmp_path, provider="claude"):
    bundle = skill_compiler.compile_bundle(ROOT / "skill", provider)
    install.install_bundle(bundle, tmp_path, source_version="test")
    plan = install.plan_hooks(tmp_path, provider)
    install.enable_hooks(tmp_path, provider, consent_ref=plan["consent_ref"])
    return plan


def test_architecture_definitions_use_argv_and_map_to_admission():
    assert hooks.HOOK_DEFINITIONS
    for definition in hooks.HOOK_DEFINITIONS.values():
        assert isinstance(definition.argv, tuple)
        assert definition.argv
        assert definition.tool_name
        assert definition.action
        assert definition.permission_tier == "unrestricted"
        assert definition.side_effect_profile == "read_only"


def test_architecture_rendering_has_no_write_capability():
    source = inspect.getsource(hooks.render_hook_artifacts)
    assert ".write" not in source
    assert "mkdir" not in source
    assert "subprocess" not in source


def test_architecture_every_rendered_command_is_admitted(monkeypatch, tmp_path):
    install_with_hooks(tmp_path)
    calls = []

    def admitted(**kwargs):
        calls.append((kwargs["tool_name"], kwargs["action"]))
        return 0, {"status": "admitted", "stop_reason": None}

    monkeypatch.setattr(cli, "action_admit_payload", admitted)
    monkeypatch.setattr(hooks.subprocess, "run", lambda *_a, **_k: hooks.completed_process(0, '{"status":"pass"}', ""))
    result = hooks.run_hook_payload("claude", "session_start", tmp_path, {"cwd": str(tmp_path), "hook_event_name": "SessionStart"})
    definition = hooks.HOOK_DEFINITIONS["session_start"]
    assert result["status"] == "pass"
    assert calls == [(definition.tool_name, definition.action)]


def test_denied_action_never_executes(monkeypatch, tmp_path):
    install_with_hooks(tmp_path)
    monkeypatch.setattr(cli, "action_admit_payload", lambda **_kwargs: (1, {"status": "denied", "stop_reason": "permission_denied"}))
    monkeypatch.setattr(hooks.subprocess, "run", lambda *_a, **_k: pytest.fail("denied hook executed"))
    result = hooks.run_hook_payload("claude", "session_start", tmp_path, {"cwd": str(tmp_path), "hook_event_name": "SessionStart"})
    assert result["status"] == "denied"
    assert result["stop_reason"] == "permission_denied"


@pytest.mark.parametrize("cwd", ["../escape", "/tmp/outside", "repo; touch PWNED"])
def test_malicious_workspace_input_fails_closed(tmp_path, cwd):
    install_with_hooks(tmp_path)
    with pytest.raises(ValueError, match="hook cwd"):
        hooks.run_hook_payload("claude", "session_start", tmp_path, {"cwd": cwd, "hook_event_name": "SessionStart"})


def test_oversized_and_wrong_event_input_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="too large"):
        hooks.parse_hook_input(b"x" * (hooks.MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="event mismatch"):
        hooks.validate_hook_input("session_start", tmp_path, {"cwd": str(tmp_path), "hook_event_name": "Stop"})


def test_secret_like_output_is_redacted(monkeypatch, tmp_path):
    install_with_hooks(tmp_path)
    monkeypatch.setattr(cli, "action_admit_payload", lambda **_kwargs: (0, {"status": "admitted", "stop_reason": None}))
    raw = json.dumps({"status": "fail", "detail": "token=sk-secret-value password=hunter2"})
    monkeypatch.setattr(hooks.subprocess, "run", lambda *_a, **_k: hooks.completed_process(1, raw, "Bearer abcdefghijklmnop"))
    result = hooks.run_hook_payload("claude", "session_start", tmp_path, {"cwd": str(tmp_path), "hook_event_name": "SessionStart"})
    rendered = json.dumps(result)
    assert "sk-secret-value" not in rendered
    assert "hunter2" not in rendered
    assert "abcdefghijklmnop" not in rendered
    assert "[REDACTED]" in rendered


def test_hook_config_collision_and_symlink_ancestor_are_untouched(tmp_path):
    bundle = skill_compiler.compile_bundle(ROOT / "skill", "codex")
    install.install_bundle(bundle, tmp_path, source_version="test")
    config = tmp_path / ".codex/hooks.json"
    config.parent.mkdir(parents=True)
    config.write_text("mine\n", encoding="utf-8")
    plan = install.plan_hooks(tmp_path, "codex")
    with pytest.raises(install.InstallBlocked, match="unmanaged hook collision"):
        install.enable_hooks(tmp_path, "codex", consent_ref=plan["consent_ref"])
    assert config.read_text() == "mine\n"


def test_hook_symlink_ancestor_is_rejected_before_any_write(tmp_path):
    bundle = skill_compiler.compile_bundle(ROOT / "skill", "codex")
    install.install_bundle(bundle, tmp_path, source_version="test")
    outside = tmp_path / "outside"
    outside.mkdir()
    hooks_parent = tmp_path / ".adlc/hooks"
    hooks_parent.parent.mkdir(parents=True, exist_ok=True)
    hooks_parent.symlink_to(outside, target_is_directory=True)
    plan = install.plan_hooks(tmp_path, "codex")
    with pytest.raises(install.InstallBlocked, match="unsafe symlink ancestor"):
        install.enable_hooks(tmp_path, "codex", consent_ref=plan["consent_ref"])
    assert not (tmp_path / ".codex/hooks.json").exists()
    assert list(outside.iterdir()) == []


def test_uninstall_refuses_drifted_owned_hook(tmp_path):
    plan = install_with_hooks(tmp_path, "claude")
    config = tmp_path / plan["diff"][0]["path"]
    config.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(install.InstallBlocked, match="hook files drifted"):
        install.uninstall(tmp_path, "claude")
    assert config.exists()


def test_failed_uninstall_does_not_disable_hooks_when_bundle_drifted(tmp_path):
    plan = install_with_hooks(tmp_path, "claude")
    (tmp_path / ".claude/skills/adlc/SKILL.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(install.InstallBlocked, match="managed files drifted"):
        install.uninstall(tmp_path, "claude")
    assert all((tmp_path / item["path"]).exists() for item in plan["diff"])
    manifest = json.loads((tmp_path / ".adlc/install-manifests/claude.json").read_text())
    assert manifest["hooks_enabled"] is True
