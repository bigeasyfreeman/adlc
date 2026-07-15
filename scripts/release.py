#!/usr/bin/env python3
"""Prepare reproducible ADLC release evidence while keeping publication approval-blocked."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = ROOT / "docs/schemas/release-approval-packet.schema.json"
APPROVAL_SCHEMA = ROOT / "docs/schemas/approval-record.schema.json"
SUPPORT_MATRIX = ROOT / "docs/evidence/provider-conformance/support-matrix.json"
RELEASE_ROOT = ROOT / "release-out"
TAG_PATTERN = re.compile(r"^(fixture-)?v(\d+\.\d+\.\d+)$")
PRIVATE_PATH = re.compile(r"/(?:Users/[^/\s\"']+|(?:private/)?var/folders/[^\s\"']+)")
SECRET_LIKE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|password\s*[=:]\s*[^\s\"']+|"
    r"(?:api|access|secret)[_-]?key\s*[=:]\s*[^\s\"']+)",
    re.IGNORECASE,
)


class ReleaseBlocked(RuntimeError):
    """A release preparation or approval gate failed closed."""


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReleaseBlocked(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def redact(text: str) -> str:
    text = text.replace(str(ROOT), "<REPOSITORY>")
    return PRIVATE_PATH.sub("<PRIVATE_PATH>", text)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise ReleaseBlocked(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def project_version() -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.MULTILINE)
    if not match:
        raise ReleaseBlocked("pyproject project.version is missing")
    return match.group(1)


def docs_version() -> str:
    match = re.search(r"^\s*adlc_version:\s*([^\s]+)", (ROOT / "mkdocs.yml").read_text(), re.MULTILINE)
    if not match:
        raise ReleaseBlocked("mkdocs extra.adlc_version is missing")
    return match.group(1).strip('"\'')


def release_identity(tag: str) -> Tuple[str, bool]:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ReleaseBlocked("tag must be vX.Y.Z or fixture-vX.Y.Z")
    return match.group(2), bool(match.group(1))


def support_claims(path: Path = SUPPORT_MATRIX) -> Dict[str, Any]:
    source = read_json(path)
    configurations = source.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        raise ReleaseBlocked("provider support evidence has no configurations")
    return {
        "source": path.relative_to(ROOT).as_posix(),
        "source_sha256": sha256_path(path),
        "configurations": configurations,
        "limitations": source.get("limitations", []),
        "no_overclaim": str(source.get("no_overclaim", "")),
    }


def digest_ref(path: Path) -> Dict[str, Any]:
    return {"name": path.name, "sha256": sha256_path(path), "size": path.stat().st_size}


def run_logged(
    name: str,
    command: Sequence[str],
    evidence_dir: Path,
    *,
    cwd: Path = ROOT,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=process_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    evidence = {
        "command": [redact(str(item)) for item in command],
        "cwd": "<REPOSITORY>" if cwd == ROOT else "<ISOLATED_WORKSPACE>",
        "returncode": result.returncode,
        "status": "pass" if result.returncode == 0 else "fail",
        "stdout": redact(result.stdout),
        "stderr": redact(result.stderr),
    }
    path = evidence_dir / f"{name}.json"
    write_json(path, evidence)
    if result.returncode:
        raise ReleaseBlocked(f"release gate failed: {name} (see {path.relative_to(ROOT)})")
    return {
        "name": name,
        "status": "pass",
        "evidence_ref": path.relative_to(ROOT).as_posix(),
        "evidence_sha256": sha256_path(path),
    }


def builder_environment(path: Path, evidence_dir: Path, index: int) -> Path:
    run_logged(f"builder-{index}-venv", [sys.executable, "-m", "venv", str(path)], evidence_dir)
    python = path / "bin/python"
    run_logged(
        f"builder-{index}-dependencies",
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "build==1.2.2.post1",
            "setuptools==75.8.2",
            "wheel==0.45.1",
        ],
        evidence_dir,
    )
    return python


def build_once(index: int, temporary: Path, epoch: int, evidence_dir: Path) -> Path:
    environment = temporary / f"builder-{index}"
    output = temporary / f"build-{index}"
    source = temporary / f"source-{index}"
    output.mkdir()
    source.mkdir()
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if archive.returncode:
        raise ReleaseBlocked(f"git archive failed for build {index}: {archive.stderr.decode().strip()}")
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as source_archive:
        source_archive.extractall(source)
    for path in source.rglob("*"):
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    python = builder_environment(environment, evidence_dir, index)
    run_logged(
        f"build-{index}",
        [str(python), "-m", "build", "--no-isolation", "--sdist", "--wheel", "--outdir", str(output), "."],
        evidence_dir,
        cwd=source,
        env={"SOURCE_DATE_EPOCH": str(epoch), "PYTHONHASHSEED": "0", "TZ": "UTC"},
    )
    artifacts = sorted(path for path in output.iterdir() if path.suffix in {".whl", ".gz"})
    if len(artifacts) != 2:
        raise ReleaseBlocked(f"build {index} did not produce exactly one wheel and one source archive")
    canonicalize_sdist(next(path for path in artifacts if path.suffix == ".gz"), epoch)
    return output


def canonicalize_sdist(path: Path, epoch: int) -> None:
    with tempfile.TemporaryDirectory(prefix="adlc-sdist-normalize-") as temporary_name:
        temporary = Path(temporary_name)
        with tarfile.open(path, mode="r:gz") as archive:
            archive.extractall(temporary)
        replacement = path.with_suffix(path.suffix + ".normalized")
        with replacement.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                    for item in sorted(temporary.rglob("*"), key=lambda value: value.relative_to(temporary).as_posix()):
                        relative = item.relative_to(temporary).as_posix()
                        info = archive.gettarinfo(str(item), arcname=relative)
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.mtime = epoch
                        if info.isdir():
                            info.mode = 0o755
                            archive.addfile(info)
                        elif info.isfile():
                            info.mode = 0o755 if item.stat().st_mode & 0o111 else 0o644
                            with item.open("rb") as source:
                                archive.addfile(info, source)
                        else:
                            archive.addfile(info)
        os.replace(replacement, path)


def compare_builds(first: Path, second: Path, artifact_dir: Path, epoch: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    first_files = {path.name: path for path in first.iterdir() if path.is_file()}
    second_files = {path.name: path for path in second.iterdir() if path.is_file()}
    if set(first_files) != set(second_files):
        raise ReleaseBlocked("reproducible builds emitted different artifact names")
    build_digests = [
        {"build": index, "artifacts": [digest_ref(files[name]) for name in sorted(files)]}
        for index, files in ((1, first_files), (2, second_files))
    ]
    differences = [name for name in sorted(first_files) if sha256_path(first_files[name]) != sha256_path(second_files[name])]
    if differences:
        raise ReleaseBlocked(f"reproducible build digest mismatch: {differences}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    published = []
    for name in sorted(first_files):
        target = artifact_dir / name
        shutil.copy2(first_files[name], target)
        published.append(digest_ref(target))
    return published, {
        "status": "pass",
        "builds": 2,
        "matching_names": True,
        "matching_sha256": True,
        "source_date_epoch": epoch,
        "build_digests": build_digests,
    }


def release_identity_policy(repository: str, version: str) -> Dict[str, Any]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    name = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
    homepage = re.search(r'^Homepage\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not name or name.group(1) != "adlc" or not homepage or homepage.group(1) != "https://github.com/bigeasyfreeman/adlc":
        raise ReleaseBlocked("package or source repository identity drifted")
    return {
        "status": "pass",
        "package_name": name.group(1),
        "package_version": version,
        "requested_registry": repository,
        "registry_project": "https://pypi.org/project/adlc/" if repository == "pypi" else "local-test-index/adlc",
        "source_repository": homepage.group(1),
    }


def python_support_policy() -> Dict[str, Any]:
    package = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    requirement = re.search(r'^requires-python\s*=\s*"([^"]+)"', package, re.MULTILINE)
    discovered = set(re.findall(r'"(3\.(?:9|13))"', workflow))
    versions = ["3.9", "3.13"]
    if not requirement or requirement.group(1) != ">=3.9" or discovered != set(versions):
        raise ReleaseBlocked("Python support claim is not covered by the hosted CI boundary matrix")
    return {
        "status": "pass",
        "requires_python": requirement.group(1),
        "hosted_ci_versions": versions,
        "evidence": ".github/workflows/ci.yml",
        "claim": "minimum and newest supported Python boundaries run canonical CI before merge",
    }


def dependency_policy() -> Dict[str, Any]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    dependencies = re.findall(r'"([^"]+)"', block)
    violations = [item for item in dependencies if "@" in item or ">=" not in item or "<" not in item]
    if violations:
        raise ReleaseBlocked(f"dependency policy rejects unbounded or direct dependencies: {violations}")
    return {"status": "pass", "dependencies": dependencies, "policy": "lower-and-upper-bounded-no-direct-url"}


def wheel_metadata(wheel: Path, version: str) -> Dict[str, Any]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
        names = set(archive.namelist())
    checks = {
        "name": "Name: adlc" in metadata,
        "version": f"Version: {version}" in metadata,
        "runtime": any(name.startswith("adlc_runtime/") for name in names),
        "skill": any("share/adlc/skill/" in name for name in names),
        "schemas": any("share/adlc/schemas/" in name for name in names),
    }
    if not all(checks.values()):
        raise ReleaseBlocked(f"wheel metadata/content check failed: {checks}")
    return {"status": "pass", "checks": checks, "wheel": wheel.name}


def record_gate(name: str, value: Any, evidence_dir: Path) -> Dict[str, Any]:
    path = evidence_dir / f"{name}.json"
    write_json(path, value)
    return {
        "name": name,
        "status": "pass",
        "evidence_ref": path.relative_to(ROOT).as_posix(),
        "evidence_sha256": sha256_path(path),
    }


def reference_gate(name: str, evidence_dir: Path) -> Dict[str, Any]:
    path = evidence_dir / f"{name}.json"
    if not path.is_file():
        raise ReleaseBlocked(f"release gate evidence is missing: {name}")
    value = read_json(path)
    if value.get("status") != "pass" or value.get("returncode") != 0:
        raise ReleaseBlocked(f"release gate evidence did not pass: {name}")
    return {
        "name": name,
        "status": "pass",
        "evidence_ref": path.relative_to(ROOT).as_posix(),
        "evidence_sha256": sha256_path(path),
    }


def completion_audit(gates: Sequence[Mapping[str, Any]], evidence_dir: Path) -> Dict[str, Any]:
    required = {
        "reproducibility",
        "package-metadata",
        "release-identity",
        "python-support",
        "dependency-policy",
        "dependency-vulnerability-audit",
        "canonical-ci",
        "release-contract",
        "public-hygiene",
        "benchmark-bundle",
        "support-matrix-render",
        "docs-build",
        "docs-contract",
        "clean-test-index-install",
        "rollback",
        "release-notes",
    }
    passed = {str(gate.get("name")) for gate in gates if gate.get("status") == "pass"}
    missing = sorted(required - passed)
    if missing:
        raise ReleaseBlocked(f"completion audit is missing release gates: {missing}")
    return record_gate(
        "completion-audit",
        {"status": "pass", "required_gates": sorted(required), "missing": [], "external_actions_performed": 0},
        evidence_dir,
    )


def scan_release_output(output: Path, evidence_dir: Path) -> Dict[str, Any]:
    reviewed = 0
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.suffix in {".whl", ".gz"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if SECRET_LIKE.search(text):
            raise ReleaseBlocked(f"secret-like value found in release evidence: {path.relative_to(output)}")
        if PRIVATE_PATH.search(text):
            raise ReleaseBlocked(f"private path found in release evidence: {path.relative_to(output)}")
        reviewed += 1
    return record_gate(
        "release-output-scan",
        {"status": "pass", "files_reviewed": reviewed, "secret_matches": 0, "private_path_matches": 0},
        evidence_dir,
    )


def assert_publication_safe(value: Any, label: str) -> None:
    serialized = json.dumps(value, sort_keys=True)
    if SECRET_LIKE.search(serialized):
        raise ReleaseBlocked(f"secret-like value found in {label}")
    if PRIVATE_PATH.search(serialized):
        raise ReleaseBlocked(f"private path found in {label}")


def install_and_rehearse_rollback(
    wheel: Path, version: str, output: Path, evidence_dir: Path
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    local_index = output / "test-index/adlc"
    local_index.mkdir(parents=True)
    index_wheel = local_index / wheel.name
    shutil.copy2(wheel, index_wheel)
    (local_index / "index.html").write_text(f'<a href="{wheel.name}">{wheel.name}</a>\n', encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="adlc-release-install-") as temporary:
        environment = Path(temporary) / "venv"
        run_logged("install-venv", [sys.executable, "-m", "venv", str(environment)], evidence_dir)
        python = environment / "bin/python"
        run_logged(
            "test-index-install",
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--find-links", str(local_index), "adlc==" + version],
            evidence_dir,
        )
        run_logged(
            "installed-package-smoke",
            [str(python), "-c", "import importlib.metadata as m; assert m.version('adlc') == '" + version + "'"],
            evidence_dir,
        )
        audit_requirements = output / "audit-requirements.txt"
        audit_requirements.write_text("\n".join(dependency_policy()["dependencies"]) + "\n", encoding="utf-8")
        run_logged(
            "dependency-auditor-install",
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "pip-audit==2.9.0"],
            evidence_dir,
        )
        run_logged(
            "dependency-vulnerability-audit",
            [str(python), "-m", "pip_audit", "-r", str(audit_requirements), "--progress-spinner", "off", "--format", "json"],
            evidence_dir,
        )
        run_logged("rollback-uninstall", [str(python), "-m", "pip", "uninstall", "-y", "adlc"], evidence_dir)
        run_logged(
            "rollback-reinstall",
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--find-links", str(local_index), "adlc==" + version],
            evidence_dir,
        )
        run_logged(
            "rollback-version-check",
            [str(python), "-c", "import importlib.metadata as m; assert m.version('adlc') == '" + version + "'"],
            evidence_dir,
        )
        run_logged("installed-dependency-check", [str(python), "-m", "pip", "check"], evidence_dir)
    install_gate = record_gate(
        "clean-test-index-install",
        {
            "status": "pass",
            "version": version,
            "source": index_wheel.relative_to(ROOT).as_posix(),
            "package_smoke": "pass",
            "dependency_check": "pass",
            "vulnerability_audit": "pass",
        },
        evidence_dir,
    )
    rollback_manifest = {
        "contract_version": "1.0.0",
        "candidate": digest_ref(index_wheel),
        "test_index": local_index.relative_to(ROOT).as_posix(),
        "prior_public_release": None,
        "rehearsal": "uninstall candidate and restore it from immutable local test-index bytes",
        "status": "pass",
    }
    rollback_path = output / "rollback-manifest.json"
    write_json(rollback_path, rollback_manifest)
    rollback = {
        "status": "pass",
        "mode": "local-test-index-candidate-restore",
        "manifest_ref": rollback_path.relative_to(ROOT).as_posix(),
        "reinstall_verified": True,
        "prior_public_release": None,
    }
    return install_gate, rollback


def external_actions() -> List[Dict[str, Any]]:
    return [
        {"action": "pypi_upload", "status": "pending_human_approval", "environment": "pypi", "approval_required": True},
        {"action": "github_release", "status": "pending_human_approval", "environment": "github-release", "approval_required": True},
        {"action": "pages_deploy", "status": "pending_human_approval", "environment": "github-pages", "approval_required": True},
        {"action": "launch_communication", "status": "pending_human_approval", "environment": "launch", "approval_required": True},
    ]


def test_packet() -> Dict[str, Any]:
    digest = {"name": "adlc-0.9.0-py3-none-any.whl", "sha256": "a" * 64, "size": 1}
    gates = [
        {"name": f"gate-{index}", "status": "pass", "evidence_ref": f"evidence/{index}.json", "evidence_sha256": "b" * 64}
        for index in range(8)
    ]
    return {
        "contract_version": "1.0.0",
        "status": "awaiting_human_approval",
        "release": {"tag": "fixture-v0.9.0", "version": "0.9.0", "repository": "test", "fixture": True, "generated_at": "2026-07-15T00:00:00Z"},
        "source": {"commit": "c" * 40, "tree_clean": True, "tag_ref_verified": False, "changelog_sha256": "d" * 64},
        "artifacts": [digest, {**digest, "name": "adlc-0.9.0.tar.gz"}],
        "reproducibility": {"status": "pass", "builds": 2, "matching_names": True, "matching_sha256": True, "source_date_epoch": 1, "build_digests": [{"build": 1, "artifacts": [digest, {**digest, "name": "adlc-0.9.0.tar.gz"}]}, {"build": 2, "artifacts": [digest, {**digest, "name": "adlc-0.9.0.tar.gz"}]}]},
        "gates": gates,
        "support_claims": {"source": "docs/evidence/provider-conformance/support-matrix.json", "source_sha256": "e" * 64, "configurations": [{}], "limitations": ["fixture"], "no_overclaim": "fixture only"},
        "provenance": {"predicate_type": "https://slsa.dev/provenance/v1", "builder": "test", "source_commit": "c" * 40, "artifact_digests": [digest, {**digest, "name": "adlc-0.9.0.tar.gz"}], "signed": False},
        "rollback": {"status": "pass", "mode": "local-test-index-candidate-restore", "manifest_ref": "rollback.json", "reinstall_verified": True, "prior_public_release": None},
        "external_actions": external_actions(),
        "approval": {"decision": "pending", "required_approver": "human-release-owner", "packet_sha256_bound_at_approval": True},
        "honesty": {"doc_honesty_section": "Preparation is local candidate evidence.", "no_overclaim": "No public release exists.", "limitations": ["No prior public release exists to downgrade to."]},
    }


def prepare_release(args: argparse.Namespace) -> Dict[str, Any]:
    version, fixture = release_identity(args.tag)
    if project_version() != version or docs_version() != version:
        raise ReleaseBlocked(
            f"version drift: tag={version}, package={project_version()}, docs={docs_version()}"
        )
    dirty = git("status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise ReleaseBlocked("release preparation requires a clean source checkout")
    commit = git("rev-parse", "HEAD")
    tag_ref_verified = False
    if not fixture:
        if git("rev-parse", f"refs/tags/{args.tag}^{{commit}}") != commit:
            raise ReleaseBlocked("release tag does not resolve to the current commit")
        tag_ref_verified = True
    epoch = int(git("show", "-s", "--format=%ct", commit))
    output = RELEASE_ROOT / args.tag
    if output.exists():
        shutil.rmtree(output)
    artifact_dir = output / "artifacts"
    evidence_dir = output / "evidence"
    evidence_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="adlc-release-build-") as temporary_name:
        temporary = Path(temporary_name)
        first = build_once(1, temporary, epoch, evidence_dir)
        second = build_once(2, temporary, epoch, evidence_dir)
        artifacts, reproducibility = compare_builds(first, second, artifact_dir, epoch)

    wheel = next(path for path in artifact_dir.iterdir() if path.suffix == ".whl")
    gates: List[Dict[str, Any]] = []
    gates.append(record_gate("reproducibility", reproducibility, evidence_dir))
    gates.append(record_gate("package-metadata", wheel_metadata(wheel, version), evidence_dir))
    gates.append(record_gate("release-identity", release_identity_policy(args.repository, version), evidence_dir))
    gates.append(record_gate("python-support", python_support_policy(), evidence_dir))
    gates.append(record_gate("dependency-policy", dependency_policy(), evidence_dir))
    gates.append(
        record_gate(
            "release-notes",
            {
                "status": "pass",
                "source": "CHANGELOG.md",
                "sha256": sha256_path(ROOT / "CHANGELOG.md"),
                "version": version,
                "publication_state": "candidate-only",
            },
            evidence_dir,
        )
    )
    gates.append(run_logged("canonical-ci", [str(ROOT / "bin/adlc"), "ci", "--json"], evidence_dir))
    gates.append(run_logged("release-contract", [sys.executable, "-m", "pytest", "tests/test_release_workflow.py", "-q"], evidence_dir))
    gates.append(run_logged("public-hygiene", ["bash", "tests/test_public_hygiene.sh"], evidence_dir))
    gates.append(run_logged("benchmark-bundle", [sys.executable, "benchmarks/run.py", "--verify-published-bundle", "docs/evidence/benchmarks/v0.1.0/publication-attestation.json", "--json"], evidence_dir))
    gates.append(run_logged("support-matrix-render", [sys.executable, "scripts/render_support_matrix.py", "--check"], evidence_dir))
    gates.append(run_logged("docs-build", [sys.executable, "-m", "mkdocs", "build", "--strict"], evidence_dir))
    gates.append(run_logged("docs-contract", [sys.executable, "tests/check_built_docs.py", "site"], evidence_dir))
    install_gate, rollback = install_and_rehearse_rollback(wheel, version, output, evidence_dir)
    gates.append(install_gate)
    gates.append(reference_gate("dependency-vulnerability-audit", evidence_dir))
    gates.append(record_gate("rollback", rollback, evidence_dir))
    gates.append(completion_audit(gates, evidence_dir))
    gates.append(scan_release_output(output, evidence_dir))

    claims = support_claims()
    generated_at = datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")
    packet = {
        "contract_version": "1.0.0",
        "status": "awaiting_human_approval",
        "release": {"tag": args.tag, "version": version, "repository": args.repository, "fixture": fixture, "generated_at": generated_at},
        "source": {"commit": commit, "tree_clean": True, "tag_ref_verified": tag_ref_verified, "changelog_sha256": sha256_path(ROOT / "CHANGELOG.md")},
        "artifacts": artifacts,
        "reproducibility": reproducibility,
        "gates": gates,
        "support_claims": claims,
        "provenance": {"predicate_type": "https://slsa.dev/provenance/v1", "builder": "scripts/release.py@1", "source_commit": commit, "artifact_digests": artifacts, "signed": False},
        "rollback": rollback,
        "external_actions": external_actions(),
        "approval": {"decision": "pending", "required_approver": "human-release-owner", "packet_sha256_bound_at_approval": True},
        "honesty": {
            "doc_honesty_section": "Release preparation proves a local candidate and keeps every external action approval-blocked.",
            "no_overclaim": "No package, GitHub release, Pages deployment, or launch communication is published by prepare.",
            "limitations": ["The first release has no prior public package to downgrade to; rollback rehearses restoration from immutable candidate bytes.", "Unsigned local provenance is replaced by GitHub artifact attestation only in the protected publication workflow."],
        },
    }
    jsonschema.validate(packet, read_json(PACKET_SCHEMA))
    assert_publication_safe(packet, "release approval packet")
    packet_path = output / "release-approval-packet.json"
    write_json(packet_path, packet)
    return {
        "contract_version": "1.0.0",
        "status": "awaiting_human_approval",
        "message": "external publication remains approval-blocked",
        "packet": packet_path.relative_to(ROOT).as_posix(),
        "packet_sha256": sha256_path(packet_path),
        "artifacts": artifacts,
        "external_actions": packet["external_actions"],
    }


def validate_human_approval(packet_path: Path, approval_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    packet = read_json(packet_path)
    jsonschema.validate(packet, read_json(PACKET_SCHEMA))
    approval = read_json(approval_path)
    jsonschema.validate(approval, read_json(APPROVAL_SCHEMA))
    if approval["decision"] != "approved" or approval["decided_by"] != "human":
        raise ReleaseBlocked("publish requires an approved human approval record")
    if Path(approval["artifact_ref"]).resolve() != packet_path.resolve():
        raise ReleaseBlocked("approval record is not bound to this release packet")
    if approval.get("gate_id") != "release_publication":
        raise ReleaseBlocked("publish requires a release_publication approval record")
    if approval.get("packet_sha256") != sha256_path(packet_path):
        raise ReleaseBlocked("approval record packet digest does not match this release packet")
    return packet, approval


def publish_release(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.confirm_external_publication:
        raise ReleaseBlocked("publish requires --confirm-external-publication")
    packet, approval = validate_human_approval(args.packet, args.approval_record)
    action = next((item for item in packet["external_actions"] if item["action"] == args.target), None)
    if action is None:
        raise ReleaseBlocked(f"release packet does not authorize target: {args.target}")
    return {
        "contract_version": "1.0.0",
        "status": "approved_for_protected_workflow",
        "target": args.target,
        "packet_sha256": sha256_path(args.packet),
        "approval_id": approval["approval_id"],
        "external_action_performed": False,
        "message": "Use the protected GitHub environment job; this command performs no registry write.",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Build and verify an approval-bound release candidate.")
    prepare.add_argument("--tag", required=True)
    prepare.add_argument("--repository", choices=("test", "pypi"), required=True)
    prepare.add_argument("--verify-reproducible", action="store_true", required=True)
    prepare.add_argument("--rehearse-rollback", action="store_true", required=True)
    prepare.add_argument("--json", action="store_true")
    publish = subparsers.add_parser("publish", help="Validate approval for a protected external workflow.")
    publish.add_argument("--packet", type=Path, required=True)
    publish.add_argument("--approval-record", type=Path, required=True)
    publish.add_argument("--target", choices=("pypi_upload", "github_release", "pages_deploy", "launch_communication"), required=True)
    publish.add_argument("--confirm-external-publication", action="store_true")
    publish.add_argument("--json", action="store_true")
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = prepare_release(args) if args.command == "prepare" else publish_release(args)
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload["status"])
        return 0
    except (ReleaseBlocked, jsonschema.ValidationError) as exc:
        payload = {"status": "blocked", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else str(exc), file=sys.stdout if args.json else sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
