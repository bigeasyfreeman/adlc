#!/usr/bin/env python3
"""Fail-closed MIG009 proof for legacy ADLC surface migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DISPOSITIONS = {
    "internal_capability_pack",
    "command_reference",
    "deterministic_command",
    "deprecation",
}
MIGRATION_DATE = "2026-07-14"
LEGACY_ANTIGRAVITY_AGENTS_SHA256 = "fdc6fb623030d6f1fa09eaf1a7a15598713699243101b5caa3cec35bb8bcf010"


def fail(message: str) -> None:
    raise SystemExit(f"legacy migration check failed: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load {path.relative_to(ROOT)}: {error}")


def source_inventory(manifest: dict) -> tuple[set[str], set[str], set[str], set[str]]:
    skill_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "skills").glob("*/SKILL.md")
    }
    agent_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "agents").glob("*.md")
    }
    manifest_skills = {item["path"] for item in manifest["skills"]}
    manifest_agents = {item["path"] for item in manifest["agents"]}
    return skill_paths, agent_paths, manifest_skills, manifest_agents


def check_ledger(ledger: dict, manifest: dict) -> None:
    status = ledger.get("migration_status", {})
    if status.get("ticket") != "ADLC-MIG-009" or status.get("effective_date") != MIGRATION_DATE:
        fail("ledger lacks the dated ADLC-MIG-009 migration status")
    if status.get("default_public_skills") != ["adlc"] or status.get("default_public_agents") != []:
        fail("ledger does not declare exactly one public skill and zero public agents")
    guide = ROOT / status.get("migration_guide", "")
    if not guide.is_file() or MIGRATION_DATE not in guide.read_text(encoding="utf-8"):
        fail("dated migration guide is missing")

    skill_paths, agent_paths, manifest_skills, manifest_agents = source_inventory(manifest)
    expected = skill_paths | agent_paths
    surfaces = ledger.get("surfaces", [])
    actual = {item.get("path") for item in surfaces}
    if actual != expected:
        fail(
            f"ledger/source inventory mismatch: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}"
        )
    ids = [item.get("surface_id") for item in surfaces]
    if len(ids) != len(set(ids)):
        fail("surface ids are not unique")
    if ledger.get("summary", {}).get("total") != len(surfaces):
        fail("ledger summary total is stale")

    for item in surfaces:
        path = item["path"]
        expected_id = f"{item['surface_type']}:{item['name']}"
        if item.get("surface_id") != expected_id:
            fail(f"bad surface id for {path}")
        if item.get("disposition") not in ALLOWED_DISPOSITIONS:
            fail(f"unsupported disposition for {path}")
        if not item.get("replacement") or not item.get("reason"):
            fail(f"missing replacement or reason for {path}")
        if not item.get("consumer_refs") or not item.get("validation_refs"):
            fail(f"missing consumer or validation evidence for {path}")
        if "0.x" not in item.get("compatibility_window", ""):
            fail(f"missing compatibility window for {path}")
        if item.get("removal_authorized"):
            fail(f"MIG009 does not authorize source deletion: {path}")
        if not (ROOT / path).is_file():
            fail(f"retained source is missing: {path}")
        expected_member = path in (manifest_skills | manifest_agents)
        if item.get("manifest_member") is not expected_member:
            fail(f"manifest membership is stale for {path}")
        if item["disposition"] in {"command_reference", "deprecation"}:
            replacement = ROOT / item["replacement"]
            if not replacement.is_file():
                fail(f"replacement reference is missing for {path}: {item['replacement']}")
        if item["disposition"] == "deterministic_command" and not item["replacement"].startswith("bin/adlc "):
            fail(f"deterministic responsibility is not mapped to the kernel: {path}")

    if manifest_skills != skill_paths or not manifest_agents.issubset(agent_paths):
        fail("skills/manifest.json does not match source membership")


def check_internal_registers(ledger: dict) -> None:
    registered: set[str] = set()
    for register in ledger.get("internal_pack_registers", []):
        reference = ROOT / register["reference"]
        if not reference.is_file():
            fail(f"internal pack register is missing: {register['reference']}")
        text = reference.read_text(encoding="utf-8")
        for member in register["members"]:
            if member in registered:
                fail(f"internal skill appears in multiple registers: {member}")
            if member not in text:
                fail(f"register {register['reference']} does not document {member}")
            registered.add(member)
        command_references = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "skill" / "reference").glob("command-*.md")
        )
        if reference.name not in command_references:
            fail(f"internal pack register is unreachable from command references: {register['reference']}")
    expected = {
        item["name"]
        for item in ledger["surfaces"]
        if item["surface_type"] == "skill" and item["disposition"] == "internal_capability_pack"
    }
    if registered != expected:
        fail(
            f"internal pack register coverage mismatch: missing={sorted(expected - registered)} "
            f"extra={sorted(registered - expected)}"
        )

    roles = ledger.get("internal_loop_roles", {})
    expected_roles = {
        item["name"]
        for item in ledger["surfaces"]
        if item["surface_type"] == "agent" and item["disposition"] == "internal_capability_pack"
    }
    if set(roles.get("members", [])) != expected_roles:
        fail("internal loop role coverage mismatch")


def check_manifest_policy(manifest: dict) -> None:
    public = manifest.get("public_surface", {})
    policy = manifest.get("legacy_surface_policy", {})
    if public.get("skills") != ["adlc"] or public.get("agents") != []:
        fail("skills manifest exposes a peer public surface")
    if policy.get("default_installed") is not False:
        fail("legacy surfaces are not explicitly excluded from default installation")
    if set(policy.get("excluded_from_product", [])) != {"execute-trade", "ship-content"}:
        fail("domain exclusions are incomplete")
    fixture = ROOT / "tests/fixtures/migration/antigravity-agents-pre-mig009.md"
    if not fixture.is_file() or hashlib.sha256(fixture.read_bytes()).hexdigest() != LEGACY_ANTIGRAVITY_AGENTS_SHA256:
        fail("legacy Antigravity ownership fixture is missing or drifted")


def installed_files(target: Path, pattern: str) -> list[str]:
    return sorted(path.relative_to(target).as_posix() for path in target.glob(pattern) if path.is_file())


def check_default_install() -> None:
    with tempfile.TemporaryDirectory(prefix="adlc-mig009-") as temporary:
        target = Path(temporary)
        result = subprocess.run(
            [str(ROOT / "setup.sh"), "all", str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            fail(f"default compatibility install failed: {result.stderr.strip() or result.stdout.strip()}")
        inventories = {
            "claude": installed_files(target, ".claude/skills/*/SKILL.md"),
            "codex": installed_files(target, ".agents/skills/*/SKILL.md"),
            "cursor": installed_files(target, ".cursor/rules/adlc*.mdc"),
            "antigravity": installed_files(target, ".agent/skills/*/SKILL.md"),
            "factory": installed_files(target, ".factory/docs/skills/adlc*.md"),
        }
        expected = {
            "claude": [".claude/skills/adlc/SKILL.md"],
            "codex": [".agents/skills/adlc/SKILL.md"],
            "cursor": [".cursor/rules/adlc.mdc"],
            "antigravity": [".agent/skills/adlc/SKILL.md"],
            "factory": [".factory/docs/skills/adlc.md"],
        }
        if inventories != expected:
            fail(f"default install inventory is not canonical-only: {inventories}")
        leaked_agents = installed_files(target, ".claude/agents/*.md") + installed_files(
            target, ".factory/droids/adlc-*.md"
        )
        if leaked_agents:
            fail(f"legacy agents leaked into default install: {leaked_agents}")
        bundled_text = "\n".join(path.read_text(encoding="utf-8") for path in target.rglob("*") if path.is_file())
        if "name: execute-trade" in bundled_text or "name: ship-content" in bundled_text:
            fail("excluded domain skill leaked into default install")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args()
    ledger_path = args.ledger if args.ledger.is_absolute() else ROOT / args.ledger
    ledger = load_json(ledger_path)
    manifest = load_json(ROOT / "skills/manifest.json")
    check_ledger(ledger, manifest)
    check_internal_registers(ledger)
    check_manifest_policy(manifest)
    check_default_install()
    print(f"verified: {len(ledger['surfaces'])} legacy surfaces; one public adlc skill; zero public agents")
    print("limitation: repository-local evidence cannot enumerate unknown external forks or private consumers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
