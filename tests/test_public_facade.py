from __future__ import annotations

import inspect
import sys
from pathlib import Path
from time import monotonic

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import cli  # noqa: E402
from adlc_runtime import public_facade  # noqa: E402


def request(operation: str, *, allow_mutation: bool = False, approved: bool = False, arguments=None, workspace=None, state=None):
    payload = {
        "contract_version": "1.0.0",
        "operation": operation,
        "experimental": True,
        "allow_mutation": allow_mutation,
        "human_approved": approved,
        "arguments": arguments or {},
    }
    if approved:
        payload["approval_ref"] = "human:test"
    if workspace:
        payload["workspace"] = str(workspace)
    if state:
        payload["state"] = str(state)
    return payload


class FakeKernel:
    def __init__(self, deny=False):
        self.calls = []
        self.deny = deny

    def _call(self, name, payload):
        self.calls.append(name)
        return payload

    def health_check_payload(self, include_optional=False):
        return self._call("health_check_payload", {"status": "pass", "checks": []})

    def workflow_status_payload(self, workspace, state):
        return self._call("workflow_status_payload", {"read_only": True, "state": {"status": "planned", "phase": "triage"}})

    def action_admit_payload(self, **kwargs):
        status = "denied" if self.deny else "admitted"
        return (1 if self.deny else 0), self._call("action_admit_payload", {"status": status, "stop_reason": "permission_denied" if self.deny else None})

    def queue_status_payload(self, args):
        return self._call("queue_status_payload", {"status": "pass", "tasks": []})

    def run_phase_payload(self, args):
        return 0, self._call("run_phase_payload", {"state_path": ".adlc/workflow_state.json", "state": {"status": "planned", "phase": args.phase}})

    def completion_audit_payload(self, args):
        return self._call("completion_audit_payload", {"status": "pass", "independence": {"evidence_refs": ["audit:independent"]}})

    def resume_workflow_payload(self, workspace, state, approve, decision, reason):
        return self._call("resume_workflow_payload", {"state_path": ".adlc/workflow_state.json", "state": {"status": "planned", "phase": "code", "side_effects": [{"idempotency_key": "same"}]}})

    def goal_prompt_payload(self, brief, task_id, workspace):
        return self._call("goal_prompt_payload", {"artifact_ref": ".adlc/prompts/task.json", "task_id": task_id})

    def memory_health_payload(self, args):
        return 0, self._call("memory_health_payload", {"status": "pass", "evidence_refs": ["memory:checked"]})


ADMISSION = {
    "tool_registry": "tests/fixtures/control_plane/tool-registry.json",
    "tool": "adlc-tool-node",
    "action": "execute",
    "phase": "code",
    "brief_id": "BRIEF-1",
    "session_id": "SESSION-1",
}
AUDIT = {
    "input": "audit-plan.json",
    "executor": "executor-1",
    "auditor": "auditor-2",
    "independence_evidence": "independence.json",
}


def test_architecture_facade_imports_kernel_without_shelling():
    source = inspect.getsource(public_facade)
    assert "from adlc_runtime import cli as kernel" in source
    assert "subprocess" not in source
    assert "shell=True" not in source
    assert set(public_facade.PUBLIC_OPERATIONS) == {"init", "shape", "build", "fix", "review", "harden", "ship", "status", "resume", "doctor", "learn"}


def test_architecture_status_reaches_no_write_capability(tmp_path):
    state = cli.new_workflow_state("BRIEF-STATUS", tmp_path, phase="triage")
    state_path = tmp_path / ".adlc" / "workflow_state.json"
    cli.save_workflow_state(state_path, state)
    before = state_path.read_bytes()
    result = public_facade.dispatch_public_operation(request("status", workspace=tmp_path, state=str(state_path)))
    assert result["status"] == "completed"
    assert result["result"]["read_only"] is True
    assert state_path.read_bytes() == before


def test_architecture_every_result_validates_and_routes_once():
    cases = {
        "init": request("init"),
        "shape": request("shape", arguments={"build_brief": "brief.json", "task_id": "TASK-1"}),
        "build": request("build", allow_mutation=True, arguments={**ADMISSION, "queue": "queue.json"}),
        "fix": request("fix", allow_mutation=True, arguments=ADMISSION),
        "review": request("review", arguments=AUDIT),
        "harden": request("harden", allow_mutation=True, arguments=ADMISSION),
        "ship": request("ship", approved=True, arguments=AUDIT),
        "status": request("status"),
        "resume": request("resume", allow_mutation=True, arguments=ADMISSION),
        "doctor": request("doctor"),
        "learn": request("learn"),
    }
    for operation, payload in cases.items():
        fake = FakeKernel()
        result = public_facade.dispatch_public_operation(payload, bindings=fake)
        assert not cli.validate_artifact_payload(cli.resolve_schema("public-operation-result"), result), operation
        for call in set(fake.calls):
            assert fake.calls.count(call) == 1, (operation, fake.calls)


def test_denial_is_not_converted_to_success():
    result = public_facade.dispatch_public_operation(
        request("fix", allow_mutation=True, arguments=ADMISSION), bindings=FakeKernel(deny=True)
    )
    assert result["status"] == "blocked"
    assert result["stop_reason"] == "permission_denied"
    assert result["result"]["admission"]["status"] == "denied"


def test_mutation_requires_kernel_admission_inputs():
    result = public_facade.dispatch_public_operation(request("build", allow_mutation=True), bindings=FakeKernel())
    assert result["status"] == "blocked"
    assert result["stop_reason"] == "action_admission_required"


def test_review_rejects_mutation_and_ship_stops_for_approval():
    fake = FakeKernel()
    review = public_facade.dispatch_public_operation(request("review", allow_mutation=True, arguments=AUDIT), bindings=fake)
    ship = public_facade.dispatch_public_operation(request("ship", arguments=AUDIT), bindings=fake)
    assert review["stop_reason"] == "review_is_read_only"
    assert "completion_audit_payload" not in fake.calls
    assert ship["status"] == "awaiting_human"
    assert ship["result"]["external_action_invoked"] is False


def test_resume_preserves_kernel_idempotency_evidence_without_synthesis():
    fake = FakeKernel()
    result = public_facade.dispatch_public_operation(
        request("resume", allow_mutation=True, arguments=ADMISSION), bindings=fake
    )
    assert result["result"]["delegated"]["state"]["side_effects"] == [{"idempotency_key": "same"}]
    assert fake.calls == ["action_admit_payload", "resume_workflow_payload"]


def test_benchmark_dispatch_stays_bounded():
    fake = FakeKernel()
    payload = request("doctor")
    started = monotonic()
    for _ in range(200):
        public_facade.dispatch_public_operation(payload, bindings=fake)
    assert monotonic() - started < 2.0


def test_invalid_request_fails_before_delegation():
    fake = FakeKernel()
    payload = request("doctor")
    payload["experimental"] = False
    with pytest.raises(ValueError, match="request failed schema validation"):
        public_facade.dispatch_public_operation(payload, bindings=fake)
    assert fake.calls == []


@pytest.mark.parametrize("reserved", ["workspace", "state", "allow_mutation", "human_approved", "approval_ref"])
def test_reserved_safety_fields_cannot_be_smuggled_through_arguments(reserved, tmp_path):
    payload = request("doctor", workspace=tmp_path)
    payload["arguments"][reserved] = "/smuggled" if reserved in {"workspace", "state", "approval_ref"} else True
    with pytest.raises(ValueError, match="request failed schema validation"):
        public_facade.dispatch_public_operation(payload)
