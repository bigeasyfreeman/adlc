from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def test_project_builds_wheel_and_console_entry_point(tmp_path):
    venv = tmp_path / "venv"
    created = run(sys.executable, "-m", "venv", str(venv))
    assert created.returncode == 0, created.stderr
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    build_dependency = run(str(python), "-m", "pip", "install", "-q", "build>=1,<2")
    assert build_dependency.returncode == 0, build_dependency.stderr
    wheel_dir = tmp_path / "wheel"
    built = run(str(python), "-m", "build", "--wheel", "--outdir", str(wheel_dir), ".")
    assert built.returncode == 0, built.stderr
    wheel = next(wheel_dir.glob("adlc-*.whl"))
    installed = run(str(python), "-m", "pip", "install", str(wheel))
    assert installed.returncode == 0, installed.stderr
    executable = venv / ("Scripts/adlc-skill.exe" if os.name == "nt" else "bin/adlc-skill")
    help_result = run(str(executable), "--help", cwd=tmp_path)
    assert help_result.returncode == 0, help_result.stderr
    assert "install" in help_result.stdout
    target = tmp_path / "target"
    installed_bundle = run(str(executable), "install", "--provider", "codex", "--target", str(target), cwd=tmp_path)
    assert installed_bundle.returncode == 0, installed_bundle.stderr
    checked_bundle = run(str(executable), "doctor", "--provider", "codex", "--target", str(target), cwd=tmp_path)
    assert checked_bundle.returncode == 0, checked_bundle.stderr
    assert '"status": "pass"' in checked_bundle.stdout
    source = run(str(python), "-c", "from adlc_runtime.skill_compiler import default_source_root; print(default_source_root())", cwd=tmp_path)
    assert source.returncode == 0, source.stderr
    assert Path(source.stdout.strip(), "SKILL.src.md").is_file()


def test_setup_sh_keeps_legacy_commands_and_migration_notice():
    text = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "MIGRATION NOTICE" in text
    assert "claude)" in text
    assert "codex)" in text
