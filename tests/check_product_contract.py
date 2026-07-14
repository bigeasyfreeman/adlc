#!/usr/bin/env python3
"""Deterministically verify the ADLC public product and migration contract."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COMMANDS = {
    "init",
    "shape",
    "build",
    "fix",
    "review",
    "harden",
    "ship",
    "status",
    "resume",
    "doctor",
    "learn",
}
SUPPORT_LABELS = {"unsupported", "experimental", "beta", "supported"}
DISPOSITIONS = {
    "command_reference",
    "internal_capability_pack",
    "deterministic_command",
    "deprecation",
    "deletion",
}
DECISION_IDS = {
    "ADR-ADLC-001",
    "ADR-ADLC-002",
    "ADR-ADLC-003",
    "ADR-ADLC-004",
    "ADR-ADLC-005",
    "ADR-ADLC-006",
}
APPROVED_SURFACES = {
    "public_promise",
    "initial_user",
    "first_wedge",
    "public_commands",
    "support_labels",
    "brand_voice",
    "architecture_decisions",
}


def fail(message: str) -> None:
    print(f"product contract error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(load_text(path))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
    if not isinstance(payload, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return payload


def require_headings(text: str, path: Path, headings: Iterable[str]) -> None:
    missing = [heading for heading in headings if not re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)]
    if missing:
        fail(f"{path.relative_to(ROOT)} missing headings: {', '.join(missing)}")


def manifest_inventory() -> tuple[List[Dict[str, Any]], Set[str], Set[str]]:
    manifest = load_json(ROOT / "skills/manifest.json")
    skills = manifest.get("skills")
    agents = manifest.get("agents")
    if not isinstance(skills, list) or not isinstance(agents, list):
        fail("skills/manifest.json must contain skills and agents arrays")
    skill_names = {str(item.get("name")) for item in skills if isinstance(item, dict)}
    agent_paths = {str(item.get("path")) for item in agents if isinstance(item, dict)}
    if len(skill_names) != len(skills):
        fail("skills/manifest.json contains missing or duplicate skill names")
    if len(agent_paths) != len(agents):
        fail("skills/manifest.json contains missing or duplicate agent paths")
    return skills, skill_names, agent_paths


def expected_surfaces() -> Dict[str, Dict[str, Any]]:
    skills, skill_names, manifest_agent_paths = manifest_inventory()
    surfaces: Dict[str, Dict[str, Any]] = {}
    for item in skills:
        name = str(item["name"])
        path = str(item["path"])
        if not (ROOT / path).is_file():
            fail(f"manifest skill path does not exist: {path}")
        surfaces[f"skill:{name}"] = {
            "surface_type": "skill",
            "name": name,
            "path": path,
            "manifest_member": name in skill_names,
        }
    for path in sorted((ROOT / "agents").glob("*.md")):
        relative = path.relative_to(ROOT).as_posix()
        name = path.stem
        surfaces[f"agent:{name}"] = {
            "surface_type": "agent",
            "name": name,
            "path": relative,
            "manifest_member": relative in manifest_agent_paths,
        }
    return surfaces


def verify_product(path: Path, text: str) -> None:
    require_headings(
        text,
        path,
        [
            "Public promise",
            "Initial user",
            "Problem",
            "First wedge",
            "Public commands",
            "Support labels",
            "Context ownership",
            "Success metrics",
            "Brand voice",
            "Claim rules",
            "Non-goals",
            "Honest status",
        ],
    )
    promise = "Run repeatable build, fix, and review loops with your coding agent, with every completion claim tied to evidence."
    if promise not in text:
        fail("PRODUCT.md does not contain the canonical public promise")
    if "senior engineer" not in text.lower() or "Fix loop" not in text:
        fail("PRODUCT.md must name the initial senior-engineer user and Fix-loop wedge")
    commands = set(re.findall(r"^\|\s*`/adlc ([a-z-]+)`\s*\|", text, re.MULTILINE))
    if commands != PUBLIC_COMMANDS:
        fail(f"PRODUCT.md command table mismatch: expected {sorted(PUBLIC_COMMANDS)}, found {sorted(commands)}")
    labels = set(re.findall(r"^\|\s*`(unsupported|experimental|beta|supported)`\s*\|", text, re.MULTILINE))
    if labels != SUPPORT_LABELS:
        fail(f"PRODUCT.md support-label table mismatch: expected {sorted(SUPPORT_LABELS)}, found {sorted(labels)}")
    for context_path in (".adlc/PROJECT.md", ".adlc/ENGINEERING.md", ".adlc/config.json"):
        if f"`{context_path}`" not in text:
            fail(f"PRODUCT.md missing context ownership path {context_path}")
    for marker in ("doc_honesty_section", "no_overclaim", "limitations"):
        if marker not in text:
            fail(f"PRODUCT.md missing honesty marker {marker}")


def verify_style(path: Path, text: str) -> None:
    require_headings(
        text,
        path,
        [
            "Outcome before machinery",
            "Voice",
            "Terminology",
            "Claims and evidence",
            "Provider support language",
            "Commands",
            "Accessibility and examples",
            "No-overclaim boundary",
        ],
    )
    for phrase in ("evidence-bound", "read-only", "unsupported", "experimental", "beta", "supported"):
        if phrase not in text:
            fail(f"docs/STYLE.md missing required terminology: {phrase}")


def verify_ledger(path: Path, payload: Dict[str, Any]) -> None:
    if payload.get("contract_version") != "1.0.0":
        fail("legacy ledger contract_version must be 1.0.0")
    if set(payload.get("public_commands", [])) != PUBLIC_COMMANDS:
        fail("legacy ledger public_commands do not match the product contract")
    if set(payload.get("support_labels", [])) != SUPPORT_LABELS:
        fail("legacy ledger support_labels do not match the product contract")
    decisions = payload.get("architecture_decisions")
    if (
        not isinstance(decisions, list)
        or len(decisions) != len(DECISION_IDS)
        or {item.get("decision_id") for item in decisions if isinstance(item, dict)} != DECISION_IDS
    ):
        fail("legacy ledger must reference all six architecture decisions exactly once")
    for decision in decisions:
        if not isinstance(decision, dict):
            fail("every architecture decision reference must be an object")
        for field, minimum_length in (("topic", 10), ("record", 20), ("reversal_path", 20)):
            value = decision.get(field)
            if not isinstance(value, str) or len(value.strip()) < minimum_length:
                fail(f"{decision.get('decision_id')} missing substantive {field}")
    entries = payload.get("surfaces")
    if not isinstance(entries, list):
        fail("legacy ledger surfaces must be an array")
    expected = expected_surfaces()
    actual: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("every legacy ledger surface must be an object")
        surface_id = str(entry.get("surface_id", ""))
        if not surface_id or surface_id in actual:
            fail(f"missing or duplicate surface_id: {surface_id!r}")
        actual[surface_id] = entry
        if entry.get("disposition") not in DISPOSITIONS:
            fail(f"{surface_id} has invalid disposition {entry.get('disposition')!r}")
        if entry.get("removal_authorized") is not False:
            fail(f"{surface_id} must keep removal_authorized false before migration proof")
        for field in ("replacement", "compatibility_window", "consumer_refs", "validation_refs", "reason"):
            value = entry.get(field)
            if value in (None, "", []):
                fail(f"{surface_id} missing substantive {field}")
        if entry.get("disposition") in {"deprecation", "deletion"} and not entry.get("removal_prerequisites"):
            fail(f"{surface_id} needs removal_prerequisites for {entry.get('disposition')}")
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        fail(f"legacy surface coverage mismatch; missing={missing}, extra={extra}")
    for surface_id, expected_entry in expected.items():
        entry = actual[surface_id]
        for field, value in expected_entry.items():
            if entry.get(field) != value:
                fail(f"{surface_id} {field} mismatch: expected {value!r}, found {entry.get(field)!r}")
    summary = payload.get("summary", {})
    expected_skill_count = sum(item["surface_type"] == "skill" for item in expected.values())
    expected_agent_count = sum(item["surface_type"] == "agent" for item in expected.values())
    expected_manifest_agents = sum(
        item["surface_type"] == "agent" and item["manifest_member"] for item in expected.values()
    )
    counts = {
        "skills": expected_skill_count,
        "agents": expected_agent_count,
        "manifest_agents": expected_manifest_agents,
        "total": len(expected),
    }
    if summary != counts:
        fail(f"legacy ledger summary mismatch: expected {counts}, found {summary}")


def verify_decisions(path: Path, text: str) -> None:
    for decision_id in DECISION_IDS:
        match = re.search(
            rf"^## {re.escape(decision_id)}\b(?P<section>.*?)(?=^## |\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if not match:
            fail(f"decision record missing {decision_id}")
        section = match.group("section")
        for marker in ("Decision", "Why", "Reversal path"):
            field = re.search(rf"\*\*{re.escape(marker)}:\*\*\s+(.+)", section)
            if not field or len(field.group(1).strip()) < 30:
                fail(f"{decision_id} missing substantive {marker.lower()}")


def verify_product_owner_approval(path: Path, payload: Dict[str, Any]) -> None:
    if payload.get("task_id") != "ADLC-MIG-002":
        fail("product-owner approval evidence must belong to ADLC-MIG-002")
    approval = payload.get("product_owner_approval")
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        fail("ADLC-MIG-002 needs structured approved product-owner evidence")
    approver = approval.get("approved_by")
    if not isinstance(approver, dict) or not approver.get("identity") or approver.get("role") != "adlc-product-owner":
        fail("product-owner approval needs approver identity and adlc-product-owner role")
    if set(approval.get("approved_surfaces", [])) != APPROVED_SURFACES:
        fail("product-owner approval does not cover every required product surface")
    source = approval.get("source")
    if not isinstance(source, str) or "approved continue the entire process" not in source:
        fail("product-owner approval must preserve the approving user statement")
    approved_at = approval.get("approved_at")
    if not isinstance(approved_at, str):
        fail("product-owner approval needs an approved_at timestamp")
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError:
        fail("product-owner approval approved_at must be an ISO-8601 timestamp")


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: check_product_contract.py PRODUCT.md docs/STYLE.md LEGACY_LEDGER.json", file=sys.stderr)
        return 2
    product_path, style_path, ledger_path = (Path(value).resolve() for value in sys.argv[1:])
    product_text = load_text(product_path)
    style_text = load_text(style_path)
    ledger = load_json(ledger_path)
    decision_path = ROOT / "docs/decisions/skill-loop-product-surface.md"
    decision_text = load_text(decision_path)
    evidence_path = ROOT / "docs/evidence/skill-loop-productization/adlc-run-09d1561af2e2/ADLC-MIG-002.json"
    evidence = load_json(evidence_path)
    verify_product(product_path, product_text)
    verify_style(style_path, style_text)
    verify_ledger(ledger_path, ledger)
    verify_decisions(decision_path, decision_text)
    verify_product_owner_approval(evidence_path, evidence)
    print(
        "product contract: pass "
        f"commands={len(PUBLIC_COMMANDS)} labels={len(SUPPORT_LABELS)} "
        f"surfaces={len(expected_surfaces())} decisions={len(DECISION_IDS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
