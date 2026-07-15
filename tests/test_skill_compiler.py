from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import provider_targets, skill_compiler  # noqa: E402


def test_architecture_provider_targets_are_pure_declarations():
    source = inspect.getsource(provider_targets)
    assert "write_" not in source
    assert "mkdir" not in source
    assert "shutil" not in source
    assert set(provider_targets.SUPPORTED_TARGETS) == {"claude", "codex"}


def test_architecture_compiler_is_deterministic_from_one_source():
    first = skill_compiler.compile_bundle(ROOT / "skill", "claude")
    second = skill_compiler.compile_bundle(ROOT / "skill", "claude")
    assert first.files == second.files
    assert first.digests == second.digests
    assert first.bundle_digest == second.bundle_digest


def test_architecture_installer_accepts_only_compiled_bundle(monkeypatch):
    from adlc_runtime import install

    signature = inspect.signature(install.install_bundle)
    assert "bundle" in signature.parameters
    assert "source_files" not in signature.parameters


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_compiler_emits_provider_bundle_with_canonical_skill(provider):
    bundle = skill_compiler.compile_bundle(ROOT / "skill", provider)
    assert bundle.provider == provider
    assert "SKILL.md" in bundle.files
    assert "SKILL.src.md" not in bundle.files
    assert bundle.files["SKILL.md"].startswith(b"---\nname: adlc")
    assert "reference/command-build.md" in bundle.files
    assert "scripts/context.py" in bundle.files
    assert "loops/public-build.json" in bundle.files
    assert "loops/public-fix.json" in bundle.files
    assert "loops/public-review.json" in bundle.files
    assert b"skill/scripts/context.py" not in bundle.files["SKILL.md"]
    assert b"skill/reference/" not in bundle.files["SKILL.md"]
    assert b"skill/reference/" not in bundle.files["scripts/context.py"]
    assert b"loops/public-fix.json" in bundle.files["reference/command-fix.md"]
    assert all(len(digest) == 64 for digest in bundle.digests.values())


@pytest.mark.parametrize("loop", ["build", "fix", "review"])
def test_bundled_public_loop_contract_matches_repository_contract(loop):
    bundled = ROOT / "skill" / "loops" / f"public-{loop}.json"
    public = ROOT / "docs" / "loop-library" / f"public-{loop}.json"
    assert bundled.read_bytes() == public.read_bytes()


def test_compiler_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported provider"):
        skill_compiler.compile_bundle(ROOT / "skill", "cursor")


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "nested\\escape"])
def test_compiler_rejects_unsafe_output_paths(unsafe):
    with pytest.raises(ValueError, match="unsafe bundle path"):
        skill_compiler.bundle_from_files("claude", {"SKILL.md": b"ok", unsafe: b"escape"})


def test_benchmark_compile_scales_linearly(tmp_path):
    source = tmp_path / "skill"
    (source / "reference").mkdir(parents=True)
    (source / "SKILL.src.md").write_text("---\nname: adlc\n---\n", encoding="utf-8")
    for index in range(1000):
        (source / "reference" / f"part-{index:04}.md").write_text("bounded\n", encoding="utf-8")
    bundle = skill_compiler.compile_bundle(source, "codex")
    assert len(bundle.files) == 1001
