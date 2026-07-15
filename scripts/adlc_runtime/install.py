"""Transactional lifecycle manager for generated ADLC provider bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from adlc_runtime.provider_targets import SUPPORTED_TARGETS, get_target
from adlc_runtime.skill_compiler import CompiledBundle, compile_bundle, default_source_root, write_bundle


class InstallBlocked(RuntimeError):
    def __init__(self, message: str, *, diff: Optional[Iterable[str]] = None):
        super().__init__(message)
        self.diff = sorted(diff or [])


def _version() -> str:
    try:
        return metadata.version("adlc")
    except metadata.PackageNotFoundError:
        return "0.1.0"


def _manifest_path(target: Path, provider: str) -> Path:
    return target / ".adlc" / "install-manifests" / f"{provider}.json"


def _bundle_path(target: Path, provider: str) -> Path:
    return target / get_target(provider).bundle_path


def _assert_no_symlinks(target: Path, path: Path, *, include_final: bool = False) -> None:
    try:
        relative = path.relative_to(target)
    except ValueError as error:
        raise InstallBlocked(f"managed path escapes target: {path}") from error
    parts = relative.parts if include_final else relative.parts[:-1]
    current = target
    for part in parts:
        current = current / part
        if current.is_symlink():
            unsafe = current.relative_to(target).as_posix()
            raise InstallBlocked(f"unsafe symlink ancestor: {unsafe}", diff=[unsafe])


def _assert_safe_layout(target: Path, provider: str) -> None:
    _assert_no_symlinks(target, _bundle_path(target, provider))
    _assert_no_symlinks(target, _manifest_path(target, provider), include_final=True)
    _assert_no_symlinks(target, target / ".adlc" / "staging", include_final=True)
    _assert_no_symlinks(target, target / ".adlc" / "rollbacks" / provider, include_final=True)
    _assert_no_symlinks(target, target / ".adlc" / "links" / provider, include_final=True)


def _read_manifest(target: Path, provider: str) -> Dict[str, Any]:
    path = _manifest_path(target, provider)
    if not path.is_file():
        raise InstallBlocked(f"no managed {provider} installation found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"source_version", "provider", "target_paths", "digests", "ownership", "rollback_ref"}
    if not required.issubset(payload) or payload.get("provider") != provider or payload.get("ownership") != "adlc-managed":
        raise InstallBlocked(f"invalid managed install manifest: {path}")
    payload.setdefault("hooks_enabled", False)
    payload.setdefault("hook_paths", [])
    payload.setdefault("hook_digests", {})
    payload.setdefault("hook_consent_ref", None)
    return payload


def _write_manifest_atomic(path: Path, payload: Dict[str, Any]) -> None:
    import jsonschema

    candidates = [
        Path(__file__).resolve().parents[2] / "docs" / "schemas" / "install-manifest.schema.json",
        Path(sys.prefix) / "share" / "adlc" / "schemas" / "install-manifest.schema.json",
    ]
    schema_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if schema_path is None:
        raise FileNotFoundError("install manifest schema is unavailable")
    jsonschema.validate(payload, json.loads(schema_path.read_text(encoding="utf-8")))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _manifest(
    bundle: CompiledBundle,
    target: Path,
    source_version: str,
    rollback_ref: Optional[str],
    *,
    linked: bool,
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    bundle_path = _bundle_path(target, bundle.provider)
    previous = previous or {}
    return {
        "contract_version": "1.0.0",
        "source_version": source_version,
        "provider": bundle.provider,
        "target_paths": [str(bundle_path.relative_to(target))],
        "digests": dict(bundle.digests),
        "bundle_digest": bundle.bundle_digest,
        "ownership": "adlc-managed",
        "rollback_ref": rollback_ref,
        "linked": linked,
        "hooks_enabled": bool(previous.get("hooks_enabled", False)),
        "hook_paths": list(previous.get("hook_paths", [])),
        "hook_digests": dict(previous.get("hook_digests", {})),
        "hook_consent_ref": previous.get("hook_consent_ref"),
        "no_overclaim": "Installation proves bundle integrity, not live provider invocation.",
        "limitations": ["Generated targets are limited to Claude Code and Codex layouts."],
    }


def _diff_path(root: Path, expected: Dict[str, str]) -> list[str]:
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    } if root.exists() else set()
    changed = set(actual) ^ set(expected)
    for relative in actual & set(expected):
        import hashlib

        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected[relative]:
            changed.add(relative)
    return sorted(changed)


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def doctor(target: Path, provider: str) -> Dict[str, Any]:
    target = target.resolve()
    try:
        _assert_safe_layout(target, provider)
        manifest = _read_manifest(target, provider)
    except InstallBlocked as error:
        return {"status": "fail", "provider": provider, "issues": [str(error)]}
    bundle_path = _bundle_path(target, provider)
    issues = []
    if bundle_path.is_symlink():
        if not manifest.get("linked") or not _under(bundle_path.resolve(), target / ".adlc" / "links"):
            issues.append("<unsafe-symlink>")
    elif manifest.get("linked"):
        issues.append("<missing-managed-link>")
    if not issues:
        issues = _diff_path(bundle_path, manifest["digests"])
    hook_issues = _hook_issues(target, manifest) if manifest["hooks_enabled"] else []
    issues.extend(hook_issues)
    return {
        "status": "pass" if not issues else "fail",
        "provider": provider,
        "issues": issues,
        "hooks_enabled": manifest["hooks_enabled"],
        "hook_support": get_target(provider).hook_support,
        "manifest": str(_manifest_path(target, provider)),
        "no_overclaim": manifest["no_overclaim"],
        "limitations": manifest["limitations"],
    }


def _hook_artifacts(target: Path, provider: str) -> Dict[str, bytes]:
    from adlc_runtime.hooks import render_hook_artifacts

    return render_hook_artifacts(provider, target, sys.executable)


def _digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hook_issues(target: Path, manifest: Dict[str, Any]) -> list[str]:
    issues = []
    expected = manifest.get("hook_digests", {})
    for relative in manifest.get("hook_paths", []):
        path = target / relative
        try:
            _assert_no_symlinks(target, path, include_final=True)
        except InstallBlocked:
            issues.append(relative)
            continue
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected.get(relative):
            issues.append(relative)
    return sorted(issues)


def plan_hooks(target: Path, provider: str) -> Dict[str, Any]:
    target = target.resolve()
    manifest = _assert_managed_clean(target, provider)
    if manifest["hooks_enabled"]:
        return {
            "status": "unchanged",
            "provider": provider,
            "consent_ref": manifest["hook_consent_ref"],
            "diff": [],
        }
    artifacts = _hook_artifacts(target, provider)
    diff = [
        {"operation": "add", "path": path, "digest": _digest_bytes(content)}
        for path, content in sorted(artifacts.items())
    ]
    consent_payload = json.dumps(diff, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "status": "consent_required",
        "provider": provider,
        "consent_ref": "sha256:" + hashlib.sha256(consent_payload).hexdigest(),
        "diff": diff,
        "warning": "Provider hooks run local commands with user permissions. Review this exact diff before consent.",
    }


def enable_hooks(target: Path, provider: str, *, consent_ref: str) -> Dict[str, Any]:
    target = target.resolve()
    manifest = _assert_managed_clean(target, provider)
    plan = plan_hooks(target, provider)
    if plan["status"] == "unchanged":
        return {"status": "unchanged", "provider": provider}
    if consent_ref != plan["consent_ref"]:
        raise InstallBlocked("explicit hook consent does not match the displayed install diff")
    artifacts = _hook_artifacts(target, provider)
    paths = []
    for relative in artifacts:
        path = target / relative
        _assert_no_symlinks(target, path, include_final=True)
        if path.exists() or path.is_symlink():
            raise InstallBlocked("unmanaged hook collision; target left untouched", diff=[relative])
        paths.append(path)
    created = []
    try:
        for path, content in ((target / relative, content) for relative, content in artifacts.items()):
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
            temporary.write_bytes(content)
            os.replace(temporary, path)
            created.append(path)
        enabled = dict(manifest)
        enabled.update(
            {
                "hooks_enabled": True,
                "hook_paths": sorted(artifacts),
                "hook_digests": {path: _digest_bytes(content) for path, content in artifacts.items()},
                "hook_consent_ref": consent_ref,
            }
        )
        _write_manifest_atomic(_manifest_path(target, provider), enabled)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        _write_manifest_atomic(_manifest_path(target, provider), manifest)
        raise
    return {"status": "hooks_enabled", "provider": provider, "consent_ref": consent_ref, "paths": sorted(artifacts)}


def disable_hooks(target: Path, provider: str) -> Dict[str, Any]:
    target = target.resolve()
    _assert_safe_layout(target, provider)
    manifest = _read_manifest(target, provider)
    if not manifest["hooks_enabled"]:
        return {"status": "unchanged", "provider": provider}
    issues = _hook_issues(target, manifest)
    if issues:
        raise InstallBlocked("hook files drifted; refusing destructive lifecycle operation", diff=issues)
    tombstones = []
    try:
        for relative in manifest["hook_paths"]:
            path = target / relative
            tombstone = path.with_name(f".{path.name}.{uuid.uuid4().hex}.disabled")
            path.rename(tombstone)
            tombstones.append((path, tombstone))
        disabled = dict(manifest)
        disabled.update({"hooks_enabled": False, "hook_paths": [], "hook_digests": {}, "hook_consent_ref": None})
        _write_manifest_atomic(_manifest_path(target, provider), disabled)
    except Exception:
        for path, tombstone in reversed(tombstones):
            if tombstone.exists():
                tombstone.rename(path)
        raise
    for _path, tombstone in tombstones:
        tombstone.unlink()
    return {"status": "hooks_disabled", "provider": provider}


def _assert_managed_clean(target: Path, provider: str) -> Dict[str, Any]:
    _assert_safe_layout(target, provider)
    manifest = _read_manifest(target, provider)
    report = doctor(target, provider)
    if report["status"] != "pass":
        raise InstallBlocked("managed files drifted; refusing destructive lifecycle operation", diff=report["issues"])
    return manifest


def _stage(bundle: CompiledBundle, target: Path) -> tuple[Path, Path]:
    staging_root = target / ".adlc" / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix=f"{bundle.provider}-", dir=staging_root))
    try:
        staged = write_bundle(bundle, transaction)
    except Exception:
        shutil.rmtree(transaction, ignore_errors=True)
        raise
    return transaction, staged


def _snapshot(target: Path, provider: str, manifest: Dict[str, Any]) -> str:
    relative = Path(".adlc") / "rollbacks" / provider / uuid.uuid4().hex
    destination = target / relative
    destination.mkdir(parents=True)
    try:
        source = _bundle_path(target, provider)
        if source.is_symlink():
            shutil.copytree(source.resolve(), destination / "bundle")
        else:
            shutil.copytree(source, destination / "bundle")
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return relative.as_posix()


def _swap(target_path: Path, replacement: Path, manifest_path: Path, payload: Dict[str, Any]) -> None:
    old_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.old")
    had_old = target_path.exists() or target_path.is_symlink()
    if had_old:
        target_path.rename(old_path)
    try:
        replacement.rename(target_path)
        _write_manifest_atomic(manifest_path, payload)
    except Exception:
        if target_path.exists() or target_path.is_symlink():
            if target_path.is_dir() and not target_path.is_symlink():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
        if had_old:
            old_path.rename(target_path)
        raise
    if had_old:
        if old_path.is_dir() and not old_path.is_symlink():
            shutil.rmtree(old_path, ignore_errors=True)
        else:
            try:
                old_path.unlink()
            except OSError:
                pass


def install_bundle(bundle: CompiledBundle, target: Path, *, source_version: str) -> Dict[str, Any]:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    _assert_safe_layout(target, bundle.provider)
    destination = _bundle_path(target, bundle.provider)
    manifest_path = _manifest_path(target, bundle.provider)
    if manifest_path.exists():
        existing = _read_manifest(target, bundle.provider)
        if existing.get("bundle_digest") == bundle.bundle_digest and doctor(target, bundle.provider)["status"] == "pass":
            return {"status": "unchanged", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest}
        raise InstallBlocked("managed install exists with different content; use update")
    if destination.exists() or destination.is_symlink():
        expected = dict(bundle.digests)
        collision_diff = ["<symlink>"] if destination.is_symlink() else _diff_path(destination, expected)
        raise InstallBlocked("unmanaged collision; target left untouched", diff=collision_diff)
    transaction, staged = _stage(bundle, target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        _swap(destination, staged, manifest_path, _manifest(bundle, target, source_version, None, linked=False))
    finally:
        shutil.rmtree(transaction, ignore_errors=True)
    return {"status": "installed", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest}


def update_bundle(bundle: CompiledBundle, target: Path, *, source_version: str) -> Dict[str, Any]:
    target = target.resolve()
    previous = _assert_managed_clean(target, bundle.provider)
    if previous.get("bundle_digest") == bundle.bundle_digest:
        if previous.get("source_version") != source_version:
            previous["source_version"] = source_version
            _write_manifest_atomic(_manifest_path(target, bundle.provider), previous)
            return {"status": "updated", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest}
        return {"status": "unchanged", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest}
    rollback_ref = _snapshot(target, bundle.provider, previous)
    transaction, staged = _stage(bundle, target)
    try:
        _swap(
            _bundle_path(target, bundle.provider),
            staged,
            _manifest_path(target, bundle.provider),
            _manifest(bundle, target, source_version, rollback_ref, linked=False, previous=previous),
        )
    except Exception:
        shutil.rmtree(target / rollback_ref, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)
    return {"status": "updated", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest, "rollback_ref": rollback_ref}


def link_bundle(bundle: CompiledBundle, target: Path, *, source_version: str) -> Dict[str, Any]:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    _assert_safe_layout(target, bundle.provider)
    destination = _bundle_path(target, bundle.provider)
    manifest_path = _manifest_path(target, bundle.provider)
    if destination.exists() or destination.is_symlink() or manifest_path.exists():
        raise InstallBlocked("target already exists; use update or uninstall before link")
    link_root = target / ".adlc" / "links" / bundle.provider / bundle.bundle_digest
    shutil.rmtree(link_root, ignore_errors=True)
    compiled = write_bundle(bundle, link_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_link = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.link")
    temporary_link.symlink_to(compiled, target_is_directory=True)
    try:
        _swap(destination, temporary_link, manifest_path, _manifest(bundle, target, source_version, None, linked=True))
    except Exception:
        shutil.rmtree(link_root, ignore_errors=True)
        raise
    return {"status": "linked", "provider": bundle.provider, "bundle_digest": bundle.bundle_digest}


def rollback(target: Path, provider: str) -> Dict[str, Any]:
    target = target.resolve()
    current = _assert_managed_clean(target, provider)
    rollback_ref = current.get("rollback_ref")
    if not rollback_ref:
        raise InstallBlocked("no rollback snapshot is available")
    snapshot = target / rollback_ref
    previous = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    new_rollback = _snapshot(target, provider, current)
    transaction = Path(tempfile.mkdtemp(prefix=f"{provider}-rollback-", dir=target / ".adlc" / "staging"))
    staged = transaction / "adlc"
    shutil.copytree(snapshot / "bundle", staged)
    previous["rollback_ref"] = new_rollback
    try:
        _swap(_bundle_path(target, provider), staged, _manifest_path(target, provider), previous)
    except Exception:
        shutil.rmtree(target / new_rollback, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)
    return {"status": "rolled_back", "provider": provider, "bundle_digest": previous["bundle_digest"]}


def uninstall(target: Path, provider: str) -> Dict[str, Any]:
    target = target.resolve()
    _assert_safe_layout(target, provider)
    manifest = _read_manifest(target, provider)
    hook_issues = _hook_issues(target, manifest) if manifest["hooks_enabled"] else []
    if hook_issues:
        raise InstallBlocked("hook files drifted; refusing destructive lifecycle operation", diff=hook_issues)
    report = doctor(target, provider)
    if report["status"] != "pass":
        raise InstallBlocked("managed files drifted; refusing destructive lifecycle operation", diff=report["issues"])
    if manifest["hooks_enabled"]:
        disable_hooks(target, provider)
    _assert_managed_clean(target, provider)
    destination = _bundle_path(target, provider)
    manifest_path = _manifest_path(target, provider)
    tombstone = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.uninstall")
    destination.rename(tombstone)
    try:
        manifest_path.unlink()
    except Exception:
        tombstone.rename(destination)
        raise
    if tombstone.is_dir() and not tombstone.is_symlink():
        shutil.rmtree(tombstone)
    else:
        tombstone.unlink()
    return {"status": "uninstalled", "provider": provider}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adlc-skill", description="Compile and manage ADLC provider skill bundles.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--provider", required=True, choices=sorted(SUPPORTED_TARGETS))
    compile_parser.add_argument("--source")
    compile_parser.add_argument("--output", required=True)
    for command in ("install", "update", "link"):
        lifecycle = subparsers.add_parser(command)
        lifecycle.add_argument("--provider", required=True, choices=sorted(SUPPORTED_TARGETS))
        lifecycle.add_argument("--target", required=True)
        lifecycle.add_argument("--source")
        lifecycle.add_argument("--source-version", default=_version())
    for command in ("rollback", "uninstall", "doctor", "hooks-plan", "hooks-disable"):
        lifecycle = subparsers.add_parser(command)
        lifecycle.add_argument("--provider", required=True, choices=sorted(SUPPORTED_TARGETS))
        lifecycle.add_argument("--target", required=True)
    hooks_enable = subparsers.add_parser("hooks-enable")
    hooks_enable.add_argument("--provider", required=True, choices=sorted(SUPPORTED_TARGETS))
    hooks_enable.add_argument("--target", required=True)
    hooks_enable.add_argument("--consent-ref", required=True)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            compiled = compile_bundle(Path(args.source) if args.source else default_source_root(), args.provider)
            result = {"status": "compiled", "provider": args.provider, "path": str(write_bundle(compiled, Path(args.output))), "bundle_digest": compiled.bundle_digest}
        elif args.command in {"install", "update", "link"}:
            compiled = compile_bundle(Path(args.source) if args.source else default_source_root(), args.provider)
            operation = {"install": install_bundle, "update": update_bundle, "link": link_bundle}[args.command]
            result = operation(compiled, Path(args.target), source_version=args.source_version)
        elif args.command == "rollback":
            result = rollback(Path(args.target), args.provider)
        elif args.command == "uninstall":
            result = uninstall(Path(args.target), args.provider)
        elif args.command == "hooks-plan":
            result = plan_hooks(Path(args.target), args.provider)
        elif args.command == "hooks-enable":
            result = enable_hooks(Path(args.target), args.provider, consent_ref=args.consent_ref)
        elif args.command == "hooks-disable":
            result = disable_hooks(Path(args.target), args.provider)
        else:
            result = doctor(Path(args.target), args.provider)
    except (InstallBlocked, ValueError, FileNotFoundError) as error:
        result = {"status": "blocked", "reason": str(error), "diff": getattr(error, "diff", [])}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
