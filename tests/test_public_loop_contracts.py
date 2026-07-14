import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "docs" / "schemas" / "loop-contract.schema.json").read_text())
CONTRACTS = {
    name: ROOT / "docs" / "loop-library" / f"public-{name}.json"
    for name in ("build", "fix", "review")
}


def load_contract(name):
    return json.loads(CONTRACTS[name].read_text())


def phases(contract):
    return [
        item["after_action"].removeprefix("phase:")
        for item in contract["feedback_channels"]
        if item["after_action"].startswith("phase:")
    ]


def terminal_states(contract):
    values = [contract["job_win_condition"]["done_when"], contract["safe_bail_state"]["state"]]
    values.extend(contract["stop_escalate_rules"]["escalate_when"])
    return {match for value in values for match in value.split() if match.startswith("terminal:")}


def assert_public_semantics(name, contract):
    assert contract["contract_version"] == "1.0.0"
    assert contract["contract_id"] == f"adlc-public-{name}-1"
    assert contract["autonomy_claim"] == "assisted_loop"
    assert phases(contract)
    assert contract["job_win_condition"]["deterministic_checks"]
    assert any(state.startswith("terminal:") for state in terminal_states(contract))
    assert contract["safe_bail_state"]["idempotency"]
    assert contract["control_channel"]["safe_checkpoint_required"] is True
    assert contract["independent_truth"]["type"] != "agent_self_assessment"
    assert "secret" in contract["redaction_posture"].lower()


def test_all_public_loop_contracts_validate_and_expose_runtime_semantics():
    for name in CONTRACTS:
        contract = load_contract(name)
        jsonschema.validate(contract, SCHEMA)
        assert_public_semantics(name, contract)
        command = [
            "bin/adlc",
            "validate-artifact",
            "--schema",
            "loop-contract",
            "--input",
            str(CONTRACTS[name]),
            "--json",
        ]
        import subprocess

        assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode == 0


def test_build_uses_approved_intent_and_reaches_only_honest_terminal_states():
    contract = load_contract("build")
    assert phases(contract)[:3] == ["triage", "plan", "intent_validation"]
    assert "intent_validation" in " ".join(contract["job_win_condition"]["deterministic_checks"])
    assert "terminal:pr_ready" in terminal_states(contract)
    assert "terminal:blocked_human_approval" in terminal_states(contract)


def test_fix_requires_reproduction_and_failing_verifier_before_mutation():
    contract = load_contract("fix")
    assert phases(contract)[0] == "reproduce"
    allowed = [action for tool in contract["allowed_tools"] for action in tool["actions"]]
    assert "mutate_after_reproduction" in allowed
    assert "reproduction_evidence" in contract["job_win_condition"]["deterministic_checks"]
    assert "failing_verifier_expected_reason" in contract["job_win_condition"]["deterministic_checks"]


def test_review_contract_is_read_only():
    contract = load_contract("review")
    actions = [action for tool in contract["allowed_tools"] for action in tool["actions"]]
    forbidden = ("write", "mutate", "publish", "merge", "delete")
    assert not any(token in action for action in actions for token in forbidden)
    assert "terminal:findings_ready" in terminal_states(contract)
    assert "read-only" in contract["safe_bail_state"]["state"]


def test_negative_controls_reject_review_mutation_and_fix_without_reproduction():
    review = load_contract("review")
    review["allowed_tools"][0]["actions"].append("mutate_files")
    with pytest.raises(AssertionError):
        assert_public_review_read_only(review)

    fix = load_contract("fix")
    fix["feedback_channels"] = [
        item for item in fix["feedback_channels"] if item["after_action"] != "phase:reproduce"
    ]
    with pytest.raises(AssertionError):
        assert_public_fix_reproduction_first(fix)


def assert_public_review_read_only(contract):
    actions = [action for tool in contract["allowed_tools"] for action in tool["actions"]]
    assert not any("mutate" in action or "write" in action for action in actions)


def assert_public_fix_reproduction_first(contract):
    assert phases(contract)[0] == "reproduce"
