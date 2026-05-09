#!/usr/bin/env python3
"""ADLC contract CLI.

This is intentionally thin: it exposes the machine-readable ADLC contracts
without becoming a full workflow orchestrator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(os.environ.get("ADLC_ROOT", Path(__file__).resolve().parents[1]))


SCHEMA_ALIASES = {
    "applicability-manifest": "docs/schemas/applicability-manifest.schema.json",
    "build-brief": "docs/schemas/build-brief.schema.json",
    "coder-output": "docs/schemas/coder-output.schema.json",
    "council-verdict": "docs/schemas/council-verdict-output.schema.json",
    "test-author-output": "docs/schemas/test-author-output.schema.json",
    "test-strength-output": "docs/schemas/test-strength-output.schema.json",
    "triage-output": "docs/schemas/triage-output.schema.json",
    "workflow-state": "docs/schemas/workflow-state.schema.json",
}

DEFAULT_STATE_PATH = ".adlc/workflow_state.json"
DEFAULT_SUCCESS_LABELS = ("proceed", "lgtm", "pass", "approve", "fixed")
SUPPORTED_RUNTIMES = ("claude", "codex", "cursor", "antigravity", "factory")
WORK_ITEM_TARGETS = ("github", "jira", "linear")
DEFAULT_PHASE_TOOLS = {
    "triage": "",
    "research": "Read,Bash,Glob,Grep",
    "plan": "Read",
    "plan_review": "Read",
    "gen_tests": "Read,Write,Bash",
    "code": "Read,Write,Edit,Bash,Glob,Grep",
    "code_review": "Read",
    "security": "Read,Bash,Glob,Grep",
    "test_strength": "Read,Bash",
    "fixer": "Read,Write,Edit,Bash,Glob,Grep",
    "pr_prep": "Read,Write,Bash",
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def manifest() -> Dict[str, Any]:
    return read_json(ROOT / "skills/manifest.json")


def list_agents_payload() -> Dict[str, Any]:
    agents = []
    for agent in manifest().get("agents", []):
        agents.append(
            {
                "name": agent["name"],
                "path": agent["path"],
                "dag_node": agent.get("dag_node"),
                "skills": agent.get("skills", []),
                "labels": agent.get("labels", []),
                "runtime_model_map": agent.get("runtime_model_map", {}),
            }
        )

    return {"agents": agents, "count": len(agents)}


def command_list_agents(args: argparse.Namespace) -> int:
    payload = list_agents_payload()
    if args.json:
        write_json(payload)
    else:
        for agent in payload["agents"]:
            skills = ",".join(agent["skills"]) if agent["skills"] else "-"
            print(f"{agent['name']}\t{agent['dag_node']}\t{agent['path']}\t{skills}")
    return 0


def parse_attrs(raw: str) -> Dict[str, str]:
    attrs = {}
    for key, value in re.findall(r'([A-Za-z_][A-Za-z0-9_]*)=("[^"]*"|[^,\]]+)', raw):
        attrs[key] = value.strip().strip('"')
    return attrs


def workflow_nodes_and_edges() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    dot_path = ROOT / "WORKFLOW.dot"
    node_order: List[str] = []
    node_attrs: Dict[str, Dict[str, str]] = {}
    edges: List[Dict[str, Any]] = []

    node_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+\[(.+)\]\s*$")
    edge_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s+\[(.+)\])?")

    for line in dot_path.read_text(encoding="utf-8").splitlines():
        node_match = node_re.match(line)
        if node_match:
            node_id, attrs_raw = node_match.groups()
            if node_id.startswith("l_"):
                continue
            if node_id not in node_attrs:
                node_order.append(node_id)
            node_attrs[node_id] = parse_attrs(attrs_raw)
            continue

        edge_match = edge_re.match(line)
        if edge_match:
            source, target, attrs_raw = edge_match.groups()
            if source.startswith("l_") or target.startswith("l_"):
                continue
            attrs = parse_attrs(attrs_raw or "")
            edges.append(
                {
                    "from": source,
                    "to": target,
                    "label": attrs.get("label"),
                }
            )

    agent_by_node = {agent.get("dag_node"): agent for agent in manifest().get("agents", [])}
    nodes = []
    for node_id in node_order:
        attrs = node_attrs[node_id]
        shape = attrs.get("shape", "")
        style = attrs.get("style", "")
        if node_id in agent_by_node:
            node_type = "agent"
        elif shape == "component":
            node_type = "fan_out"
        elif shape == "hexagon":
            node_type = "human_gate"
        elif shape == "diamond":
            node_type = "conditional"
        elif shape in {"Mdiamond", "Msquare"}:
            node_type = "terminal"
        elif "dashed" in style:
            node_type = "tool"
        else:
            node_type = "workflow"

        nodes.append(
            {
                "id": node_id,
                "label": attrs.get("label", node_id).replace("\\n", " / "),
                "type": node_type,
                "agent": agent_by_node.get(node_id, {}).get("name"),
            }
        )

    return nodes, edges


def list_phases_payload() -> Dict[str, Any]:
    nodes, edges = workflow_nodes_and_edges()
    return {"nodes": nodes, "edges": edges, "count": len(nodes)}


def command_list_phases(args: argparse.Namespace) -> int:
    payload = list_phases_payload()
    if args.json:
        write_json(payload)
    else:
        for node in payload["nodes"]:
            agent = node["agent"] or "-"
            print(f"{node['id']}\t{node['type']}\t{agent}\t{node['label']}")
    return 0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_workspace(workspace_arg: str | None) -> Path:
    return Path(workspace_arg or Path.cwd()).resolve()


def resolve_under_workspace(path_arg: str | None, workspace: Path, default: str) -> Path:
    path = Path(path_arg or default)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def resolve_input_path(path_arg: str, workspace: Path) -> Path:
    path = Path(path_arg)
    if path.is_absolute():
        return path.resolve()
    cwd_path = (Path.cwd() / path).resolve()
    if cwd_path.exists():
        return cwd_path
    return (workspace / path).resolve()


def workflow_maps() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    nodes, edges = workflow_nodes_and_edges()
    node_by_id = {node["id"]: node for node in nodes}
    outgoing: Dict[str, List[Dict[str, Any]]] = {node["id"]: [] for node in nodes}
    for edge in edges:
        outgoing.setdefault(edge["from"], []).append(edge)
    return node_by_id, outgoing


def next_phase(current_phase: str, label: str | None = None) -> str | None:
    _, outgoing = workflow_maps()
    candidates = outgoing.get(current_phase, [])
    if not candidates:
        return None
    if label is not None:
        for edge in candidates:
            if edge.get("label") == label:
                return edge["to"]
        raise ValueError(f"no transition from {current_phase} with label {label}")
    if len(candidates) == 1:
        return candidates[0]["to"]
    for default_label in DEFAULT_SUCCESS_LABELS:
        for edge in candidates:
            if edge.get("label") == default_label:
                return edge["to"]
    return None


def infer_brief_id(input_arg: str | None) -> str | None:
    if not input_arg:
        return None
    input_path = Path(input_arg)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    if not input_path.is_file():
        return None
    try:
        payload = read_json(input_path)
    except Exception:
        return None
    brief_id = payload.get("brief_id") if isinstance(payload, dict) else None
    return brief_id if isinstance(brief_id, str) and brief_id else None


def new_workflow_state(
    brief_id: str,
    workspace: Path,
    phase: str = "start",
    input_path: str | None = None,
) -> Dict[str, Any]:
    now = utc_now()
    checkpoint: Dict[str, Any] = {
        "workspace": str(workspace),
        "history": [],
    }
    if input_path:
        checkpoint["input"] = input_path
    return {
        "brief_id": brief_id,
        "session_id": f"adlc-{uuid.uuid4().hex[:12]}",
        "phase": phase,
        "step": "ready",
        "status": "planned",
        "started_at": now,
        "updated_at": now,
        "checkpoint": checkpoint,
        "side_effects": [],
        "resume_count": 0,
    }


def load_workflow_state(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"workflow state not found: {path}")
    state = read_json(path)
    if not isinstance(state, dict):
        raise ValueError(f"workflow state must be a JSON object: {path}")
    return state


def save_workflow_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("workflow-state"), path)
    if errors:
        raise ValueError("workflow state failed schema validation: " + "; ".join(errors))


def workflow_state_for_args(args: argparse.Namespace, workspace: Path) -> Tuple[Path, Dict[str, Any]]:
    state_path = resolve_under_workspace(getattr(args, "state", None), workspace, DEFAULT_STATE_PATH)
    if state_path.exists():
        return state_path, load_workflow_state(state_path)

    brief_id = getattr(args, "brief_id", None) or infer_brief_id(getattr(args, "input", None))
    if not brief_id:
        raise ValueError("--brief-id is required when creating a new workflow state")
    state = new_workflow_state(
        brief_id=brief_id,
        workspace=workspace,
        phase=getattr(args, "phase", None) or "start",
        input_path=getattr(args, "input", None),
    )
    return state_path, state


def append_history(state: Dict[str, Any], event: Dict[str, Any]) -> None:
    checkpoint = state.setdefault("checkpoint", {})
    checkpoint.setdefault("history", []).append({"timestamp": utc_now(), **event})


def phase_invocation_plan(
    phase: str,
    workspace: Path,
    input_arg: str | None,
    output_arg: str | None,
    runtime: str,
    tools_csv: str | None,
    schema_arg: str | None,
) -> Dict[str, Any]:
    node_by_id, _ = workflow_maps()
    if phase not in node_by_id:
        raise ValueError(f"unknown workflow phase: {phase}")
    node = node_by_id[phase]
    agent_path = None
    if node.get("agent"):
        agent = next(
            (candidate for candidate in manifest().get("agents", []) if candidate.get("dag_node") == phase),
            None,
        )
        if not agent:
            raise ValueError(f"phase {phase} is marked agent-backed but no manifest agent exists")
        agent_path = agent["path"]

    input_path = resolve_input_path(input_arg, workspace) if input_arg else None
    output_path = resolve_under_workspace(output_arg, workspace, f".adlc/outputs/{phase}.json")
    schema_path = resolve_schema(schema_arg) if schema_arg else None
    return {
        "phase": phase,
        "node_type": node["type"],
        "agent": node.get("agent"),
        "agent_path": agent_path,
        "runtime": runtime,
        "adapter_path": f"tests/smoke/adapters/{runtime}.sh",
        "input": str(input_path) if input_path else None,
        "output": str(output_path),
        "tools": tools_csv if tools_csv is not None else DEFAULT_PHASE_TOOLS.get(phase, ""),
        "schema": str(schema_path) if schema_path else None,
    }


def read_output_label(output_path: str | None) -> str | None:
    if not output_path:
        return None
    path = Path(output_path)
    if not path.is_file():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    label = payload.get("label") if isinstance(payload, dict) else None
    return label if isinstance(label, str) and label else None


def invoke_agent_phase(plan: Dict[str, Any], workspace: Path) -> subprocess.CompletedProcess[str]:
    if not plan["agent_path"]:
        raise ValueError(f"phase {plan['phase']} is not agent-backed")
    if not plan["input"]:
        raise ValueError(f"phase {plan['phase']} requires --input for runtime execution")
    output_path = Path(plan["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(ROOT / plan["adapter_path"]),
        "invoke_agent",
        "--agent",
        str(ROOT / plan["agent_path"]),
        "--input",
        plan["input"],
        "--output",
        plan["output"],
        "--tools",
        plan["tools"],
    ]
    if plan.get("schema"):
        command.extend(["--schema", plan["schema"]])
    return subprocess.run(command, cwd=str(workspace), text=True, capture_output=True, check=False)


def apply_phase_result(
    state: Dict[str, Any],
    phase: str,
    status: str,
    label: str | None,
    plan: Dict[str, Any],
    dry_run: bool,
    returncode: int = 0,
    stderr: str = "",
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "phase": phase,
        "status": status,
        "label": label,
        "dry_run": dry_run,
        "returncode": returncode,
        "invocation": plan,
    }
    if stderr:
        event["stderr"] = stderr[-2000:]

    if status != "completed":
        state["phase"] = phase
        state["status"] = "failed"
        state["step"] = "failed"
        state["updated_at"] = utc_now()
        state["stop_reason"] = "phase_execution_failed"
        append_history(state, event)
        return state

    destination = next_phase(phase, label)
    event["next_phase"] = destination
    append_history(state, event)
    state["updated_at"] = utc_now()

    if destination is None:
        state["phase"] = phase
        state["status"] = "completed"
        state["step"] = "done"
        state.pop("stop_reason", None)
        return state

    node_by_id, _ = workflow_maps()
    destination_node = node_by_id.get(destination, {})
    state["phase"] = destination
    state["step"] = "ready"
    if destination_node.get("type") == "human_gate":
        state["status"] = "awaiting_approval"
        state["stop_reason"] = "human_gate"
    elif destination in {"done", "escalate"}:
        state["status"] = "completed"
        state["stop_reason"] = destination
    else:
        state["status"] = "planned"
        state.pop("stop_reason", None)
    return state


def run_phase_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    state_path, state = workflow_state_for_args(args, workspace)
    phase = args.phase or state["phase"]
    runtime = args.runtime or os.environ.get("ADLC_RUNTIME", "claude")
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime}")

    plan = phase_invocation_plan(
        phase=phase,
        workspace=workspace,
        input_arg=args.input or state.get("checkpoint", {}).get("input"),
        output_arg=args.output,
        runtime=runtime,
        tools_csv=args.tools,
        schema_arg=args.schema,
    )

    node_by_id, _ = workflow_maps()
    node_type = node_by_id[phase]["type"]
    if phase in {"done", "escalate"}:
        state["status"] = "completed"
        state["updated_at"] = utc_now()
        save_workflow_state(state_path, state)
        return 0, {"state_path": rel_path(state_path), "state": state, "result": "terminal"}

    if node_type == "human_gate":
        state["status"] = "awaiting_approval"
        state["stop_reason"] = "human_gate"
        state["updated_at"] = utc_now()
        append_history(state, {"phase": phase, "status": "awaiting_approval", "dry_run": args.dry_run})
        save_workflow_state(state_path, state)
        return 0, {"state_path": rel_path(state_path), "state": state, "result": "awaiting_approval"}

    if args.dry_run or phase == "start" or node_type in {"tool", "fan_out", "workflow", "conditional"}:
        label = args.label
        state = apply_phase_result(
            state=state,
            phase=phase,
            status="completed",
            label=label,
            plan=plan,
            dry_run=True,
        )
        save_workflow_state(state_path, state)
        return 0, {"state_path": rel_path(state_path), "state": state, "plan": plan, "dry_run": True}

    result = invoke_agent_phase(plan, workspace)
    label = args.label or read_output_label(plan["output"])
    state = apply_phase_result(
        state=state,
        phase=phase,
        status="completed" if result.returncode == 0 else "failed",
        label=label,
        plan=plan,
        dry_run=False,
        returncode=result.returncode,
        stderr=result.stderr,
    )
    save_workflow_state(state_path, state)
    payload = {
        "state_path": rel_path(state_path),
        "state": state,
        "plan": plan,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    return result.returncode, payload


def command_run_phase(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = run_phase_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['state']['brief_id']}: {payload['state']['phase']} ({payload['state']['status']})")
    return exit_code


def command_run(args: argparse.Namespace) -> int:
    try:
        payloads = []
        exit_code = 0
        for _ in range(args.max_phases):
            exit_code, payload = run_phase_payload(args)
            payloads.append(payload)
            state = payload["state"]
            if exit_code != 0 or state["status"] in {"failed", "awaiting_approval", "completed"}:
                break
            args.phase = None
        final_payload = {"runs": payloads, "state": payloads[-1]["state"] if payloads else None}
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(final_payload)
    else:
        state = final_payload["state"]
        print(f"{state['brief_id']}: {state['phase']} ({state['status']})")
    return exit_code


def command_resume_workflow(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    state_path = resolve_under_workspace(args.state, workspace, DEFAULT_STATE_PATH)
    try:
        state = load_workflow_state(state_path)
        state["resume_count"] = int(state.get("resume_count", 0)) + 1
        state["updated_at"] = utc_now()
        node_by_id, _ = workflow_maps()
        next_action = {
            "phase": state["phase"],
            "status": state["status"],
            "node": node_by_id.get(state["phase"]),
            "runnable": state["status"] == "planned" and state["phase"] not in {"done", "escalate"},
        }
        state.setdefault("checkpoint", {})["next_action"] = next_action
        save_workflow_state(state_path, state)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = {"state_path": rel_path(state_path), "state": state, "next_action": next_action}
    if args.json:
        write_json(payload)
    else:
        print(f"{state['brief_id']}: resume {state['phase']} ({state['status']})")
    return 0


def resolve_schema(schema_arg: str) -> Path:
    schema_path = SCHEMA_ALIASES.get(schema_arg, schema_arg)
    path = Path(schema_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def schema_store() -> Dict[str, Any]:
    store: Dict[str, Any] = {}
    for path in (ROOT / "docs/schemas").glob("*.schema.json"):
        schema = read_json(path)
        store[path.as_uri()] = schema
        store[str(path)] = schema
        store[path.name] = schema
        if "$id" in schema:
            store[schema["$id"]] = schema
    return store


def validate_artifact(schema_path: Path, input_path: Path) -> List[str]:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from jsonschema import Draft7Validator, RefResolver
    except ImportError as exc:
        raise RuntimeError(
            "jsonschema is required for schema validation. Install with: pip3 install jsonschema"
        ) from exc

    schema = read_json(schema_path)
    artifact = read_json(input_path)
    store = schema_store()
    store[schema_path.as_uri()] = schema
    resolver = RefResolver.from_schema(schema, store=store)
    validator = Draft7Validator(schema, resolver=resolver)
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(artifact), key=lambda item: list(item.path))
    ]


def command_validate_artifact(args: argparse.Namespace) -> int:
    schema_path = resolve_schema(args.schema)
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    if not schema_path.is_file():
        print(f"schema not found: {schema_path}", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"input not found: {input_path}", file=sys.stderr)
        return 2

    try:
        errors = validate_artifact(schema_path, input_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = {
        "valid": len(errors) == 0,
        "schema": rel_path(schema_path),
        "input": rel_path(input_path),
        "errors": errors,
    }
    if args.json:
        write_json(payload)
    elif payload["valid"]:
        print(f"valid: {payload['input']} against {payload['schema']}")
    else:
        print(f"invalid: {payload['input']} against {payload['schema']}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    return 0 if payload["valid"] else 1


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def load_phase_project_map(value: str | None) -> Dict[str, str] | None:
    if not value:
        return None
    candidate = Path(value)
    raw = candidate.read_text(encoding="utf-8") if candidate.exists() else value
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("--phase-project-map must be a JSON object or a path to one")
    phase_project_map: Dict[str, str] = {}
    for key, project in parsed.items():
        if not isinstance(key, str) or not isinstance(project, str) or not key.strip() or not project.strip():
            raise ValueError("--phase-project-map entries must be non-empty string pairs")
        phase_project_map[key.strip()] = project.strip()
    return phase_project_map


def build_brief_feature_name(brief: Dict[str, Any]) -> str:
    sections = brief.get("sections", {})
    for key in ("0_goal", "1_context", "feature_name"):
        value = sections.get(key) if isinstance(sections, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0][:120]
    return brief.get("prd_id") or brief.get("brief_id") or "ADLC Build Brief"


def task_blocks_implementation(task: Dict[str, Any]) -> bool:
    decision = task.get("decision_contract", {})
    return bool(decision.get("blocks_implementation")) or task.get("artifact_type") == "decision_gate"


def task_executable(task: Dict[str, Any]) -> bool:
    return task.get("artifact_type") in {"implementation_task", "validation_task"}


def terminal_side_effect_dependency_ids(state: Dict[str, Any] | None, target: str, brief_id: str) -> set:
    if not state:
        return set()
    dependency_ids = set()
    expected_tool = f"{target}-work-item-emitter"
    expected_key_prefix = f"{brief_id}:{target}:"
    for item in state.get("side_effects", []):
        if item.get("status") not in {"completed", "deduplicated"}:
            continue
        if item.get("tool_name") != expected_tool or item.get("operation") != "upsert_artifact":
            continue
        idempotency_key = item.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key.startswith(expected_key_prefix):
            continue
        for key in ("artifact_id", "artifact_ref"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                dependency_ids.add(value.strip())
    return dependency_ids


def compute_readiness_report(
    brief: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    phase_project_map: Dict[str, str] | None,
    external_dependency_ids: set | None = None,
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    task_ids = {t["task_id"] for t in tasks}
    resolvable_dependency_ids = task_ids | (external_dependency_ids or set())
    validation_task_ids = {t["task_id"] for t in tasks if t.get("artifact_type") == "validation_task"}
    erc = brief.get("enterprise_readiness_contract", {})
    erc_validation_tasks = erc.get("validation_tasks", [])

    for task in tasks:
        for dep in task.get("dependencies", []):
            if dep not in resolvable_dependency_ids:
                issues.append({
                    "severity": "blocking",
                    "rule": "unresolved_dependency_alias",
                    "task_id": task["task_id"],
                    "message": f"dependency {dep} does not resolve to a task_id or emitted target artifact",
                })

    for vt_id in erc_validation_tasks:
        if vt_id not in validation_task_ids:
            issues.append({
                "severity": "blocking",
                "rule": "validation_task_resolution",
                "task_id": "<enterprise_readiness_contract>",
                "message": f"validation_tasks entry {vt_id} does not resolve to a validation_task artifact",
            })

    for task in tasks:
        if task.get("artifact_type") == "decision_gate":
            dc = task.get("decision_contract", {})
            if not dc.get("blocks_implementation"):
                issues.append({
                    "severity": "blocking",
                    "rule": "decision_gate_blocks_implementation",
                    "task_id": task["task_id"],
                    "message": "decision_gate must have blocks_implementation=true",
                })
            if dc.get("status") != "unresolved":
                issues.append({
                    "severity": "blocking",
                    "rule": "decision_gate_unresolved",
                    "task_id": task["task_id"],
                    "message": "decision_gate must have decision_contract.status=unresolved",
                })
            if not dc.get("type1_decision"):
                issues.append({
                    "severity": "blocking",
                    "rule": "decision_gate_type1",
                    "task_id": task["task_id"],
                    "message": "decision_gate must have decision_contract.type1_decision=true",
                })

    for task in tasks:
        atype = task.get("artifact_type")
        if atype == "implementation_task":
            dc = task.get("decision_contract", {})
            if dc.get("blocks_implementation"):
                issues.append({
                    "severity": "blocking",
                    "rule": "implementation_task_blocks",
                    "task_id": task["task_id"],
                    "message": "implementation_task must not block implementation",
                })
            if dc.get("status") not in ("resolved", "not_applicable"):
                issues.append({
                    "severity": "blocking",
                    "rule": "implementation_task_decision_status",
                    "task_id": task["task_id"],
                    "message": "implementation_task must have decision_contract.status in [resolved, not_applicable]",
                })

    for task in tasks:
        atype = task.get("artifact_type")
        if atype in ("implementation_task", "validation_task"):
            checks = [
                ("verification_spec.primary_verifier.target", task.get("verification_spec", {}).get("primary_verifier", {}).get("target")),
                ("acceptance_criteria", task.get("acceptance_criteria")),
                ("evidence_responsibilities", task.get("evidence_responsibilities")),
                ("definition_of_done", task.get("definition_of_done")),
                ("compatibility_contract", task.get("compatibility_contract")),
                ("tech_debt_boundaries", task.get("tech_debt_boundaries")),
                ("failure_modes", task.get("failure_modes")),
            ]
            for field_name, value in checks:
                missing = False
                if value is None:
                    missing = True
                elif isinstance(value, list) and len(value) == 0:
                    missing = True
                elif isinstance(value, dict):
                    if field_name == "compatibility_contract":
                        for sub in ("backward", "forward", "migration_or_rollout"):
                            if not isinstance(value.get(sub), str) or not value.get(sub):
                                missing = True
                                break
                    elif field_name == "tech_debt_boundaries":
                        for sub in ("prerequisite_debt", "deferred_debt", "deferral_safety"):
                            if not isinstance(value.get(sub), str) or not value.get(sub):
                                missing = True
                                break
                elif isinstance(value, str) and not value.strip():
                    missing = True
                if missing:
                    issues.append({
                        "severity": "blocking",
                        "rule": "missing_required_field",
                        "task_id": task["task_id"],
                        "message": f"{field_name} is empty or missing",
                    })

    if phase_project_map:
        for task in tasks:
            meta = task.get("work_item_metadata", {})
            phase_label = meta.get("phase_label")
            if phase_label and phase_label in phase_project_map:
                expected_project = phase_project_map[phase_label]
                target_project = meta.get("target_project")
                if not target_project:
                    issues.append({
                        "severity": "blocking",
                        "rule": "phase_project_map_missing_target_project",
                        "task_id": task["task_id"],
                        "message": f"phase_label '{phase_label}' expects target_project '{expected_project}' but target_project is missing",
                    })
                elif target_project != expected_project:
                    issues.append({
                        "severity": "blocking",
                        "rule": "phase_project_map_mismatch",
                        "task_id": task["task_id"],
                        "message": f"phase_label '{phase_label}' expects target_project '{expected_project}' but found '{target_project}'",
                    })

    deduped: List[Dict[str, Any]] = []
    seen: set = set()
    for issue in issues:
        key = (issue["rule"], issue.get("task_id", ""), issue["message"])
        if key not in seen:
            seen.add(key)
            deduped.append(issue)

    blocked_task_ids = {issue["task_id"] for issue in deduped if issue.get("task_id") in task_ids}
    blocked_count = len(blocked_task_ids)
    status = "blocked" if deduped else "ready"

    return {
        "status": status,
        "issues": deduped,
        "totals": {
            "tasks": len(tasks),
            "ready": len(tasks) - blocked_count if blocked_count else len(tasks),
            "blocked": blocked_count,
            "issues": len(deduped),
        },
    }


def normalized_work_item_payload(brief_path: Path, target: str, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    errors = validate_artifact(resolve_schema("build-brief"), brief_path)
    if errors:
        raise ValueError("build brief failed schema validation: " + "; ".join(errors))

    brief = read_json(brief_path)
    brief_id = brief["brief_id"]
    tasks = brief.get("sections", {}).get("8_task_tickets", [])
    terminal_keys = {
        item.get("idempotency_key")
        for item in (state or {}).get("side_effects", [])
        if item.get("status") in {"completed", "deduplicated"}
    }

    artifacts = []
    for index, task in enumerate(tasks, start=1):
        task_id = task["task_id"]
        meta = task.get("work_item_metadata", {})
        idempotency_key = f"{brief_id}:{target}:{task_id}:upsert"
        artifact = {
            "id": task_id,
            "title": task.get("title", task_id),
            "url": f"dry-run://{target}/{brief_id}/{task_id}",
            "artifact_type": task["artifact_type"],
            "task_classification": task.get("task_classification"),
            "executable": task_executable(task),
            "blocks_implementation": task_blocks_implementation(task),
            "area": meta.get("area") or meta.get("area_label") or "unknown",
            "phase": index,
            "phase_label": meta.get("phase_label"),
            "target_project": meta.get("target_project"),
            "labels": meta.get("labels", []),
            "external_refs": meta.get("external_refs", []),
            "linked_failure_modes": task.get("failure_modes", []),
            "idempotency_key": idempotency_key,
            "emission_status": "deduplicated" if idempotency_key in terminal_keys else "pending",
            "decision_contract": task.get("decision_contract"),
            "verification_spec": task.get("verification_spec"),
            "dependencies": task.get("dependencies", []),
            "acceptance_criteria": task.get("acceptance_criteria", []),
            "reference_impl": task.get("reference_impl"),
            "files_to_create": task.get("files_to_create", []),
            "files_to_modify": task.get("files_to_modify", []),
            "tech_debt_boundaries": task.get("tech_debt_boundaries"),
            "compatibility_contract": task.get("compatibility_contract"),
            "evidence_responsibilities": task.get("evidence_responsibilities", []),
            "definition_of_done": task.get("definition_of_done", []),
            "failure_modes": task.get("failure_modes", []),
        }
        artifacts.append(artifact)

    dependency_links = []
    task_ids = {task["task_id"] for task in tasks}
    resolvable_dependency_ids = task_ids | terminal_side_effect_dependency_ids(state, target, brief_id)
    for task in tasks:
        for dependency in task.get("dependencies", []):
            if dependency not in resolvable_dependency_ids:
                raise ValueError(f"unresolved_dependency_alias: {task['task_id']} depends on {dependency}")
            dependency_links.append({"from": dependency, "to": task["task_id"], "type": "blocks"})

    return {
        "contract_version": "1.0.0",
        "target": target,
        "build_brief_id": brief_id,
        "feature_name": build_brief_feature_name(brief),
        "parent_artifact": {
            "id": f"{brief_id}:{target}:parent:{stable_hash(brief_id + target)}",
            "title": build_brief_feature_name(brief),
            "url": f"dry-run://{target}/{brief_id}",
        },
        "artifacts": artifacts,
        "dependency_links": dependency_links,
        "enterprise_readiness_contract": brief.get("enterprise_readiness_contract"),
        "applicability_manifest": brief.get("applicability_manifest"),
        "summary": f"{len(artifacts)} ADLC work items prepared for {target}.",
    }


def append_permission_log(workspace: Path, entry: Dict[str, Any]) -> None:
    log_path = workspace / ".adlc" / "permission_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def first_nonempty_text(item: Dict[str, Any] | None, keys: Iterable[str]) -> str | None:
    if not item:
        return None
    for key in keys:
        value = item.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    return None


def provider_results_by_idempotency_key(provider_result: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    if not provider_result:
        return {}
    candidates: List[Dict[str, Any]] = []
    if isinstance(provider_result.get("idempotency_key"), str):
        candidates.append(provider_result)
    for key in ("artifacts", "issues", "tickets", "items", "results"):
        value = provider_result.get(key)
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))

    mapped: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        idempotency_key = item.get("idempotency_key")
        if isinstance(idempotency_key, str) and idempotency_key.strip():
            mapped[idempotency_key.strip()] = item
    return mapped


def normalized_side_effect_status(value: Any, default: str) -> str:
    if value in {"attempted", "deduplicated", "completed", "failed"}:
        return value
    return default


def provider_result_has_failed_items(provider_result: Dict[str, Any] | None) -> bool:
    return any(
        item.get("status") == "failed"
        for item in provider_results_by_idempotency_key(provider_result).values()
    )


def record_emitter_side_effects(
    state: Dict[str, Any],
    target: str,
    payload: Dict[str, Any],
    status: str,
    provider_result: Dict[str, Any] | None = None,
) -> None:
    provider_by_key = provider_results_by_idempotency_key(provider_result)
    existing_terminal = {
        item.get("idempotency_key")
        for item in state.get("side_effects", [])
        if item.get("status") in {"completed", "deduplicated"}
    }
    for artifact in payload.get("artifacts", []):
        idempotency_key = artifact["idempotency_key"]
        provider_item = provider_by_key.get(idempotency_key)
        if idempotency_key in existing_terminal:
            side_effect_status = "deduplicated"
        else:
            side_effect_status = normalized_side_effect_status(
                provider_item.get("status") if provider_item else None,
                status,
            )
        artifact_id = first_nonempty_text(
            provider_item,
            ("artifact_id", "key", "identifier", "number", "id"),
        ) or artifact["id"]
        artifact_ref = first_nonempty_text(
            provider_item,
            ("artifact_ref", "url", "html_url", "web_url"),
        ) or artifact["url"]
        state.setdefault("side_effects", []).append(
            {
                "idempotency_key": idempotency_key,
                "tool_name": f"{target}-work-item-emitter",
                "operation": "upsert_artifact",
                "status": side_effect_status,
                "artifact_id": artifact_id,
                "artifact_ref": artifact_ref,
                "timestamp": utc_now(),
                **({"error": provider_result.get("error")} if provider_result and provider_result.get("error") else {}),
            }
        )


def invoke_provider_command(provider_command: str, payload: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    command = shlex.split(provider_command)
    if not command:
        raise ValueError("provider command is empty")
    result = subprocess.run(
        command,
        cwd=str(workspace),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {"status": "failed", "returncode": result.returncode, "error": result.stderr[-2000:]}
    if not result.stdout.strip():
        return {"status": "completed"}
    try:
        provider_payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "completed", "raw_stdout": result.stdout}
    if isinstance(provider_payload, dict):
        provider_payload.setdefault("status", "completed")
        return provider_payload
    return {"status": "completed", "result": provider_payload}


def emit_work_items_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.target not in WORK_ITEM_TARGETS:
        raise ValueError(f"unsupported work-item target: {args.target}")
    workspace = resolve_workspace(args.workspace)
    brief_path = Path(args.build_brief)
    if not brief_path.is_absolute():
        brief_path = Path.cwd() / brief_path
    state_path = resolve_under_workspace(args.state, workspace, DEFAULT_STATE_PATH)
    state = load_workflow_state(state_path) if state_path.exists() else None

    phase_project_map = load_phase_project_map(getattr(args, "phase_project_map", None))

    errors = validate_artifact(resolve_schema("build-brief"), brief_path.resolve())
    if errors:
        raise ValueError("build brief failed schema validation: " + "; ".join(errors))
    brief = read_json(brief_path.resolve())
    tasks = brief.get("sections", {}).get("8_task_tickets", [])
    readiness_report = compute_readiness_report(
        brief,
        tasks,
        phase_project_map,
        terminal_side_effect_dependency_ids(state, args.target, brief["brief_id"]),
    )

    require_ready = getattr(args, "require_ready", False)
    bypass_readiness = getattr(args, "bypass_readiness_check", False)

    if require_ready and readiness_report["status"] == "blocked":
        raise ValueError(f"readiness check failed: {readiness_report['totals']['issues']} blocking issue(s)")

    payload = normalized_work_item_payload(brief_path.resolve(), args.target, state)
    payload["readiness_report"] = readiness_report
    dry_run = args.dry_run or not args.allow_mutation

    if not dry_run and readiness_report["status"] == "blocked" and not bypass_readiness:
        raise ValueError(
            f"readiness check blocked: {readiness_report['totals']['issues']} blocking issue(s). "
            "Use --bypass-readiness-check to force."
        )

    result: Dict[str, Any] = {
        "dry_run": dry_run,
        "state_path": rel_path(state_path),
        **payload,
    }
    if dry_run:
        return 0, result

    if not args.provider_command:
        raise ValueError("--provider-command is required with --allow-mutation")
    if state is None:
        brief_id = payload["build_brief_id"]
        state = new_workflow_state(brief_id=brief_id, workspace=workspace, phase="pr_prep")

    append_permission_log(
        workspace,
        {
            "tool": f"{args.target}-work-item-emitter",
            "provider": args.provider_command,
            "action": "upsert_artifacts",
            "tier": "requires_approval",
            "decision": "approved",
            "decided_by": "cli --allow-mutation",
            "timestamp": utc_now(),
            "rationale": "ADLC emit-work-items mutation requested explicitly.",
        },
    )
    provider_result = invoke_provider_command(args.provider_command, payload, workspace)
    provider_failed = provider_result.get("status") == "failed"
    partial_failure = not provider_failed and provider_result_has_failed_items(provider_result)
    default_side_effect_status = "failed" if provider_failed else "completed"
    record_emitter_side_effects(state, args.target, payload, default_side_effect_status, provider_result)
    if partial_failure:
        provider_result["status"] = "failed"
        provider_result["stop_reason"] = "external_mutation_partial"
    elif provider_failed and provider_result_has_failed_items(provider_result):
        provider_result.setdefault("stop_reason", "external_mutation_partial")
    state["updated_at"] = utc_now()
    state.setdefault("checkpoint", {})["last_emitter_result"] = provider_result
    save_workflow_state(state_path, state)
    result["provider_result"] = provider_result
    result["state"] = state
    return (1 if provider_failed or partial_failure else 0), result


def command_emit_work_items(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = emit_work_items_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        mode = "dry-run" if payload["dry_run"] else "mutated"
        print(f"{payload['build_brief_id']}: {len(payload['artifacts'])} {payload['target']} work items ({mode})")
    return exit_code


def mcp_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "adlc_list_agents",
            "description": "List ADLC agents from skills/manifest.json.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "json": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": "adlc_list_phases",
            "description": "List ADLC workflow nodes and edges from WORKFLOW.dot.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "json": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": "adlc_validate_artifact",
            "description": "Validate an ADLC artifact JSON file against a known schema alias or schema path.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["schema", "input"],
                "properties": {
                    "schema": {
                        "type": "string",
                        "enum": sorted(SCHEMA_ALIASES.keys()),
                    },
                    "input": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": "adlc_run_phase",
            "description": "Run or dry-run one ADLC workflow phase and persist workflow state.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "phase": {"type": "string", "minLength": 1},
                    "brief_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "input": {"type": "string", "minLength": 1},
                    "output": {"type": "string", "minLength": 1},
                    "runtime": {"type": "string", "enum": list(SUPPORTED_RUNTIMES)},
                    "tools": {"type": "string"},
                    "schema": {"type": "string"},
                    "label": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": "adlc_resume_workflow",
            "description": "Load ADLC workflow state, increment resume_count, and return the next runnable action.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": "adlc_emit_work_items",
            "description": "Create a normalized ADLC work-item emitter payload, with explicit opt-in local provider mutation.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["target", "build_brief"],
                "properties": {
                    "target": {"type": "string", "enum": list(WORK_ITEM_TARGETS)},
                    "build_brief": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "provider_command": {"type": "string"},
                    "require_ready": {"type": "boolean", "default": False},
                    "phase_project_map": {"type": "string"},
                    "bypass_readiness_check": {"type": "boolean", "default": False},
                },
            },
        },
    ]


def tool_result(payload: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, sort_keys=True),
            }
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "adlc_list_agents":
        return tool_result(list_agents_payload())
    if name == "adlc_list_phases":
        return tool_result(list_phases_payload())
    if name == "adlc_validate_artifact":
        schema = arguments.get("schema")
        input_path = arguments.get("input")
        if not isinstance(schema, str) or not isinstance(input_path, str):
            raise ValueError("adlc_validate_artifact requires string arguments: schema, input")
        schema_path = resolve_schema(schema)
        artifact_path = Path(input_path)
        if not artifact_path.is_absolute():
            artifact_path = ROOT / artifact_path
        errors = validate_artifact(schema_path, artifact_path)
        payload = {
            "valid": len(errors) == 0,
            "schema": rel_path(schema_path),
            "input": rel_path(artifact_path),
            "errors": errors,
        }
        return tool_result(payload, is_error=not payload["valid"])
    if name == "adlc_run_phase":
        args = argparse.Namespace(
            phase=arguments.get("phase"),
            brief_id=arguments.get("brief_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            input=arguments.get("input"),
            output=arguments.get("output"),
            runtime=arguments.get("runtime"),
            tools=arguments.get("tools"),
            schema=arguments.get("schema"),
            label=arguments.get("label"),
            dry_run=arguments.get("dry_run", True),
            json=True,
        )
        exit_code, payload = run_phase_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_resume_workflow":
        workspace = resolve_workspace(arguments.get("workspace"))
        state_path = resolve_under_workspace(arguments.get("state"), workspace, DEFAULT_STATE_PATH)
        state = load_workflow_state(state_path)
        state["resume_count"] = int(state.get("resume_count", 0)) + 1
        state["updated_at"] = utc_now()
        node_by_id, _ = workflow_maps()
        next_action = {
            "phase": state["phase"],
            "status": state["status"],
            "node": node_by_id.get(state["phase"]),
            "runnable": state["status"] == "planned" and state["phase"] not in {"done", "escalate"},
        }
        state.setdefault("checkpoint", {})["next_action"] = next_action
        save_workflow_state(state_path, state)
        return tool_result({"state_path": rel_path(state_path), "state": state, "next_action": next_action})
    if name == "adlc_emit_work_items":
        args = argparse.Namespace(
            target=arguments.get("target"),
            build_brief=arguments.get("build_brief"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            provider_command=arguments.get("provider_command"),
            require_ready=arguments.get("require_ready", False),
            phase_project_map=arguments.get("phase_project_map"),
            bypass_readiness_check=arguments.get("bypass_readiness_check", False),
            json=True,
        )
        exit_code, payload = emit_work_items_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
    raise KeyError(f"Unknown tool: {name}")


def jsonrpc_response(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_mcp_message(message: Dict[str, Any]) -> Dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if request_id is None:
        return None

    if method == "initialize":
        protocol_version = params.get("protocolVersion", "2025-06-18")
        return jsonrpc_response(
            request_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "adlc", "version": "0.1.0"},
            },
        )
    if method == "ping":
        return jsonrpc_response(request_id, {})
    if method == "tools/list":
        return jsonrpc_response(request_id, {"tools": mcp_tools()})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return jsonrpc_error(request_id, -32602, "tools/call requires name and arguments")
        try:
            return jsonrpc_response(request_id, call_tool(name, arguments))
        except KeyError as exc:
            return jsonrpc_error(request_id, -32602, str(exc).strip("'"))
        except Exception as exc:
            return jsonrpc_response(
                request_id,
                tool_result({"error": str(exc)}, is_error=True),
            )

    return jsonrpc_error(request_id, -32601, f"Method not found: {method}")


def command_mcp_serve(args: argparse.Namespace) -> int:
    del args
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            write_json(jsonrpc_error(None, -32700, f"Parse error: {exc.msg}"))
            continue
        if not isinstance(message, dict):
            write_json(jsonrpc_error(None, -32600, "Invalid request"))
            continue
        response = handle_mcp_message(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            sys.stdout.flush()
    return 0


def command_mcp_tools(args: argparse.Namespace) -> int:
    payload = {"tools": mcp_tools()}
    if args.json:
        write_json(payload)
    else:
        for tool in payload["tools"]:
            print(f"{tool['name']}\t{tool['description']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adlc")
    parser.add_argument("--root", default=str(ROOT), help="ADLC repo root. Defaults to ADLC_ROOT or script parent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_agents = subparsers.add_parser("list-agents", help="List registered ADLC agents.")
    list_agents.add_argument("--json", action="store_true", help="Emit JSON.")
    list_agents.set_defaults(func=command_list_agents)

    list_phases = subparsers.add_parser("list-phases", help="List workflow nodes and edges.")
    list_phases.add_argument("--json", action="store_true", help="Emit JSON.")
    list_phases.set_defaults(func=command_list_phases)

    validate = subparsers.add_parser("validate-artifact", help="Validate an artifact against an ADLC JSON schema.")
    validate.add_argument("--schema", required=True, help="Schema alias or path.")
    validate.add_argument("--input", required=True, help="Artifact JSON path.")
    validate.add_argument("--json", action="store_true", help="Emit JSON.")
    validate.set_defaults(func=command_validate_artifact)

    run = subparsers.add_parser("run", help="Run or dry-run ADLC workflow phases with persisted state.")
    run.add_argument("--brief-id", help="Build Brief ID. Required when creating new state without --input.")
    run.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    run.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    run.add_argument("--input", help="Input artifact path for agent phases.")
    run.add_argument("--output", help="Output artifact path for the current phase.")
    run.add_argument("--runtime", choices=SUPPORTED_RUNTIMES, help="Runtime adapter to use. Defaults to ADLC_RUNTIME or claude.")
    run.add_argument("--tools", help="Runtime tool allowlist CSV for agent phases.")
    run.add_argument("--schema", help="Schema alias or path for agent output enforcement.")
    run.add_argument("--label", help="Transition label to use after this phase.")
    run.add_argument("--max-phases", type=int, default=1, help="Maximum phases to advance in this invocation.")
    run.add_argument("--dry-run", action="store_true", help="Plan and advance state without invoking runtime adapters.")
    run.add_argument("--json", action="store_true", help="Emit JSON.")
    run.set_defaults(func=command_run, phase=None)

    run_phase = subparsers.add_parser("run-phase", help="Run or dry-run one ADLC workflow phase.")
    run_phase.add_argument("phase", nargs="?", help="Workflow phase ID. Defaults to the phase in workflow state.")
    run_phase.add_argument("--brief-id", help="Build Brief ID. Required when creating new state.")
    run_phase.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    run_phase.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    run_phase.add_argument("--input", help="Input artifact path for agent phases.")
    run_phase.add_argument("--output", help="Output artifact path for this phase.")
    run_phase.add_argument("--runtime", choices=SUPPORTED_RUNTIMES, help="Runtime adapter to use. Defaults to ADLC_RUNTIME or claude.")
    run_phase.add_argument("--tools", help="Runtime tool allowlist CSV for agent phases.")
    run_phase.add_argument("--schema", help="Schema alias or path for agent output enforcement.")
    run_phase.add_argument("--label", help="Transition label to use after this phase.")
    run_phase.add_argument("--dry-run", action="store_true", help="Plan and advance state without invoking runtime adapters.")
    run_phase.add_argument("--json", action="store_true", help="Emit JSON.")
    run_phase.set_defaults(func=command_run_phase)

    resume = subparsers.add_parser("resume-workflow", help="Resume ADLC workflow state and report the next action.")
    resume.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    resume.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    resume.add_argument("--json", action="store_true", help="Emit JSON.")
    resume.set_defaults(func=command_resume_workflow)

    emit = subparsers.add_parser("emit-work-items", help="Prepare or mutate normalized ADLC work items.")
    emit.add_argument("--target", required=True, choices=WORK_ITEM_TARGETS, help="Work-item target.")
    emit.add_argument("--build-brief", required=True, help="Build Brief JSON path.")
    emit.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    emit.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    emit.add_argument("--dry-run", action="store_true", help="Prepare payload without external mutation.")
    emit.add_argument("--allow-mutation", action="store_true", help="Permit local provider mutation.")
    emit.add_argument("--provider-command", help="Local provider command that accepts the normalized payload on stdin.")
    emit.add_argument("--require-ready", action="store_true", help="Fail if readiness report is blocked.")
    emit.add_argument("--phase-project-map", help="JSON object, or path to one, mapping phase labels to project names.")
    emit.add_argument("--bypass-readiness-check", action="store_true", help="Force mutation even if readiness is blocked.")
    emit.add_argument("--json", action="store_true", help="Emit JSON.")
    emit.set_defaults(func=command_emit_work_items)

    mcp = subparsers.add_parser("mcp-tools", help="Emit MCP-compatible tool declarations for the ADLC CLI.")
    mcp.add_argument("--json", action="store_true", help="Emit JSON.")
    mcp.set_defaults(func=command_mcp_tools)

    mcp_serve = subparsers.add_parser("mcp-serve", help="Serve ADLC tools over newline-delimited MCP JSON-RPC stdio.")
    mcp_serve.set_defaults(func=command_mcp_serve)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    global ROOT
    ROOT = Path(args.root).resolve()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
