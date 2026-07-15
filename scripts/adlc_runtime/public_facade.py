"""Versioned public ADLC operations delegated to the deterministic kernel."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import monotonic
from typing import Any, Dict, Iterable

from adlc_runtime import cli as kernel
from adlc_runtime.metadata import LOW_LEVEL_COMPATIBILITY, PUBLIC_OPERATION_METADATA


CONTRACT_VERSION = "1.0.0"
PUBLIC_OPERATIONS = (
    "init", "shape", "build", "fix", "review", "harden", "ship",
    "status", "resume", "doctor", "learn",
)
MUTATING_OPERATIONS = frozenset({"build", "fix", "harden", "resume"})
KERNEL_ROUTES = {
    "init": ("health_check_payload",),
    "shape": ("goal_prompt_payload",),
    "build": ("action_admit_payload", "queue_status_payload", "run_phase_payload"),
    "fix": ("action_admit_payload", "queue_status_payload", "run_phase_payload"),
    "review": ("completion_audit_payload",),
    "harden": ("action_admit_payload", "run_phase_payload"),
    "ship": ("completion_audit_payload",),
    "status": ("workflow_status_payload",),
    "resume": ("action_admit_payload", "resume_workflow_payload"),
    "doctor": ("health_check_payload",),
    "learn": ("memory_health_payload",),
}


def _schema_errors(alias: str, payload: Dict[str, Any]) -> list[str]:
    return kernel.validate_artifact_payload(kernel.resolve_schema(alias), payload)


def _refs(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_refs" and isinstance(item, list):
                found.extend(str(entry) for entry in item if isinstance(entry, str) and entry)
            elif key in {"artifact_ref", "state_path", "audit_trail_path", "evidence_path"} and isinstance(item, str) and item:
                found.append(item)
            else:
                found.extend(_refs(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_refs(item))
    return list(dict.fromkeys(found))


def _result(
    request: Dict[str, Any],
    status: str,
    stop_reason: str | None,
    payload: Dict[str, Any],
    approvals: Iterable[str] = (),
) -> Dict[str, Any]:
    operation = request["operation"]
    low_level_commands = [
        {"name": name, **LOW_LEVEL_COMPATIBILITY[name]}
        for name in PUBLIC_OPERATION_METADATA[operation]["kernel"]
    ]
    result: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "operation": operation,
        "status": status,
        "stop_reason": stop_reason,
        "evidence_refs": _refs(payload),
        "approval_requirements": list(dict.fromkeys(approvals)),
        "compatibility_warnings": [
            f"Experimental {operation} facade; retained low-level commands are not deprecated: "
            + ", ".join(item["name"] for item in low_level_commands)
        ],
        "compatibility": {
            "support": PUBLIC_OPERATION_METADATA[operation]["support"],
            "public_command": "public-operation",
            "low_level_commands": low_level_commands,
        },
        "kernel": list(KERNEL_ROUTES[operation]),
        "result": payload,
        "no_overclaim": "This result proves deterministic facade delegation only; it does not prove provider execution, installation, publication, or production fitness.",
        "limitations": [
            "Provider adapters and generated skill bundles are validated by downstream migration tasks.",
            "External changes are never published directly by this facade.",
        ],
    }
    if request.get("request_id"):
        result["request_id"] = request["request_id"]
    errors = _schema_errors("public-operation-result", result)
    if errors:
        raise ValueError("public operation result failed schema validation: " + "; ".join(errors))
    return result


def _blocked(request: Dict[str, Any], reason: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return _result(request, "blocked", reason, details or {"reason": reason})


def _namespace(request: Dict[str, Any], **defaults: Any) -> argparse.Namespace:
    values = dict(defaults)
    values.update(request.get("arguments", {}))
    values["workspace"] = request.get("workspace")
    values["state"] = request.get("state")
    values["allow_mutation"] = request["allow_mutation"]
    values["human_approved"] = request["human_approved"]
    values["approval_ref"] = request.get("approval_ref")
    values.setdefault("json", True)
    return argparse.Namespace(**values)


def _admit(request: Dict[str, Any], bindings: Any) -> tuple[bool, Dict[str, Any]]:
    args = request["arguments"]
    required = ("tool_registry", "tool", "action", "phase")
    missing = [name for name in required if not isinstance(args.get(name), str) or not args[name].strip()]
    if missing:
        return False, {"status": "denied", "stop_reason": "action_admission_required", "missing": missing}
    workspace = kernel.resolve_workspace(request.get("workspace"))
    state_path = kernel.resolve_under_workspace(request.get("state"), workspace, kernel.DEFAULT_STATE_PATH) if request.get("state") else None
    exit_code, payload = bindings.action_admit_payload(
        tool_registry_path=kernel.resolve_input_path(args["tool_registry"], workspace),
        tool_name=args["tool"], action=args["action"], phase=args["phase"],
        state_path=state_path, brief_id=args.get("brief_id"), session_id=args.get("session_id"), run_id=args.get("run_id"),
        allow_mutation=request["allow_mutation"], human_approved=request["human_approved"], approval_ref=request.get("approval_ref"),
        audit_trail_path=kernel.resolve_input_path(args["audit_trail"], workspace) if isinstance(args.get("audit_trail"), str) else None,
    )
    return exit_code == 0 and payload.get("status") == "admitted", payload


def _workflow(request: Dict[str, Any], bindings: Any, default_phase: str) -> Dict[str, Any]:
    admitted, admission = _admit(request, bindings)
    if not admitted:
        return _result(request, "blocked", admission.get("stop_reason") or "permission_denied", {"admission": admission})
    args = request["arguments"]
    queue = None
    if isinstance(args.get("queue"), str):
        queue = bindings.queue_status_payload(_namespace(request, queue=args["queue"]))
    phase_args = _namespace(
        request,
        phase=args.get("phase", default_phase), brief_id=args.get("brief_id"), input=args.get("input"), output=args.get("output"),
        build_brief=args.get("build_brief"), verifier=args.get("verifier", []), allow_noop=args.get("allow_noop", False),
        allow_mutation=request["allow_mutation"], tool_registry=args.get("tool_registry"), audit_trail=args.get("audit_trail"),
        human_approved=request["human_approved"], approval_ref=request.get("approval_ref"), max_refs=args.get("max_refs", 8),
        runtime=args.get("runtime"), tools=args.get("tools"), schema=args.get("schema"), label=args.get("label"),
        waive_label=args.get("waive_label"), dry_run=args.get("dry_run", True),
    )
    exit_code, payload = bindings.run_phase_payload(phase_args)
    state = payload.get("state", {})
    state_status = state.get("status")
    status = "failed" if exit_code else {"awaiting_approval": "awaiting_human", "completed": "completed"}.get(state_status, "planned")
    stop = state.get("stop_reason") or ("kernel_failure" if exit_code else ("workflow_checkpoint" if status == "planned" else None))
    approvals = [f"workflow gate: {state.get('phase')}"] if status == "awaiting_human" else []
    return _result(request, status, stop, {"admission": admission, "queue": queue, "delegated": payload}, approvals)


def _completion(request: Dict[str, Any], bindings: Any) -> Dict[str, Any]:
    args = request["arguments"]
    required = ("input", "executor", "auditor", "independence_evidence")
    missing = [name for name in required if not isinstance(args.get(name), str) or not args[name].strip()]
    if missing:
        return _blocked(request, "completion_audit_inputs_required", {"missing": missing})
    payload = bindings.completion_audit_payload(_namespace(request, output=args.get("output")))
    status = "completed" if payload.get("status") == "pass" else "blocked"
    return _result(request, status, None if status == "completed" else "completion_audit_blocked", payload)


def dispatch_public_operation(request: Dict[str, Any], bindings: Any = kernel) -> Dict[str, Any]:
    errors = _schema_errors("public-operation", request)
    if errors:
        raise ValueError("public operation request failed schema validation: " + "; ".join(errors))
    operation = request["operation"]
    args = request["arguments"]
    if operation == "status":
        return _result(request, "completed", None, bindings.workflow_status_payload(request.get("workspace"), request.get("state")))
    if operation == "resume":
        admitted, admission = _admit(request, bindings)
        if not admitted:
            return _result(request, "blocked", admission.get("stop_reason") or "permission_denied", {"admission": admission})
        payload = bindings.resume_workflow_payload(request.get("workspace"), request.get("state"), args.get("approve"), args.get("decision", "approved"), args.get("reason"))
        state = payload.get("state", {})
        status = "awaiting_human" if state.get("status") == "awaiting_approval" else "planned"
        approvals = [f"workflow gate: {state.get('phase')}"] if status == "awaiting_human" else []
        return _result(request, status, state.get("stop_reason") or "workflow_checkpoint", {"admission": admission, "delegated": payload}, approvals)
    if operation in {"build", "fix", "harden"}:
        return _workflow(request, bindings, {"build": "triage", "fix": "triage", "harden": "security"}[operation])
    if operation == "review":
        if request["allow_mutation"]:
            return _blocked(request, "review_is_read_only")
        return _completion(request, bindings)
    if operation == "ship":
        if not request["human_approved"]:
            return _result(request, "awaiting_human", "external_action_approval_required", {"external_action_invoked": False}, ["human approval naming the external action and target"])
        audited = _completion(request, bindings)
        if audited["status"] != "completed":
            return audited
        return _result(request, "planned", "external_action_not_invoked", {"completion_audit": audited["result"], "external_action_invoked": False})
    if operation in {"init", "doctor"}:
        payload = bindings.health_check_payload(bool(args.get("include_optional", False)))
        status = "completed" if payload.get("status") in {"pass", "warn"} else "failed"
        return _result(request, status, None if status == "completed" else "health_check_failed", payload)
    if operation == "shape":
        if not all(isinstance(args.get(key), str) and args[key] for key in ("build_brief", "task_id")):
            return _blocked(request, "shape_inputs_required", {"missing": [key for key in ("build_brief", "task_id") if not args.get(key)]})
        workspace = kernel.resolve_workspace(request.get("workspace"))
        payload = bindings.goal_prompt_payload(kernel.resolve_input_path(args["build_brief"], workspace), args["task_id"], workspace)
        return _result(request, "completed", None, payload)
    if operation == "learn":
        exit_code, payload = bindings.memory_health_payload(_namespace(request, changed_path=args.get("changed_path", []), primitive_proposals=args.get("primitive_proposals"), output=args.get("output")))
        return _result(request, "completed" if exit_code == 0 else "blocked", None if exit_code == 0 else "memory_health_blocked", payload)
    raise AssertionError(f"unhandled public operation: {operation}")


def benchmark_dispatch(request: Dict[str, Any], iterations: int = 100) -> float:
    start = monotonic()
    for _ in range(iterations):
        dispatch_public_operation(request)
    return monotonic() - start
