#!/usr/bin/env python3
"""Validate the final-form, privacy-preserving, approval-bound beta launch packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ASSETS = {"technical_article", "demo_and_recording_plan", "beta_operations", "metric_contract", "release_notes"}
REQUIRED_ACTIONS = {"pypi_upload", "github_release", "pages_deploy", "launch_communication"}
REQUIRED_FUNNEL = ["readme_visit", "install", "doctor", "first_loop", "returning_project"]
README_FUNNEL_MARKERS = ["README visit", "Install", "Doctor", "First loop", "Returning project"]


def fail(message: str, failures: List[str]) -> None:
    failures.append(message)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    packet_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "docs/launch/launch-packet.json"
    failures: List[str] = []
    try:
        packet: Dict[str, Any] = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"launch packet: fail ({exc})", file=sys.stderr)
        return 1

    if packet.get("contract_version") != "1.0.0" or packet.get("status") != "awaiting_human_approval":
        fail("packet contract/status must remain awaiting_human_approval", failures)
    release = packet.get("release", {})
    if release.get("version") != "0.9.1" or release.get("stage") != "public_beta_candidate":
        fail("release must identify the 0.9.1 public beta candidate", failures)

    assets = packet.get("assets", [])
    if {item.get("kind") for item in assets} != REQUIRED_ASSETS:
        fail("asset set is incomplete", failures)
    for item in assets:
        ref = item.get("ref", "")
        if item.get("status") != "final_form" or not nonempty(ref) or not (ROOT / ref).is_file():
            fail(f"asset is not final-form or resolvable: {item}", failures)

    claims = packet.get("claims", [])
    if len(claims) < 4:
        fail("at least four scoped launch claims are required", failures)
    claim_ids = set()
    for claim in claims:
        claim_id = claim.get("id")
        if not nonempty(claim_id) or claim_id in claim_ids:
            fail(f"claim id missing or duplicated: {claim_id}", failures)
        claim_ids.add(claim_id)
        if not nonempty(claim.get("statement")) or not claim.get("limitations"):
            fail(f"claim lacks statement or limitations: {claim_id}", failures)
        refs = claim.get("evidence_refs", [])
        if not refs or any(not (ROOT / ref).exists() for ref in refs):
            fail(f"claim evidence is missing or unresolved: {claim_id}", failures)

    communications = packet.get("communications", {})
    for key in ("release_announcement", "github_release_draft", "social_draft", "community_draft"):
        if not nonempty(communications.get(key)):
            fail(f"communication draft missing: {key}", failures)
    if communications.get("publication_status") != "pending_human_approval":
        fail("communications must remain pending human approval", failures)

    funnel = packet.get("funnel", [])
    if [item.get("stage") for item in funnel] != REQUIRED_FUNNEL or [item.get("order") for item in funnel] != list(range(1, 6)):
        fail("activation funnel is incomplete or unordered", failures)
    for item in funnel:
        if not all(nonempty(item.get(key)) for key in ("local_event", "success", "source")):
            fail(f"funnel stage lacks a local measurement contract: {item.get('stage')}", failures)

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    funnel_start = readme_text.find("<!-- BEGIN BETA FUNNEL -->")
    funnel_end = readme_text.find("<!-- END BETA FUNNEL -->")
    readme_funnel = readme_text[funnel_start:funnel_end] if 0 <= funnel_start < funnel_end else ""
    positions = [readme_funnel.find(marker) for marker in README_FUNNEL_MARKERS]
    if not readme_funnel or any(position < 0 for position in positions) or positions != sorted(positions):
        fail("README beta funnel is missing or unordered", failures)

    support_matrix = json.loads((ROOT / "docs/evidence/provider-conformance/support-matrix.json").read_text(encoding="utf-8"))
    codex_fix_rows = [
        row
        for row in support_matrix.get("configurations", [])
        if row.get("provider") == "codex" and row.get("loop") == "fix"
    ]
    if len(codex_fix_rows) != 1:
        fail("Codex Fix support evidence must resolve to exactly one configuration", failures)
    else:
        row = codex_fix_rows[0]
        if row.get("label") != "beta" or row.get("run_count") != 3 or row.get("failed_runs") != 0:
            fail("Codex Fix beta claim does not match the support matrix", failures)

    attestation = json.loads(
        (ROOT / "docs/evidence/benchmarks/v0.1.0/publication-attestation.json").read_text(encoding="utf-8")
    )
    if (
        attestation.get("status") != "approved"
        or attestation.get("primary_report", {}).get("attempts") != 3
        or attestation.get("independent_replay", {}).get("attempts") != 3
    ):
        fail("six-run candidate benchmark claim does not match the publication attestation", failures)

    metrics = packet.get("metrics", {})
    if metrics.get("telemetry_default") != "off" or metrics.get("network_endpoint") is not None:
        fail("telemetry must default off with no endpoint", failures)
    if metrics.get("calculation_location") != "operator_local" or "proposal_only" not in str(metrics.get("optional_exporter")):
        fail("metrics must stay local and exporter must remain proposal-only", failures)
    metrics_text = (ROOT / str(metrics.get("ref", "missing"))).read_text(encoding="utf-8") if (ROOT / str(metrics.get("ref", "missing"))).is_file() else ""
    for term in ("Numerator", "Denominator", "Zero denominator", "explicit opt-in", "No exporter or network endpoint"):
        if term not in metrics_text:
            fail(f"metric contract missing: {term}", failures)

    feedback = packet.get("feedback", {})
    if not all(nonempty(feedback.get(key)) for key in ("primary_owner", "security_owner", "release_owner")):
        fail("feedback ownership is incomplete", failures)
    expectations = feedback.get("response_expectations", {})
    if expectations != {"severity_1_ack_hours": 4, "severity_2_ack_business_days": 1, "general_feedback_triage_business_days": 3}:
        fail("feedback response expectations drifted", failures)
    if not (ROOT / str(feedback.get("intake_ref", "missing"))).is_file() or not (ROOT / str(feedback.get("operations_ref", "missing"))).is_file():
        fail("feedback intake or operations reference is missing", failures)

    triggers = packet.get("rollback_triggers", [])
    if len(triggers) < 4 or any(not all(nonempty(item.get(key)) for key in ("id", "condition", "action")) for item in triggers):
        fail("rollback triggers are incomplete", failures)

    reviews = packet.get("reviews", [])
    if {item.get("kind") for item in reviews} != {"product_owner", "security_privacy"}:
        fail("product and security/privacy reviews are not recorded", failures)
    if any(item.get("status") != "pending_human_review" or not nonempty(item.get("owner")) for item in reviews):
        fail("human reviews must remain explicitly pending with owners", failures)

    actions = packet.get("external_actions", [])
    if {item.get("action") for item in actions} != REQUIRED_ACTIONS or any(item.get("status") != "pending_human_approval" for item in actions):
        fail("all four external actions must remain pending human approval", failures)

    for key in ("doc_honesty_section", "no_overclaim"):
        if not nonempty(packet.get(key)):
            fail(f"honesty field missing: {key}", failures)
    if len(packet.get("limitations", [])) < 3:
        fail("packet limitations are incomplete", failures)

    serialized = json.dumps(packet).lower()
    for forbidden in ("telemetry_default\": \"on", "status\": \"approved", "generally_available"):
        if forbidden in serialized:
            fail(f"unsafe launch state found: {forbidden}", failures)

    if failures:
        print("launch packet failures:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"launch packet: pass ({len(claims)} claims, {len(assets)} assets, external actions pending)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
