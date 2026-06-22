#!/usr/bin/env python3
"""ADLC contract CLI.

This is intentionally thin: it exposes the machine-readable ADLC contracts
without becoming a full workflow orchestrator.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Dict, Iterable, List, Tuple

from adlc_runtime.metadata import (
    DEFAULT_PHASE_TOOLS,
    DEFAULT_STATE_PATH,
    DEFAULT_SUCCESS_LABELS,
    SCHEMA_ALIASES,
    SUPPORTED_RUNTIMES,
    WORK_ITEM_TARGETS,
    command_description,
    command_mcp_name,
)


ROOT = Path(os.environ.get("ADLC_ROOT", Path(__file__).resolve().parents[2]))


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
            if node_id in {"graph", "node", "edge"} or node_id.startswith("l_"):
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


def new_run_id() -> str:
    return f"adlc-run-{uuid.uuid4().hex[:12]}"


def new_session_id() -> str:
    return f"adlc-{uuid.uuid4().hex[:12]}"


def ensure_workflow_identity(state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(state.get("run_id"), str) or not state["run_id"].strip():
        state["run_id"] = new_run_id()
    if not isinstance(state.get("session_id"), str) or not state["session_id"].strip():
        state["session_id"] = new_session_id()
    try:
        resume_count = int(state.get("resume_count", 0))
    except (TypeError, ValueError):
        resume_count = 0
    state["resume_count"] = max(0, resume_count)
    try:
        attempt = int(state.get("attempt", state["resume_count"] + 1))
    except (TypeError, ValueError):
        attempt = state["resume_count"] + 1
    state["attempt"] = max(1, attempt)
    return state


def workflow_identity_payload(state: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    identity: Dict[str, Any] = {}
    for key in ("brief_id", "run_id", "session_id", "resume_count", "attempt"):
        if key in state:
            identity[key] = state[key]
    return identity or None


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
        "run_id": new_run_id(),
        "session_id": new_session_id(),
        "phase": phase,
        "step": "ready",
        "status": "planned",
        "started_at": now,
        "updated_at": now,
        "checkpoint": checkpoint,
        "side_effects": [],
        "resume_count": 0,
        "attempt": 1,
    }


def load_workflow_state(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"workflow state not found: {path}")
    state = read_json(path)
    if not isinstance(state, dict):
        raise ValueError(f"workflow state must be a JSON object: {path}")
    return state


def save_workflow_state(path: Path, state: Dict[str, Any]) -> None:
    ensure_workflow_identity(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("workflow-state"), path)
    if errors:
        raise ValueError("workflow state failed schema validation: " + "; ".join(errors))


def workflow_state_for_args(args: argparse.Namespace, workspace: Path) -> Tuple[Path, Dict[str, Any]]:
    state_path = resolve_under_workspace(getattr(args, "state", None), workspace, DEFAULT_STATE_PATH)
    if state_path.exists():
        return state_path, ensure_workflow_identity(load_workflow_state(state_path))

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


def phase_arg_path(raw_path: str | None, workspace: Path) -> Path | None:
    if not raw_path:
        return None
    return resolve_input_path(raw_path, workspace)


def phase_build_brief_path(args: argparse.Namespace, workspace: Path, state: Dict[str, Any]) -> Path | None:
    raw_path = (
        getattr(args, "build_brief", None)
        or getattr(args, "input", None)
        or state.get("checkpoint", {}).get("build_brief")
        or state.get("checkpoint", {}).get("input")
    )
    return phase_arg_path(raw_path, workspace)


def load_phase_build_brief(args: argparse.Namespace, workspace: Path, state: Dict[str, Any]) -> Tuple[Path, Dict[str, Any]]:
    brief_path = phase_build_brief_path(args, workspace, state)
    if not brief_path:
        raise ValueError("build brief is required for this tool node")
    if not brief_path.is_file():
        raise FileNotFoundError(f"build brief not found: {brief_path}")
    errors = validate_artifact(resolve_schema("build-brief"), brief_path)
    if errors:
        raise ValueError("build brief failed schema validation: " + "; ".join(errors))
    brief = read_json(brief_path)
    if not isinstance(brief, dict):
        raise ValueError(f"build brief must be a JSON object: {brief_path}")
    return brief_path, brief


def build_brief_tasks(brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks = brief.get("sections", {}).get("8_task_tickets", [])
    return [task for task in tasks if isinstance(task, dict)]


def task_verifier_commands(task: Dict[str, Any]) -> List[str]:
    commands: List[str] = []
    verification = task.get("verification_spec")
    if not isinstance(verification, dict):
        return commands
    primary = verification.get("primary_verifier")
    if isinstance(primary, dict) and isinstance(primary.get("target"), str) and primary["target"].strip():
        commands.append(primary["target"].strip())
    secondary = verification.get("secondary_verifiers")
    if isinstance(secondary, list):
        for verifier in secondary:
            if isinstance(verifier, dict) and isinstance(verifier.get("target"), str) and verifier["target"].strip():
                commands.append(verifier["target"].strip())
    return commands


def verifier_commands_for_phase(args: argparse.Namespace, workspace: Path, state: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    commands: List[str] = []
    evidence_refs: List[str] = []
    warnings: List[str] = []
    for value in getattr(args, "verifier", None) or []:
        if isinstance(value, str) and value.strip():
            commands.append(value.strip())

    brief_path = phase_build_brief_path(args, workspace, state)
    if brief_path and brief_path.is_file():
        try:
            errors = validate_artifact(resolve_schema("build-brief"), brief_path)
            if errors:
                warnings.append("build_brief_schema_invalid")
            else:
                brief = read_json(brief_path)
                for task in build_brief_tasks(brief):
                    commands.extend(task_verifier_commands(task))
                evidence_refs.append(rel_path(brief_path))
        except Exception as exc:
            warnings.append(f"build_brief_unreadable:{exc}")

    for env_name in ("TEST_COMMAND", "LINT_COMMAND", "BUILD_COMMAND"):
        value = os.environ.get(env_name)
        if value and value.strip():
            commands.append(value.strip())

    return list(dict.fromkeys(commands)), evidence_refs, warnings


def tool_node_base_result(
    phase: str,
    state: Dict[str, Any],
    dry_run: bool,
    status: str,
    label: str | None = None,
    inputs: Dict[str, Any] | None = None,
    outputs: Dict[str, Any] | None = None,
    evidence_refs: List[str] | None = None,
    warnings: List[str] | None = None,
    issues: List[Dict[str, Any]] | None = None,
    stop_reason: str | None = None,
    skip_reason: str | None = None,
    execution: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "phase": phase,
        "status": status,
        "label": label,
        "run_identity": workflow_identity_payload(state),
        "dry_run": dry_run,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "evidence_refs": evidence_refs or [],
        "warnings": warnings or [],
        "issues": issues or [],
    }
    if stop_reason:
        payload["stop_reason"] = stop_reason
    if skip_reason:
        payload["skip_reason"] = skip_reason
    if execution is not None:
        payload["execution"] = execution
    return payload


def output_log_path(output_path: Path, command_index: int, stream_name: str) -> Path:
    return output_path.parent / f"{output_path.stem}.{command_index}.{stream_name}.log"


def run_verifier_commands(commands: List[str], workspace: Path, output_path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    results: List[Dict[str, Any]] = []
    evidence_refs: List[str] = []
    for index, command in enumerate(commands, start=1):
        started_at = utc_now()
        process = subprocess.run(command, cwd=str(workspace), shell=True, text=True, capture_output=True, check=False)
        ended_at = utc_now()
        stdout_path = output_log_path(output_path, index, "stdout")
        stderr_path = output_log_path(output_path, index, "stderr")
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(process.stdout, encoding="utf-8")
        stderr_path.write_text(process.stderr, encoding="utf-8")
        evidence_refs.extend([rel_path(stdout_path), rel_path(stderr_path)])
        results.append(
            {
                "command": command,
                "exit_code": process.returncode,
                "status": "pass" if process.returncode == 0 else "fail",
                "stdout_ref": rel_path(stdout_path),
                "stderr_ref": rel_path(stderr_path),
                "stdout_tail": process.stdout[-2000:],
                "stderr_tail": process.stderr[-2000:],
                "started_at": started_at,
                "ended_at": ended_at,
            }
        )
    return results, evidence_refs


def scaffold_planned_writes(brief: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    planned: List[Dict[str, Any]] = []
    if not brief:
        return planned
    for task in build_brief_tasks(brief):
        task_id = str(task.get("task_id") or "unknown-task")
        for field_name, operation in (("files_to_create", "create_file"), ("files_to_modify", "inspect_or_update_file")):
            values = task.get(field_name)
            if not isinstance(values, list):
                continue
            for raw_path in values:
                if not isinstance(raw_path, str) or not raw_path.strip():
                    continue
                planned.append(
                    {
                        "task_id": task_id,
                        "operation": operation,
                        "path": raw_path.strip(),
                        "reason": task.get("title") or task_id,
                    }
                )
    return planned


def context_packages_for_brief(
    brief: Dict[str, Any],
    state: Dict[str, Any],
    brief_path: Path,
) -> List[Dict[str, Any]]:
    packages: List[Dict[str, Any]] = []
    queue_claims = [item for item in state.get("queue_claims", []) if isinstance(item, dict)]
    worktree_refs = [item for item in state.get("worktree_refs", []) if isinstance(item, dict)]
    work_item_links = [item for item in state.get("work_item_links", []) if isinstance(item, dict)]
    for task in build_brief_tasks(brief):
        task_id = str(task.get("task_id") or "unknown-task")
        packages.append(
            {
                "task_id": task_id,
                "title": task.get("title"),
                "objective": task.get("objective"),
                "intent_refs": [brief.get("brief_id"), brief.get("prd_id")],
                "constraints": {
                    "scope": task.get("scope", []),
                    "out_of_scope": task.get("out_of_scope", []),
                    "anti_slop_rules": task.get("anti_slop_rules", []),
                    "compatibility_contract": task.get("compatibility_contract"),
                    "implementation_interface_contract": task.get("implementation_interface_contract"),
                    "productionization_gate": task.get("productionization_gate"),
                },
                "target_files": {
                    "files_to_modify": task.get("files_to_modify", []),
                    "files_to_create": task.get("files_to_create", []),
                },
                "verifier_commands": task_verifier_commands(task),
                "queue_claims": [claim for claim in queue_claims if claim.get("task_id") == task_id],
                "worktree_refs": [ref for ref in worktree_refs if ref.get("task_id") == task_id],
                "work_item_links": [link for link in work_item_links if link.get("task_id") == task_id],
                "source_refs": [rel_path(brief_path)],
            }
        )
    return packages


def learning_candidates_from_args(args: argparse.Namespace, workspace: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    input_path = phase_arg_path(getattr(args, "input", None), workspace)
    if not input_path:
        return [], warnings
    if not input_path.is_file():
        warnings.append(f"learning_input_missing:{input_path}")
        return [], warnings
    payload = read_json(input_path)
    if not isinstance(payload, dict):
        warnings.append("learning_input_not_object")
        return [], warnings
    candidates = payload.get("learning_candidates", [])
    if not isinstance(candidates, list):
        warnings.append("learning_candidates_not_list")
        return [], warnings
    return [candidate for candidate in candidates if isinstance(candidate, dict)], warnings


def valid_learning_candidate(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    required_fields = ("title", "learning", "source_evidence", "verifier_evidence", "stale_conditions", "redaction_status")
    for field_name in required_fields:
        if not candidate.get(field_name):
            issues.append({"rule": "missing_learning_candidate_field", "field": field_name})
    if str(candidate.get("redaction_status")) not in {"passed", "redacted", "safe"}:
        issues.append({"rule": "redaction_not_passed", "field": "redaction_status"})
    return issues


def yaml_list(values: List[str]) -> str:
    return "\n".join(f"  - {json.dumps(value)}" for value in values)


def learning_entry_text(candidate: Dict[str, Any], task_id: str) -> str:
    today = utc_now()[:10]
    title = str(candidate.get("title") or "Verified ADLC learning").strip()
    module = str(candidate.get("module") or "workflow").strip()
    source_evidence = [str(value) for value in candidate.get("source_evidence", []) if str(value).strip()]
    verifier_evidence = [str(value) for value in candidate.get("verifier_evidence", []) if str(value).strip()]
    stale_conditions = [str(value) for value in candidate.get("stale_conditions", []) if str(value).strip()]
    learning = str(candidate.get("learning") or "").strip()
    applicability = str(candidate.get("applicability") or "Use when the same verified condition appears again.").strip()
    verifier_command = verifier_evidence[0] if verifier_evidence else "verified evidence unavailable"
    return f"""---
title: {json.dumps(title)}
date: {json.dumps(today)}
adlc_domain: "workflow"
problem_type: "workflow"
module: {json.dumps(module)}
severity: "low"
track: "knowledge"
tags: ["learning-capture", "adlc"]
related_tasks: [{json.dumps(task_id)}]
source_evidence:
{yaml_list(source_evidence or ["learning candidate source evidence"])}
verifier:
  type: "command"
  command: {json.dumps(verifier_command)}
  expected: "passes"
redaction_review:
  status: "passed"
  reviewer: "adlc-learning-capture"
stale_conditions:
{yaml_list(stale_conditions or ["source verifier changes"])}
---

# {title}

## Context

ADLC captured this learning from a verified workflow closeout candidate.

## Learning

{learning}

## Applicability

{applicability}

## Evidence

{chr(10).join(f"- Source: `{value}`" for value in (source_evidence or ["learning candidate source evidence"]))}
{chr(10).join(f"- Verifier: `{value}`" for value in (verifier_evidence or ["verified evidence unavailable"]))}

## Stale Conditions

{chr(10).join(f"- {value}" for value in (stale_conditions or ["source verifier changes"]))}

## Guidance

Apply this only when the cited verifier evidence still matches the current code and workflow contract.

## Examples

Use the cited source and verifier refs as the starting point for future scoped refreshes.
"""


def tool_node_mutation_admission(
    args: argparse.Namespace,
    state_path: Path,
    state: Dict[str, Any],
    phase: str,
    action: str,
) -> Tuple[int, Dict[str, Any]]:
    if not getattr(args, "tool_registry", None):
        raise ValueError("--tool-registry is required with --allow-mutation")
    audit_path = cli_input_path(args.audit_trail) if getattr(args, "audit_trail", None) else state_path.parent / "tool_node_permission_audit.json"
    return action_admit_payload(
        tool_registry_path=cli_input_path(args.tool_registry),
        tool_name="adlc-tool-node",
        action=action,
        phase=phase,
        state_path=state_path if state_path.exists() else None,
        brief_id=state.get("brief_id"),
        run_id=state.get("run_id"),
        session_id=state.get("session_id"),
        allow_mutation=True,
        human_approved=getattr(args, "human_approved", False),
        approval_ref=getattr(args, "approval_ref", None),
        audit_trail_path=audit_path,
    )


def upsert_phase_artifact_state(state: Dict[str, Any], phase: str, artifact_ref: str, result: Dict[str, Any]) -> None:
    artifacts = [
        item
        for item in state.get("phase_artifacts", [])
        if not (isinstance(item, dict) and item.get("phase") == phase and item.get("artifact_ref") == artifact_ref)
    ]
    entry: Dict[str, Any] = {
        "phase": phase,
        "artifact_ref": artifact_ref,
        "status": result.get("status"),
        "label": result.get("label"),
        "evidence_refs": result.get("evidence_refs", []),
        "updated_at": utc_now(),
    }
    if result.get("stop_reason"):
        entry["stop_reason"] = result["stop_reason"]
    artifacts.append(entry)
    state["phase_artifacts"] = artifacts


def persist_tool_node_result(output_path: Path, result: Dict[str, Any]) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.setdefault("outputs", {})["artifact_ref"] = rel_path(output_path)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("tool-node-result"), output_path)
    if errors:
        raise ValueError("tool-node result failed schema validation: " + "; ".join(errors))
    return rel_path(output_path)


def finish_tool_node_phase(
    state_path: Path,
    state: Dict[str, Any],
    phase: str,
    plan: Dict[str, Any],
    result: Dict[str, Any],
    output_path: Path,
) -> Tuple[int, Dict[str, Any]]:
    artifact_ref = persist_tool_node_result(output_path, result)
    upsert_phase_artifact_state(state, phase, artifact_ref, result)
    if result["dry_run"]:
        state["updated_at"] = utc_now()
        append_history(state, {"phase": phase, "status": result["status"], "dry_run": True, "artifact_ref": artifact_ref, "invocation": plan})
    elif result["status"] in {"pass", "skipped"}:
        state = apply_phase_result(
            state=state,
            phase=phase,
            status="completed",
            label=result.get("label"),
            plan={**plan, "artifact_ref": artifact_ref},
            dry_run=False,
        )
        upsert_phase_artifact_state(state, phase, artifact_ref, result)
    else:
        state["phase"] = phase
        state["status"] = "failed"
        state["step"] = "failed"
        state["updated_at"] = utc_now()
        state["stop_reason"] = result.get("stop_reason", "tool_node_failed")
        append_history(state, {"phase": phase, "status": result["status"], "dry_run": False, "artifact_ref": artifact_ref, "invocation": plan})
    save_workflow_state(state_path, state)
    exit_code = 0 if result["status"] in {"pass", "skipped", "planned"} else 1
    return exit_code, {
        "state_path": rel_path(state_path),
        "run_identity": workflow_identity_payload(state),
        "state": state,
        "plan": plan,
        "artifact_ref": artifact_ref,
        "tool_result": result,
        "dry_run": result["dry_run"],
    }


def execute_compound_preflight_tool(args: argparse.Namespace, workspace: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    inputs = {"workspace": str(workspace), "build_brief": getattr(args, "build_brief", None), "input": getattr(args, "input", None)}
    if dry_run:
        return tool_node_base_result(phase, state, True, "planned", inputs=inputs, outputs={"command": "compound-context"})
    payload = compound_context_payload(
        argparse.Namespace(
            workspace=str(workspace),
            input=getattr(args, "input", None),
            build_brief=getattr(args, "build_brief", None),
            max_refs=getattr(args, "max_refs", 8),
            json=True,
        )
    )
    return tool_node_base_result(
        phase,
        state,
        False,
        "pass",
        label="proceed",
        inputs=inputs,
        outputs={"compound_context": payload},
        evidence_refs=[ref["path"] for ref in payload.get("learning_refs", []) if isinstance(ref, dict) and ref.get("path")],
    )


def execute_scaffold_tool(args: argparse.Namespace, workspace: Path, state_path: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    brief = None
    brief_path = None
    warnings: List[str] = []
    try:
        brief_path, brief = load_phase_build_brief(args, workspace, state)
    except Exception as exc:
        warnings.append(f"build_brief_unavailable:{exc}")
    planned_writes = scaffold_planned_writes(brief)
    inputs = {"workspace": str(workspace), "build_brief": rel_path(brief_path) if brief_path else None}
    outputs = {"planned_writes": planned_writes}
    evidence_refs = [rel_path(brief_path)] if brief_path else []
    if dry_run:
        return tool_node_base_result(phase, state, True, "planned", inputs=inputs, outputs=outputs, evidence_refs=evidence_refs, warnings=warnings)
    if not planned_writes:
        return tool_node_base_result(
            phase,
            state,
            False,
            "skipped",
            label=None,
            inputs=inputs,
            outputs=outputs,
            evidence_refs=evidence_refs,
            warnings=warnings,
            skip_reason="no_scaffold_writes",
        )
    if not getattr(args, "allow_mutation", False):
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            outputs=outputs,
            evidence_refs=evidence_refs,
            warnings=warnings,
            issues=[{"rule": "action_not_admitted", "message": "scaffold writes require --allow-mutation and --tool-registry"}],
            stop_reason="action_not_admitted",
        )
    admission_exit, admission = tool_node_mutation_admission(args, state_path, state, phase, "scaffold_write")
    outputs["admission"] = admission
    if admission_exit != 0:
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            outputs=outputs,
            evidence_refs=evidence_refs,
            warnings=warnings,
            issues=admission.get("issues", []),
            stop_reason=admission.get("stop_reason") or admission["status"],
        )
    written: List[str] = []
    for item in planned_writes:
        if item["operation"] != "create_file":
            continue
        target = resolve_under_workspace(item["path"], workspace, item["path"])
        if target.exists():
            warnings.append(f"scaffold_target_exists:{rel_path(target)}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {item['reason']}\n\nGenerated by ADLC scaffold for {item['task_id']}.\n", encoding="utf-8")
        written.append(rel_path(target))
    if written:
        record_local_side_effect(state, "adlc-tool-node", "scaffold_write", phase, ",".join(written))
    outputs["written"] = written
    return tool_node_base_result(phase, state, False, "pass", label=None, inputs=inputs, outputs=outputs, evidence_refs=[*evidence_refs, *written], warnings=warnings)


def execute_context_assembly_tool(args: argparse.Namespace, workspace: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    inputs = {"workspace": str(workspace), "build_brief": getattr(args, "build_brief", None) or getattr(args, "input", None)}
    try:
        brief_path, brief = load_phase_build_brief(args, workspace, state)
    except Exception as exc:
        status = "planned" if dry_run else "blocked"
        return tool_node_base_result(
            phase,
            state,
            dry_run,
            status,
            inputs=inputs,
            outputs={"context_packages": []},
            issues=[{"rule": "missing_build_brief", "message": str(exc)}],
            stop_reason=None if dry_run else "missing_build_brief",
        )
    packages = context_packages_for_brief(brief, state, brief_path)
    return tool_node_base_result(
        phase,
        state,
        dry_run,
        "planned" if dry_run else "pass",
        label=None,
        inputs={"workspace": str(workspace), "build_brief": rel_path(brief_path)},
        outputs={"context_packages": packages, "package_count": len(packages)},
        evidence_refs=[rel_path(brief_path)],
    )


def execute_qa_tool(args: argparse.Namespace, workspace: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    commands, evidence_refs, warnings = verifier_commands_for_phase(args, workspace, state)
    inputs = {"workspace": str(workspace), "commands": commands}
    if dry_run:
        return tool_node_base_result(phase, state, True, "planned", inputs=inputs, outputs={"commands": commands}, evidence_refs=evidence_refs, warnings=warnings)
    if not commands:
        if getattr(args, "allow_noop", False):
            return tool_node_base_result(
                phase,
                state,
                False,
                "skipped",
                label="skipped",
                inputs=inputs,
                outputs={"commands": []},
                warnings=warnings,
                skip_reason="no_verifier_commands",
            )
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            outputs={"commands": []},
            evidence_refs=evidence_refs,
            warnings=warnings,
            issues=[{"rule": "missing_verifier_command", "message": "qa requires --verifier, Build Brief verification_spec, or TEST_COMMAND/LINT_COMMAND/BUILD_COMMAND"}],
            stop_reason="missing_verifier_command",
        )
    results, command_evidence = run_verifier_commands(commands, workspace, output_path)
    failing = [item for item in results if item["exit_code"] != 0]
    status = "fail" if failing else "pass"
    success_label = getattr(args, "label", None) or "pass + overlays inactive"
    return tool_node_base_result(
        phase,
        state,
        False,
        status,
        label="fail" if failing else success_label,
        inputs=inputs,
        outputs={"commands": commands, "results": results},
        evidence_refs=[*evidence_refs, *command_evidence],
        warnings=warnings,
        issues=[{"rule": "verifier_failed", "command": item["command"], "exit_code": item["exit_code"]} for item in failing],
        stop_reason="verifier_failed" if failing else None,
        execution={"command_count": len(commands), "failed": len(failing)},
    )


def execute_slop_gate_tool(args: argparse.Namespace, workspace: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    brief_path = phase_build_brief_path(args, workspace, state)
    inputs = {"build_brief": rel_path(brief_path) if brief_path else None}
    if dry_run:
        return tool_node_base_result(phase, state, True, "planned", inputs=inputs, outputs={"command": "slop-gate"})
    if not brief_path:
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            issues=[{"rule": "missing_build_brief", "message": "slop_gate requires a Build Brief"}],
            stop_reason="missing_build_brief",
        )
    payload = slop_gate_payload(brief_path)
    generated = payload.get("summary", {}).get("generated_output_surfaces", 0)
    if generated == 0:
        return tool_node_base_result(
            phase,
            state,
            False,
            "skipped",
            label=None,
            inputs=inputs,
            outputs={"slop_gate": payload},
            evidence_refs=[rel_path(brief_path)],
            skip_reason="generated_output_surface_inactive",
        )
    status = "pass" if payload["status"] == "pass" else "fail"
    return tool_node_base_result(
        phase,
        state,
        False,
        status,
        label="pass" if status == "pass" else "fail",
        inputs=inputs,
        outputs={"slop_gate": payload},
        evidence_refs=[rel_path(brief_path)],
        issues=payload.get("issues", []),
        stop_reason="slop_gate_failed" if status == "fail" else None,
    )


def execute_learning_capture_tool(args: argparse.Namespace, workspace: Path, state_path: Path, state: Dict[str, Any], phase: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = bool(args.dry_run)
    candidates, warnings = learning_candidates_from_args(args, workspace)
    inputs = {"workspace": str(workspace), "candidate_count": len(candidates), "input": getattr(args, "input", None)}
    if not candidates:
        return tool_node_base_result(
            phase,
            state,
            dry_run,
            "planned" if dry_run else "skipped",
            label=None if dry_run else "skipped",
            inputs=inputs,
            outputs={"written": []},
            warnings=warnings,
            skip_reason="no_verified_learning_candidates" if not dry_run else None,
        )
    issues: List[Dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        issues.extend({**issue, "candidate_index": index} for issue in valid_learning_candidate(candidate))
    if issues:
        return tool_node_base_result(
            phase,
            state,
            dry_run,
            "blocked" if not dry_run else "planned",
            inputs=inputs,
            outputs={"candidate_count": len(candidates)},
            warnings=warnings,
            issues=issues,
            stop_reason=None if dry_run else "invalid_learning_candidate",
        )
    if dry_run:
        return tool_node_base_result(phase, state, True, "planned", inputs=inputs, outputs={"candidate_count": len(candidates)}, warnings=warnings)
    if not getattr(args, "allow_mutation", False):
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            outputs={"candidate_count": len(candidates)},
            warnings=warnings,
            issues=[{"rule": "action_not_admitted", "message": "learning capture writes require --allow-mutation and --tool-registry"}],
            stop_reason="action_not_admitted",
        )
    admission_exit, admission = tool_node_mutation_admission(args, state_path, state, phase, "learning_capture_write")
    if admission_exit != 0:
        return tool_node_base_result(
            phase,
            state,
            False,
            "blocked",
            inputs=inputs,
            outputs={"admission": admission},
            warnings=warnings,
            issues=admission.get("issues", []),
            stop_reason=admission.get("stop_reason") or admission["status"],
        )
    solutions_dir = workspace / "docs" / "solutions"
    solutions_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    validation_results: List[Dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate.get("task_id") or state.get("brief_id") or "ADLC")
        title_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(candidate.get("title") or task_id).strip()).strip("-").lower() or "learning"
        target = solutions_dir / f"{title_slug}.md"
        target.write_text(learning_entry_text(candidate, task_id), encoding="utf-8")
        process = subprocess.run([sys.executable, str(ROOT / "scripts/validate_learning_entry.py"), str(target)], text=True, capture_output=True, check=False)
        validation_results.append({"path": rel_path(target), "returncode": process.returncode, "stdout": process.stdout[-1000:], "stderr": process.stderr[-1000:]})
        if process.returncode != 0:
            return tool_node_base_result(
                phase,
                state,
                False,
                "fail",
                inputs=inputs,
                outputs={"written": written, "validation_results": validation_results, "admission": admission},
                warnings=warnings,
                issues=[{"rule": "learning_entry_validation_failed", "path": rel_path(target), "stderr": process.stderr[-2000:]}],
                stop_reason="learning_entry_validation_failed",
            )
        written.append(rel_path(target))
    if written:
        record_local_side_effect(state, "adlc-tool-node", "learning_capture_write", phase, ",".join(written))
    return tool_node_base_result(
        phase,
        state,
        False,
        "pass",
        label="pass",
        inputs=inputs,
        outputs={"written": written, "validation_results": validation_results, "admission": admission},
        evidence_refs=written,
        warnings=warnings,
    )


def execute_tool_node_phase(
    args: argparse.Namespace,
    workspace: Path,
    state_path: Path,
    state: Dict[str, Any],
    phase: str,
    plan: Dict[str, Any],
) -> Tuple[int, Dict[str, Any]]:
    output_path = Path(plan["output"])
    handlers = {
        "compound_preflight": lambda: execute_compound_preflight_tool(args, workspace, state, phase, plan),
        "scaffold": lambda: execute_scaffold_tool(args, workspace, state_path, state, phase, plan),
        "context_assembly": lambda: execute_context_assembly_tool(args, workspace, state, phase, plan),
        "qa": lambda: execute_qa_tool(args, workspace, state, phase, plan, output_path),
        "slop_gate": lambda: execute_slop_gate_tool(args, workspace, state, phase, plan),
        "learning_capture": lambda: execute_learning_capture_tool(args, workspace, state_path, state, phase, plan),
    }
    if phase not in handlers:
        result = tool_node_base_result(
            phase,
            state,
            bool(args.dry_run),
            "blocked",
            inputs={"workspace": str(workspace)},
            issues=[{"rule": "missing_tool_binding", "message": f"no deterministic binding exists for tool node {phase}"}],
            stop_reason="missing_tool_binding",
        )
    else:
        result = handlers[phase]()
    return finish_tool_node_phase(state_path, state, phase, plan, result, output_path)


def run_phase_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
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
        return 0, {
            "state_path": rel_path(state_path),
            "run_identity": workflow_identity_payload(state),
            "state": state,
            "result": "terminal",
        }

    if node_type == "human_gate":
        state["status"] = "awaiting_approval"
        state["stop_reason"] = "human_gate"
        state["updated_at"] = utc_now()
        append_history(state, {"phase": phase, "status": "awaiting_approval", "dry_run": args.dry_run})
        save_workflow_state(state_path, state)
        return 0, {
            "state_path": rel_path(state_path),
            "run_identity": workflow_identity_payload(state),
            "state": state,
            "result": "awaiting_approval",
        }

    if node_type == "tool":
        return execute_tool_node_phase(args, workspace, state_path, state, phase, plan)

    if args.dry_run or phase == "start" or node_type in {"fan_out", "workflow", "conditional"}:
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
        return 0, {
            "state_path": rel_path(state_path),
            "run_identity": workflow_identity_payload(state),
            "state": state,
            "plan": plan,
            "dry_run": True,
        }

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
        "run_identity": workflow_identity_payload(state),
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
        final_state = payloads[-1]["state"] if payloads else None
        final_payload = {
            "runs": payloads,
            "run_identity": workflow_identity_payload(final_state),
            "state": final_state,
        }
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(final_payload)
    else:
        state = final_payload["state"]
        print(f"{state['brief_id']}: {state['phase']} ({state['status']})")
    return exit_code


def resume_workflow_payload(workspace_arg: str | None, state_arg: str | None) -> Dict[str, Any]:
    workspace = resolve_workspace(workspace_arg)
    state_path = resolve_under_workspace(state_arg, workspace, DEFAULT_STATE_PATH)
    state = ensure_workflow_identity(load_workflow_state(state_path))
    state["resume_count"] = int(state.get("resume_count", 0)) + 1
    state["attempt"] = int(state.get("attempt", 1)) + 1
    resumed_at = utc_now()
    state["last_resumed_at"] = resumed_at
    state["updated_at"] = resumed_at
    next_action = resume_next_action_payload(state)
    state.setdefault("checkpoint", {})["next_action"] = next_action
    save_workflow_state(state_path, state)
    return {
        "state_path": rel_path(state_path),
        "run_identity": workflow_identity_payload(state),
        "state": state,
        "next_action": next_action,
    }


def command_resume_workflow(args: argparse.Namespace) -> int:
    try:
        payload = resume_workflow_payload(args.workspace, args.state)
        state = payload["state"]
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
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


def module_available(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


def workflow_state_phase_parity_issues() -> List[str]:
    try:
        nodes, _ = workflow_nodes_and_edges()
        schema = read_json(resolve_schema("workflow-state"))
        phase_schema = schema.get("properties", {}).get("phase", {})
        allowed = set(phase_schema.get("enum", []))
    except Exception as exc:
        return [f"unable to compute workflow/state phase parity: {exc}"]

    workflow_phases = {node["id"] for node in nodes}
    missing = sorted(workflow_phases - allowed)
    if missing:
        return ["workflow nodes missing from workflow-state phase enum: " + ", ".join(missing)]
    return []


def health_check_payload(include_optional: bool = False) -> Dict[str, Any]:
    checks = []

    def add(name: str, status: str, detail: str, required: bool = True) -> None:
        checks.append({"name": name, "status": status, "required": required, "detail": detail})

    python_ok = sys.version_info >= (3, 9)
    add(
        "python",
        "pass" if python_ok else "fail",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} at {sys.executable}",
    )

    jsonschema_ok = module_available("jsonschema")
    add(
        "jsonschema",
        "pass" if jsonschema_ok else "fail",
        "Python jsonschema module importable" if jsonschema_ok else "Install with: python3 -m pip install -e .",
    )

    bin_path = ROOT / "bin/adlc"
    add("bin/adlc", "pass" if os.access(bin_path, os.X_OK) else "fail", rel_path(bin_path))

    missing_schemas = [alias for alias, path in sorted(SCHEMA_ALIASES.items()) if not (ROOT / path).is_file()]
    add(
        "schemas",
        "pass" if not missing_schemas else "fail",
        "all schema aliases resolve" if not missing_schemas else "missing: " + ", ".join(missing_schemas),
    )

    phase_parity_issues = workflow_state_phase_parity_issues()
    add(
        "workflow-state-phase-parity",
        "pass" if not phase_parity_issues else "fail",
        "all WORKFLOW.dot nodes are valid workflow-state phases"
        if not phase_parity_issues
        else "; ".join(phase_parity_issues),
    )

    optional_checks = {
        "PyMuPDF": ("fitz", "optional PDF generation support"),
        "ruff": ("ruff", "optional lint audit command"),
        "pip-audit": ("pip-audit", "optional dependency audit command"),
        "vulture": ("vulture", "optional dead-code audit command"),
        "mypy": ("mypy", "optional type audit command"),
        "radon": ("radon", "optional complexity audit command"),
    }
    if include_optional:
        for name, (module_or_command, detail) in optional_checks.items():
            available = module_available(module_or_command) or shutil.which(module_or_command) is not None
            add(name, "pass" if available else "warn", detail, required=False)

    required_failures = [check for check in checks if check["required"] and check["status"] != "pass"]
    warnings_count = sum(1 for check in checks if check["status"] == "warn")
    status = "fail" if required_failures else ("warn" if warnings_count else "pass")
    return {
        "contract_version": "1.0.0",
        "status": status,
        "root": str(ROOT),
        "checks": checks,
        "summary": {
            "total": len(checks),
            "failed_required": len(required_failures),
            "warnings": warnings_count,
        },
    }


def command_health_check(args: argparse.Namespace) -> int:
    payload = health_check_payload(include_optional=args.include_optional)
    if args.json:
        write_json(payload)
    else:
        print(f"ADLC health-check: {payload['status']}")
        for check in payload["checks"]:
            print(f"{check['status']}\t{check['name']}\t{check['detail']}")
    return 0 if payload["summary"]["failed_required"] == 0 else 1


CI_SUITES = {
    "health-check": {
        "description": "ADLC runtime preflight",
        "command": ["bin/adlc", "health-check", "--json"],
    },
    "cli": {
        "description": "Agent-native CLI and MCP contract tests",
        "command": ["bash", "tests/test_adlc_cli.sh"],
    },
    "contracts": {
        "description": "Prompt, schema, runtime, and fixture contract tests",
        "command": ["bash", "tests/test_adlc_contracts.sh"],
    },
    "setup": {
        "description": "Target install/setup contract tests",
        "command": ["bash", "tests/test_setup.sh"],
    },
    "backtest": {
        "description": "Deterministic evaluator backtest",
        "command": ["bash", "tests/backtest/run_backtest.sh"],
    },
    "py-compile": {
        "description": "Python syntax compilation over scripts/",
        "command": [],
    },
}

DEFAULT_CI_SUITE_ORDER = ("health-check", "cli", "contracts", "setup", "backtest", "py-compile")


def ci_command_for_suite(suite_name: str) -> List[str]:
    if suite_name == "py-compile":
        script_paths = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "scripts").rglob("*.py"))
        return ["python3", "-m", "py_compile", *script_paths]
    return list(CI_SUITES[suite_name]["command"])


def run_ci_suite(suite_name: str) -> Dict[str, Any]:
    command = ci_command_for_suite(suite_name)
    started = monotonic()
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = int((monotonic() - started) * 1000)
    return {
        "name": suite_name,
        "description": CI_SUITES[suite_name]["description"],
        "command": command,
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def ci_payload(suites: List[str] | None = None) -> Tuple[int, Dict[str, Any]]:
    requested = suites or list(DEFAULT_CI_SUITE_ORDER)
    unknown = sorted(set(requested) - set(CI_SUITES))
    if unknown:
        raise ValueError("unknown CI suite(s): " + ", ".join(unknown))

    results = [run_ci_suite(suite_name) for suite_name in requested]
    failures = [result for result in results if result["status"] != "pass"]
    payload = {
        "contract_version": "1.0.0",
        "status": "fail" if failures else "pass",
        "root": str(ROOT),
        "suites": results,
        "summary": {
            "total": len(results),
            "passed": len(results) - len(failures),
            "failed": len(failures),
            "suite_order": requested,
        },
    }
    return (1 if failures else 0), payload


def command_ci(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = ci_payload(args.suite)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"ADLC CI: {payload['status']}")
        for result in payload["suites"]:
            print(f"{result['status']}\t{result['name']}\t{' '.join(result['command'])}")
    return exit_code


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def task_fingerprint_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    fingerprints = state.get("task_fingerprints", [])
    if not isinstance(fingerprints, list):
        fingerprints = []
    counts: Dict[str, int] = {}
    incomplete: List[Dict[str, Any]] = []
    for item in fingerprints:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
        if status not in {"completed", "skipped_already_satisfied"}:
            incomplete.append(
                {
                    "task_id": item.get("task_id"),
                    "status": status,
                    "primary_verifier": item.get("primary_verifier"),
                    "input_hash": item.get("input_hash"),
                }
            )
    return {
        "total": sum(counts.values()),
        "counts": counts,
        "incomplete": incomplete,
    }


def resume_next_action_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    node_by_id, _ = workflow_maps()
    return {
        "run_identity": workflow_identity_payload(state),
        "phase": state["phase"],
        "status": state["status"],
        "stop_reason": state.get("stop_reason"),
        "node": node_by_id.get(state["phase"]),
        "runnable": state["status"] == "planned" and state["phase"] not in {"done", "escalate"},
        "task_resume_status": task_fingerprint_summary(state),
        "loop_progress": state.get("loop_progress"),
        "no_progress_count": state.get("no_progress_count", 0),
        "control_events": state.get("control_events", []),
        "safe_checkpoint": state.get("safe_checkpoint"),
        "escalation_context": state.get("escalation_context"),
        "budget_status": state.get("budget_status"),
        "work_item_links": state.get("work_item_links", []),
        "queue_claims": state.get("queue_claims", []),
        "worktree_refs": state.get("worktree_refs", []),
        "phase_artifacts": state.get("phase_artifacts", []),
    }


QUEUE_STATUSES = ("queued", "claimed", "running", "blocked", "done", "escalated", "released", "abandoned")
QUEUE_ACTIVE_STATUSES = {"claimed", "running"}
QUEUE_FINAL_STATUSES = {"done", "escalated", "abandoned"}


def default_queue_path(workspace: Path) -> Path:
    return workspace / ".adlc" / "work_queue.json"


def resolve_queue_path(raw_path: str | None, workspace: Path) -> Path:
    if not raw_path:
        return default_queue_path(workspace).resolve()
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    cwd_path = (Path.cwd() / path).resolve()
    if cwd_path.exists():
        return cwd_path
    return (workspace / path).resolve()


def load_work_queue(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"work queue not found: {path}")
    errors = validate_artifact(resolve_schema("work-queue"), path)
    if errors:
        raise ValueError("work queue failed schema validation: " + "; ".join(errors))
    queue = read_json(path)
    if not isinstance(queue, dict):
        raise ValueError(f"work queue must be a JSON object: {path}")
    return queue


def save_work_queue(path: Path, queue: Dict[str, Any]) -> None:
    queue["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("work-queue"), path)
    if errors:
        raise ValueError("work queue failed schema validation after write: " + "; ".join(errors))


def queue_task_key(task: Dict[str, Any]) -> Tuple[int, str, str]:
    priority = task.get("priority")
    if not isinstance(priority, int):
        priority = 1000
    return priority, str(task.get("created_at") or ""), str(task.get("task_id") or "")


def sorted_queue_tasks(queue: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted((task for task in queue.get("tasks", []) if isinstance(task, dict)), key=queue_task_key)


def find_queue_task(queue: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in queue.get("tasks", []):
        if isinstance(task, dict) and task.get("task_id") == task_id:
            return task
    raise ValueError(f"task not found in work queue: {task_id}")


def normalize_owned_path(raw_path: str) -> str:
    normalized = raw_path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized or "."


def path_owner_entries(task: Dict[str, Any]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    raw_entries = task.get("expected_paths", [])
    if not isinstance(raw_entries, list):
        return entries
    for raw in raw_entries:
        if isinstance(raw, str) and raw.strip():
            path = normalize_owned_path(raw)
            kind = "glob" if any(char in path for char in "*?[") else "file"
            entries.append({"path": path, "kind": kind})
        elif isinstance(raw, dict) and isinstance(raw.get("path"), str) and raw["path"].strip():
            path = normalize_owned_path(raw["path"])
            kind = str(raw.get("kind") or "file")
            if kind not in {"file", "directory", "glob"}:
                kind = "glob" if any(char in path for char in "*?[") else "file"
            entry = {"path": path, "kind": kind}
            if isinstance(raw.get("reason"), str) and raw["reason"].strip():
                entry["reason"] = raw["reason"].strip()
            entries.append(entry)
    return entries


def owner_is_directory(owner: Dict[str, str]) -> bool:
    return owner.get("kind") == "directory"


def path_owners_overlap(left: Dict[str, str], right: Dict[str, str]) -> bool:
    left_path = normalize_owned_path(left["path"])
    right_path = normalize_owned_path(right["path"])
    left_kind = left.get("kind", "file")
    right_kind = right.get("kind", "file")

    if left_kind == "glob" or right_kind == "glob":
        return (
            fnmatch.fnmatch(right_path, left_path)
            or fnmatch.fnmatch(left_path, right_path)
            or fnmatch.fnmatch(right_path + "/", left_path)
            or fnmatch.fnmatch(left_path + "/", right_path)
        )
    if left_path == right_path:
        return True
    if owner_is_directory(left):
        return right_path.startswith(left_path + "/")
    if owner_is_directory(right):
        return left_path.startswith(right_path + "/")
    return False


def queue_overlap_issues(queue: Dict[str, Any], candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidate_paths = path_owner_entries(candidate)
    issues: List[Dict[str, Any]] = []
    if not candidate_paths:
        return issues
    for task in sorted_queue_tasks(queue):
        if task.get("task_id") == candidate.get("task_id"):
            continue
        if task.get("status") not in QUEUE_ACTIVE_STATUSES:
            continue
        for candidate_path in candidate_paths:
            for active_path in path_owner_entries(task):
                if path_owners_overlap(candidate_path, active_path):
                    issues.append(
                        {
                            "rule": "file_overlap",
                            "message": "expected paths overlap an active queue claim",
                            "task_id": candidate.get("task_id"),
                            "conflicting_task_id": task.get("task_id"),
                            "path": candidate_path["path"],
                            "conflicting_path": active_path["path"],
                        }
                    )
    return issues


def git_dirty_status(workspace: Path) -> Dict[str, Any]:
    result = subprocess.run(
        ["git", "-C", str(workspace), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "is_git": False,
            "dirty": True,
            "reason": "not_git_workspace",
            "stderr": result.stderr[-1000:],
        }
    entries = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "is_git": True,
        "dirty": bool(entries),
        "reason": "dirty_checkout" if entries else "clean",
        "entries": entries[:50],
        "truncated": len(entries) > 50,
    }


def optional_workflow_state(workspace: Path, state_arg: str | None) -> Tuple[Path, Dict[str, Any] | None]:
    state_path = resolve_under_workspace(state_arg, workspace, DEFAULT_STATE_PATH)
    if not state_path.exists():
        return state_path, None
    return state_path, ensure_workflow_identity(load_workflow_state(state_path))


def queue_run_identity(queue: Dict[str, Any], task: Dict[str, Any], state: Dict[str, Any] | None) -> Dict[str, Any]:
    identity = workflow_identity_payload(state) if state else None
    if not identity:
        identity = {}
    for key in ("brief_id", "run_id", "session_id"):
        value = task.get(key) or queue.get(key)
        if isinstance(value, str) and value.strip():
            identity.setdefault(key, value)
    return identity


def queue_summary(queue: Dict[str, Any]) -> Dict[str, Any]:
    counts = {status: 0 for status in QUEUE_STATUSES}
    for task in sorted_queue_tasks(queue):
        status = str(task.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": sum(counts.values()),
        "counts": counts,
        "active": counts.get("claimed", 0) + counts.get("running", 0),
        "available": counts.get("queued", 0) + counts.get("released", 0),
        "blocked": counts.get("blocked", 0) + counts.get("escalated", 0),
        "done": counts.get("done", 0),
    }


def queue_status_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = resolve_workspace(args.workspace)
    queue_path = resolve_queue_path(args.queue, workspace)
    queue = load_work_queue(queue_path)
    tasks = sorted_queue_tasks(queue)
    active_claims = [
        {
            "task_id": task.get("task_id"),
            "status": task.get("status"),
            "claim": task.get("claim"),
            "expected_paths": path_owner_entries(task),
            "worktree": task.get("worktree"),
        }
        for task in tasks
        if task.get("status") in QUEUE_ACTIVE_STATUSES
    ]
    return {
        "contract_version": "1.0.0",
        "queue_ref": rel_path(queue_path),
        "queue_id": queue.get("queue_id"),
        "summary": queue_summary(queue),
        "active_claims": active_claims,
        "tasks": tasks,
    }


def claim_id_for(queue: Dict[str, Any], task: Dict[str, Any], agent_id: str, identity: Dict[str, Any]) -> str:
    return "claim:" + stable_hash(
        "|".join(
            [
                str(queue.get("queue_id", "")),
                str(task.get("task_id", "")),
                agent_id,
                str(identity.get("run_id", "")),
                str(identity.get("session_id", "")),
            ]
        )
    )


def queue_mutation_admission(
    args: argparse.Namespace,
    workspace: Path,
    state_path: Path,
    state: Dict[str, Any] | None,
    tool_name: str,
    action: str,
    default_audit_name: str,
) -> Tuple[int, Dict[str, Any]]:
    if not args.tool_registry:
        raise ValueError("--tool-registry is required with --allow-mutation")
    audit_path = cli_input_path(args.audit_trail) if args.audit_trail else state_path.parent / default_audit_name
    return action_admit_payload(
        tool_registry_path=cli_input_path(args.tool_registry),
        tool_name=tool_name,
        action=action,
        phase=(state or {}).get("phase", "code"),
        state_path=state_path if state_path.exists() else None,
        brief_id=(state or {}).get("brief_id"),
        run_id=(state or {}).get("run_id"),
        session_id=(state or {}).get("session_id"),
        allow_mutation=True,
        human_approved=args.human_approved,
        approval_ref=args.approval_ref,
        audit_trail_path=audit_path,
    )


def record_local_side_effect(
    state: Dict[str, Any],
    tool_name: str,
    operation: str,
    task_id: str,
    artifact_ref: str,
    status: str = "completed",
    error: str | None = None,
) -> None:
    now = utc_now()
    side_effect: Dict[str, Any] = {
        "idempotency_key": ":".join(
            [
                str(state.get("brief_id", "UNKNOWN-BRIEF")),
                str(tool_name),
                str(task_id),
                str(operation),
                stable_hash(artifact_ref),
            ]
        ),
        "brief_id": state.get("brief_id"),
        "run_id": state.get("run_id"),
        "session_id": state.get("session_id"),
        "tool_name": tool_name,
        "operation": operation,
        "status": status,
        "artifact_id": task_id,
        "artifact_ref": artifact_ref,
        "timestamp": now,
    }
    if error:
        side_effect["error"] = error
    state.setdefault("side_effects", []).append(side_effect)


def upsert_queue_claim_state(
    state: Dict[str, Any],
    queue: Dict[str, Any],
    queue_path: Path,
    task: Dict[str, Any],
    status: str,
    claim: Dict[str, Any] | None,
    reason: str | None = None,
    next_action: str | None = None,
    evidence_refs: List[str] | None = None,
) -> None:
    now = utc_now()
    claims = [
        item
        for item in state.get("queue_claims", [])
        if not (isinstance(item, dict) and item.get("queue_id") == queue.get("queue_id") and item.get("task_id") == task.get("task_id"))
    ]
    entry: Dict[str, Any] = {
        "queue_id": queue.get("queue_id"),
        "queue_ref": rel_path(queue_path),
        "task_id": task.get("task_id"),
        "brief_id": state.get("brief_id"),
        "run_id": state.get("run_id"),
        "session_id": state.get("session_id"),
        "status": status,
        "expected_paths": path_owner_entries(task),
        "updated_at": now,
    }
    if claim:
        for key in ("claim_id", "agent_id", "worktree_ref"):
            if claim.get(key):
                entry[key] = claim[key]
    if reason:
        entry["reason"] = reason
    if next_action:
        entry["next_action"] = next_action
    if evidence_refs:
        entry["evidence_refs"] = evidence_refs
    claims.append({k: v for k, v in entry.items() if v is not None})
    state["queue_claims"] = claims


def upsert_worktree_state_ref(
    state: Dict[str, Any],
    queue: Dict[str, Any],
    queue_path: Path,
    task_id: str,
    worktree: Dict[str, Any],
) -> None:
    refs = [
        item
        for item in state.get("worktree_refs", [])
        if not (isinstance(item, dict) and item.get("task_id") == task_id and item.get("path") == worktree.get("path"))
    ]
    entry: Dict[str, Any] = {
        "queue_id": queue.get("queue_id"),
        "queue_ref": rel_path(queue_path),
        "task_id": task_id,
        "branch": worktree.get("branch"),
        "path": worktree.get("path"),
        "base_ref": worktree.get("base_ref"),
        "status": worktree.get("status"),
        "dirty": worktree.get("dirty"),
        "cleanup_eligible": worktree.get("cleanup_eligible"),
        "updated_at": worktree.get("updated_at") or utc_now(),
    }
    refs.append({k: v for k, v in entry.items() if v is not None})
    state["worktree_refs"] = refs


def queue_block_payload(reason: str, issues: List[Dict[str, Any]], base: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    payload = {
        **base,
        "status": "blocked",
        "stop_reason": reason,
        "issues": issues,
    }
    return 1, payload


def evidence_args(args: argparse.Namespace) -> List[str]:
    values = getattr(args, "evidence", None) or []
    return [str(value) for value in values if str(value).strip()]


def queue_transition_payload(args: argparse.Namespace, operation: str) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    queue_path = resolve_queue_path(args.queue, workspace)
    queue = load_work_queue(queue_path)
    task = find_queue_task(queue, args.task_id)
    state_path, state = optional_workflow_state(workspace, args.state)
    identity = queue_run_identity(queue, task, state)
    dry_run = args.dry_run or not args.allow_mutation
    now = utc_now()
    agent_id = getattr(args, "agent_id", None) or identity.get("session_id") or os.environ.get("USER") or "adlc-agent"
    evidence = evidence_args(args)
    base: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "dry_run": dry_run,
        "operation": operation,
        "queue_ref": rel_path(queue_path),
        "queue_id": queue.get("queue_id"),
        "task_id": args.task_id,
        "task_status": task.get("status"),
        "run_identity": identity,
    }

    if operation == "claim":
        if task.get("status") != "queued":
            return queue_block_payload(
                "task_not_claimable",
                [{"rule": "task_not_claimable", "message": f"task status is {task.get('status')}"}],
                base,
            )
        dirty = git_dirty_status(workspace)
        if dirty["dirty"]:
            return queue_block_payload(
                dirty.get("reason", "dirty_checkout"),
                [{"rule": dirty.get("reason", "dirty_checkout"), "message": "workspace is not clean", "git": dirty}],
                {**base, "git": dirty},
            )
        overlaps = queue_overlap_issues(queue, task)
        if overlaps:
            return queue_block_payload("file_overlap", overlaps, {**base, "git": dirty})
        claim = {
            "claim_id": claim_id_for(queue, task, str(agent_id), identity),
            "agent_id": str(agent_id),
            "status": "claimed",
            "claimed_at": now,
            "updated_at": now,
            "expected_paths": path_owner_entries(task),
        }
        for key in ("brief_id", "run_id", "session_id"):
            if identity.get(key):
                claim[key] = identity[key]
        if getattr(args, "worktree_ref", None):
            claim["worktree_ref"] = args.worktree_ref
        planned_task = {**task, "status": "claimed", "claim": claim, "updated_at": now}
        result = {**base, "status": "pass", "git": dirty, "planned_task": planned_task, "claim": claim, "issues": []}
        if dry_run:
            return 0, result
        admission_exit, admission = queue_mutation_admission(args, workspace, state_path, state, "adlc-queue", "claim_task", "queue_permission_audit.json")
        result["admission"] = admission
        if admission_exit != 0:
            return queue_block_payload(admission.get("stop_reason") or admission["status"], admission.get("issues", []), result)
        task.update(planned_task)
        save_work_queue(queue_path, queue)
        if state:
            upsert_queue_claim_state(state, queue, queue_path, task, "claimed", claim)
            record_local_side_effect(state, "adlc-queue", "claim_task", args.task_id, rel_path(queue_path))
            state["updated_at"] = utc_now()
            save_workflow_state(state_path, state)
            result["state"] = state
        result["status"] = "committed"
        result["task"] = task
        return 0, result

    if operation == "release":
        if task.get("status") not in QUEUE_ACTIVE_STATUSES:
            return queue_block_payload(
                "task_not_releasable",
                [{"rule": "task_not_releasable", "message": f"task status is {task.get('status')}"}],
                base,
            )
        planned_task = dict(task)
        planned_task["status"] = "queued"
        planned_task["updated_at"] = now
        planned_task.pop("claim", None)
        result = {**base, "status": "pass", "planned_task": planned_task, "issues": []}
        new_state_status = "released"
    elif operation == "complete":
        requires_evidence = bool(task.get("evidence_required")) or bool(task.get("verifier_refs"))
        existing_evidence = [str(value) for value in task.get("evidence_refs", []) if str(value).strip()] if isinstance(task.get("evidence_refs"), list) else []
        if requires_evidence and not evidence and not existing_evidence:
            return queue_block_payload(
                "missing_verifier_evidence",
                [{"rule": "missing_verifier_evidence", "message": "queue-complete requires --evidence for tasks with verifier_refs or evidence_required"}],
                base,
            )
        planned_task = dict(task)
        planned_task["status"] = "done"
        planned_task["updated_at"] = now
        planned_task["evidence_refs"] = sorted(set(existing_evidence + evidence))
        planned_task.pop("claim", None)
        result = {**base, "status": "pass", "planned_task": planned_task, "issues": []}
        new_state_status = "done"
    elif operation in {"block", "escalate"}:
        if not args.reason or not args.next_action:
            return queue_block_payload(
                "missing_reason_or_next_action",
                [{"rule": "missing_reason_or_next_action", "message": f"queue-{operation} requires --reason and --next-action"}],
                base,
            )
        planned_task = dict(task)
        planned_task["status"] = "blocked" if operation == "block" else "escalated"
        planned_task["reason"] = args.reason
        planned_task["next_action"] = args.next_action
        planned_task["updated_at"] = now
        if evidence:
            planned_task["evidence_refs"] = sorted(set([*planned_task.get("evidence_refs", []), *evidence]))
        planned_task.pop("claim", None)
        result = {**base, "status": "pass", "planned_task": planned_task, "issues": []}
        new_state_status = planned_task["status"]
    else:
        raise ValueError(f"unsupported queue operation: {operation}")

    if dry_run:
        return 0, result
    admission_exit, admission = queue_mutation_admission(args, workspace, state_path, state, "adlc-queue", f"{operation}_task", "queue_permission_audit.json")
    result["admission"] = admission
    if admission_exit != 0:
        return queue_block_payload(admission.get("stop_reason") or admission["status"], admission.get("issues", []), result)
    task.clear()
    task.update(planned_task)
    save_work_queue(queue_path, queue)
    if state:
        upsert_queue_claim_state(
            state,
            queue,
            queue_path,
            task,
            new_state_status,
            task.get("claim") if isinstance(task.get("claim"), dict) else None,
            reason=task.get("reason"),
            next_action=task.get("next_action"),
            evidence_refs=task.get("evidence_refs") if isinstance(task.get("evidence_refs"), list) else None,
        )
        record_local_side_effect(state, "adlc-queue", f"{operation}_task", args.task_id, rel_path(queue_path))
        state["updated_at"] = utc_now()
        save_workflow_state(state_path, state)
        result["state"] = state
    result["status"] = "committed"
    result["task"] = task
    return 0, result


def slugify_task_id(task_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id.strip()).strip("-").lower()
    return slug or "task"


def default_worktree_root(workspace: Path) -> Path:
    return workspace.parent / f"{workspace.name}-adlc-worktrees"


def worktree_plan(workspace: Path, task: Dict[str, Any], worktree_root_arg: str | None, worktree_path_arg: str | None, base_ref: str | None) -> Dict[str, Any]:
    task_id = str(task.get("task_id") or "task")
    slug = slugify_task_id(task_id)
    branch = f"adlc/{slug}-{stable_hash(task_id)[:8]}"
    if worktree_path_arg:
        worktree_path = Path(worktree_path_arg)
        if not worktree_path.is_absolute():
            worktree_path = workspace / worktree_path
    else:
        root = Path(worktree_root_arg) if worktree_root_arg else default_worktree_root(workspace)
        if not root.is_absolute():
            root = workspace / root
        worktree_path = root / slug
    return {
        "branch": branch,
        "path": str(worktree_path.resolve()),
        "base_ref": base_ref or "HEAD",
        "status": "planned",
        "updated_at": utc_now(),
    }


def worktree_dirty_status(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "is_git": False, "dirty": False, "reason": "missing_worktree"}
    status = git_dirty_status(path)
    status["exists"] = True
    return status


def worktree_prepare_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    queue_path = resolve_queue_path(args.queue, workspace)
    queue = load_work_queue(queue_path)
    task = find_queue_task(queue, args.task_id)
    state_path, state = optional_workflow_state(workspace, args.state)
    dry_run = args.dry_run or not args.allow_mutation
    dirty = git_dirty_status(workspace)
    plan = worktree_plan(workspace, task, args.worktree_root, args.worktree_path, args.base_ref)
    base = {
        "contract_version": "1.0.0",
        "dry_run": dry_run,
        "operation": "prepare",
        "queue_ref": rel_path(queue_path),
        "queue_id": queue.get("queue_id"),
        "task_id": args.task_id,
        "task_status": task.get("status"),
        "worktree": plan,
        "git": dirty,
    }
    if task.get("status") not in {"queued", "claimed"}:
        return queue_block_payload(
            "task_not_preparable",
            [{"rule": "task_not_preparable", "message": f"task status is {task.get('status')}"}],
            base,
        )
    if dirty["dirty"]:
        return queue_block_payload(
            dirty.get("reason", "dirty_checkout"),
            [{"rule": dirty.get("reason", "dirty_checkout"), "message": "workspace is not clean", "git": dirty}],
            base,
        )
    overlaps = queue_overlap_issues(queue, task)
    if overlaps:
        return queue_block_payload("file_overlap", overlaps, base)
    result = {**base, "status": "pass", "issues": []}
    if dry_run:
        return 0, result
    admission_exit, admission = queue_mutation_admission(args, workspace, state_path, state, "adlc-worktree", "prepare_worktree", "worktree_permission_audit.json")
    result["admission"] = admission
    if admission_exit != 0:
        return queue_block_payload(admission.get("stop_reason") or admission["status"], admission.get("issues", []), result)
    worktree_path = Path(plan["path"])
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "-C", str(workspace), "worktree", "add", "-b", plan["branch"], str(worktree_path), plan["base_ref"]]
    process = subprocess.run(command, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        return queue_block_payload(
            "worktree_prepare_failed",
            [{"rule": "worktree_prepare_failed", "message": process.stderr[-2000:], "command": command}],
            result,
        )
    worktree = {**plan, "status": "active", "dirty": False, "cleanup_eligible": False, "updated_at": utc_now()}
    task["status"] = "running"
    task["updated_at"] = utc_now()
    task["worktree"] = worktree
    claim = task.get("claim") if isinstance(task.get("claim"), dict) else None
    if claim:
        claim["status"] = "running"
        claim["updated_at"] = utc_now()
        claim["worktree_ref"] = worktree["path"]
    save_work_queue(queue_path, queue)
    if state:
        upsert_queue_claim_state(state, queue, queue_path, task, "running", claim)
        upsert_worktree_state_ref(state, queue, queue_path, args.task_id, worktree)
        record_local_side_effect(state, "adlc-worktree", "prepare_worktree", args.task_id, worktree["path"])
        state["updated_at"] = utc_now()
        save_workflow_state(state_path, state)
        result["state"] = state
    result["status"] = "committed"
    result["worktree"] = worktree
    result["task"] = task
    return 0, result


def queue_task_worktree(task: Dict[str, Any], workspace: Path, args: argparse.Namespace) -> Dict[str, Any]:
    if args.worktree_path:
        plan = worktree_plan(workspace, task, args.worktree_root, args.worktree_path, args.base_ref)
        existing = task.get("worktree") if isinstance(task.get("worktree"), dict) else {}
        return {**plan, **existing, "path": plan["path"]}
    if isinstance(task.get("worktree"), dict):
        existing = dict(task["worktree"])
        if isinstance(existing.get("path"), str):
            path = Path(existing["path"])
            if not path.is_absolute():
                existing["path"] = str((workspace / path).resolve())
        return existing
    return worktree_plan(workspace, task, args.worktree_root, None, args.base_ref)


def worktree_status_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = resolve_workspace(args.workspace)
    queue_path = resolve_queue_path(args.queue, workspace) if args.queue else None
    queue = load_work_queue(queue_path) if queue_path and queue_path.exists() else {"queue_id": None, "tasks": []}
    tasks = sorted_queue_tasks(queue)
    if args.task_id:
        tasks = [find_queue_task(queue, args.task_id)]
    worktrees = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if not task.get("worktree") and not args.worktree_path and task.get("status") not in QUEUE_ACTIVE_STATUSES:
            continue
        worktree = queue_task_worktree(task, workspace, args)
        dirty = worktree_dirty_status(Path(worktree["path"]))
        worktrees.append(
            {
                "task_id": task.get("task_id"),
                "queue_id": queue.get("queue_id"),
                "task_status": task.get("status"),
                "worktree": worktree,
                "dirty_state": dirty,
                "cleanup_eligible": dirty.get("exists") and not dirty.get("dirty"),
            }
        )
    return {
        "contract_version": "1.0.0",
        "workspace": str(workspace),
        "queue_ref": rel_path(queue_path) if queue_path else None,
        "queue_id": queue.get("queue_id"),
        "worktrees": worktrees,
        "summary": {
            "total": len(worktrees),
            "dirty": sum(1 for item in worktrees if item["dirty_state"].get("dirty")),
            "cleanup_eligible": sum(1 for item in worktrees if item.get("cleanup_eligible")),
        },
    }


def worktree_cleanup_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    queue_path = resolve_queue_path(args.queue, workspace)
    queue = load_work_queue(queue_path)
    task = find_queue_task(queue, args.task_id)
    state_path, state = optional_workflow_state(workspace, args.state)
    dry_run = args.dry_run or not args.allow_mutation
    worktree = queue_task_worktree(task, workspace, args)
    dirty = worktree_dirty_status(Path(worktree["path"]))
    base = {
        "contract_version": "1.0.0",
        "dry_run": dry_run,
        "operation": "cleanup",
        "queue_ref": rel_path(queue_path),
        "queue_id": queue.get("queue_id"),
        "task_id": args.task_id,
        "worktree": worktree,
        "dirty_state": dirty,
    }
    if dirty.get("dirty") and not args.force:
        return queue_block_payload(
            "dirty_worktree",
            [{"rule": "dirty_worktree", "message": "worktree has uncommitted changes", "git": dirty}],
            base,
        )
    result = {**base, "status": "pass", "issues": []}
    if dry_run:
        return 0, result
    admission_exit, admission = queue_mutation_admission(args, workspace, state_path, state, "adlc-worktree", "cleanup_worktree", "worktree_permission_audit.json")
    result["admission"] = admission
    if admission_exit != 0:
        return queue_block_payload(admission.get("stop_reason") or admission["status"], admission.get("issues", []), result)
    if Path(worktree["path"]).exists():
        command = ["git", "-C", str(workspace), "worktree", "remove"]
        if args.force:
            command.append("--force")
        command.append(worktree["path"])
        process = subprocess.run(command, text=True, capture_output=True, check=False)
        if process.returncode != 0:
            return queue_block_payload(
                "worktree_cleanup_failed",
                [{"rule": "worktree_cleanup_failed", "message": process.stderr[-2000:], "command": command}],
                result,
            )
    cleaned = {**worktree, "status": "cleaned", "dirty": False, "cleanup_eligible": False, "updated_at": utc_now()}
    task["worktree"] = cleaned
    task["updated_at"] = utc_now()
    save_work_queue(queue_path, queue)
    if state:
        upsert_worktree_state_ref(state, queue, queue_path, args.task_id, cleaned)
        record_local_side_effect(state, "adlc-worktree", "cleanup_worktree", args.task_id, cleaned["path"])
        state["updated_at"] = utc_now()
        save_workflow_state(state_path, state)
        result["state"] = state
    result["status"] = "committed"
    result["worktree"] = cleaned
    result["task"] = task
    return 0, result


def parse_frontmatter_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            return [part.strip().strip("'\"") for part in value[1:-1].split(",") if part.strip()]
    return value


def parse_markdown_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 4)
    if end == -1:
        return {}, raw
    parsed: Dict[str, Any] = {}
    lines = raw[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            parsed[key] = parse_frontmatter_scalar(raw_value)
            continue
        items: List[Any] = []
        mapping: Dict[str, Any] = {}
        while index < len(lines) and lines[index].startswith("  "):
            child = lines[index].strip()
            index += 1
            if child.startswith("- "):
                items.append(parse_frontmatter_scalar(child[2:]))
            elif ":" in child:
                child_key, child_value = child.split(":", 1)
                mapping[child_key.strip()] = parse_frontmatter_scalar(child_value)
        parsed[key] = items if items else mapping
    return parsed, raw[end + 5 :]


def markdown_summary(body: str, max_chars: int = 280) -> str:
    lines: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        lines.append(line)
        if sum(len(item) for item in lines) >= max_chars:
            break
    summary = " ".join(lines)
    return summary[:max_chars].rstrip()


def graph_report_payload(workspace: Path) -> Dict[str, Any]:
    report_path = workspace / "graphify-out" / "GRAPH_REPORT.md"
    payload: Dict[str, Any] = {
        "present": report_path.is_file(),
        "report": rel_path(report_path) if report_path.is_file() else None,
        "built_from_commit": None,
    }
    if not report_path.is_file():
        return payload
    for line in report_path.read_text(encoding="utf-8").splitlines():
        match = re.search(r"Built from commit:\s*`?([0-9a-fA-F]+)`?", line)
        if match:
            payload["built_from_commit"] = match.group(1)
            break
    return payload


def learning_entry_refs(
    workspace: Path,
    terms: Iterable[str],
    max_refs: int,
) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
    solutions_dir = workspace / "docs" / "solutions"
    no_op_reasons: List[str] = []
    store_payload = {
        "path": rel_path(solutions_dir),
        "present": solutions_dir.is_dir(),
        "entries": 0,
        "valid_refs": 0,
    }
    if not solutions_dir.is_dir():
        no_op_reasons.append("docs/solutions not found")
        return [], no_op_reasons, store_payload

    entries = [
        path
        for path in sorted(solutions_dir.glob("*.md"))
        if path.name not in {"README.md", "_template.md"} and path.is_file()
    ]
    store_payload["entries"] = len(entries)
    if not entries:
        no_op_reasons.append("docs/solutions contains no learning entries")
        return [], no_op_reasons, store_payload

    normalized_terms = {term.lower() for term in terms if term and len(term) >= 3}
    refs = []
    for path in entries:
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = parse_markdown_frontmatter(raw)
        title = str(frontmatter.get("title") or path.stem)
        tags = frontmatter.get("tags") if isinstance(frontmatter.get("tags"), list) else []
        module = str(frontmatter.get("module") or "")
        haystack = " ".join([title, module, " ".join(str(tag) for tag in tags), body[:600]]).lower()
        score = sum(1 for term in normalized_terms if term in haystack)
        redaction = frontmatter.get("redaction_review")
        refs.append(
            {
                "id": f"learning:{path.stem}",
                "path": rel_path(path),
                "title": title,
                "track": frontmatter.get("track"),
                "adlc_domain": frontmatter.get("adlc_domain"),
                "problem_type": frontmatter.get("problem_type"),
                "module": module,
                "severity": frontmatter.get("severity"),
                "tags": tags,
                "related_tasks": frontmatter.get("related_tasks", []),
                "source_evidence": frontmatter.get("source_evidence", []),
                "verifier": frontmatter.get("verifier"),
                "stale_conditions": frontmatter.get("stale_conditions", []),
                "redaction_status": redaction.get("status") if isinstance(redaction, dict) else None,
                "summary": markdown_summary(body),
                "relevance_score": score,
            }
        )

    refs.sort(key=lambda item: (-int(item.get("relevance_score", 0)), item["path"]))
    refs = refs[:max_refs]
    store_payload["valid_refs"] = len(refs)
    return refs, no_op_reasons, store_payload


def brief_context_refs(brief_path: Path | None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    if brief_path is None:
        return [], [], []
    brief = read_json(brief_path)
    tasks = brief.get("sections", {}).get("8_task_tickets", [])
    task_refs = []
    verifier_refs = []
    terms = [str(brief.get("brief_id", "")), str(brief.get("prd_id", ""))]
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        title = task.get("title")
        objective = task.get("objective")
        terms.extend(str(value) for value in (task_id, title, objective) if value)
        verifier = task.get("verification_spec", {}).get("primary_verifier", {})
        task_refs.append(
            {
                "task_id": task_id,
                "title": title,
                "artifact_type": task.get("artifact_type"),
                "task_classification": task.get("task_classification"),
                "stable_task_identity": task.get("stable_task_identity"),
                "resume_fingerprint": task.get("resume_fingerprint"),
            }
        )
        if verifier:
            verifier_refs.append(
                {
                    "task_id": task_id,
                    "type": verifier.get("type"),
                    "target": verifier.get("target"),
                    "target_files": verifier.get("target_files", []),
                    "expected_failure_mode": verifier.get("expected_failure_mode"),
                }
            )
    return task_refs, verifier_refs, terms


def compound_context_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = resolve_workspace(args.workspace)
    brief_path = Path(args.build_brief) if args.build_brief else None
    if brief_path and not brief_path.is_absolute():
        brief_path = (Path.cwd() / brief_path).resolve()
    if brief_path and not brief_path.is_file():
        raise ValueError(f"build brief not found: {brief_path}")

    input_terms: List[str] = []
    input_payload: Dict[str, Any] = {"provided": bool(args.input), "path": None, "text_hash": None}
    if args.input:
        candidate = Path(args.input)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            input_payload["path"] = rel_path(candidate)
        else:
            text = args.input
        input_payload["text_hash"] = stable_hash(text)
        input_terms.extend(re.findall(r"[A-Za-z0-9_/-]{3,}", text[:4000]))

    task_refs, verifier_refs, brief_terms = brief_context_refs(brief_path)
    input_terms.extend(brief_terms)
    max_refs = max(1, int(args.max_refs or 8))
    learning_refs, no_op_reasons, store_payload = learning_entry_refs(workspace, input_terms, max_refs)
    graph_payload = graph_report_payload(workspace)
    if not graph_payload["present"]:
        no_op_reasons.append("graphify-out/GRAPH_REPORT.md not found")

    return {
        "contract_version": "1.0.0",
        "workspace": str(workspace),
        "input": input_payload,
        "graph": graph_payload,
        "learning_store": store_payload,
        "learning_refs": learning_refs,
        "task_refs": task_refs,
        "verifier_refs": verifier_refs,
        "no_op_reasons": no_op_reasons,
        "summary": {
            "learning_refs": len(learning_refs),
            "task_refs": len(task_refs),
            "verifier_refs": len(verifier_refs),
            "no_ops": len(no_op_reasons),
        },
    }


def command_compound_context(args: argparse.Namespace) -> int:
    try:
        payload = compound_context_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(
            f"compound context: {payload['summary']['learning_refs']} learning refs, "
            f"{payload['summary']['task_refs']} task refs, {payload['summary']['no_ops']} no-ops"
        )
    return 0


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


def is_not_applicable_reason(value: Any) -> bool:
    return isinstance(value, dict) and value.get("applicability") == "not_applicable" and bool(value.get("reason"))


def has_nonempty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def has_nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def task_has_generated_output_surface(task: Dict[str, Any]) -> bool:
    surface = task.get("generated_output_surface")
    if isinstance(surface, bool):
        return surface
    if isinstance(surface, dict):
        return bool(surface.get("active"))
    return False


def slop_gate_issues_for_task(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not task_executable(task) or not task_has_generated_output_surface(task):
        return []

    task_id = task["task_id"]
    gate = task.get("slop_quality_gate")
    if not isinstance(gate, dict):
        return [
            {
                "severity": "blocking",
                "rule": "missing_slop_quality_gate",
                "task_id": task_id,
                "message": "generated_output_surface.active=true requires slop_quality_gate",
            }
        ]

    issues: List[Dict[str, Any]] = []
    if gate.get("applicability") != "required":
        issues.append(
            {
                "severity": "blocking",
                "rule": "slop_quality_gate_not_required",
                "task_id": task_id,
                "message": "generated-output tasks must set slop_quality_gate.applicability=required",
            }
        )

    for field_name in ("mode", "threshold", "metrics", "eval_cases", "failure_action"):
        value = gate.get(field_name)
        missing = value is None or (isinstance(value, (list, dict, str)) and not value)
        if missing:
            issues.append(
                {
                    "severity": "blocking",
                    "rule": f"missing_slop_{field_name}",
                    "task_id": task_id,
                    "message": f"generated-output slop gate is missing {field_name}",
                }
            )
        elif field_name == "metrics":
            for index, metric in enumerate(value):
                if not (
                    isinstance(metric, dict)
                    and isinstance(metric.get("metric_type"), str)
                    and metric.get("metric_type")
                    and isinstance(metric.get("validator_ref"), str)
                    and metric.get("validator_ref")
                ):
                    issues.append(
                        {
                            "severity": "blocking",
                            "rule": "missing_slop_metric_validator",
                            "task_id": task_id,
                            "message": f"generated-output metric {index} must name metric_type and validator_ref",
                        }
                    )
    return issues


def productionization_gate_issues_for_task(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not task_executable(task):
        return []

    task_id = task["task_id"]
    gate = task.get("productionization_gate")
    if gate is None or is_not_applicable_reason(gate):
        return []
    if not isinstance(gate, dict):
        return [
            {
                "severity": "blocking",
                "rule": "invalid_productionization_gate",
                "task_id": task_id,
                "message": "productionization_gate must be an object or not_applicable reason",
            }
        ]
    if gate.get("coverage_state") != "production_ready":
        return []

    issues: List[Dict[str, Any]] = []
    interface_contract = task.get("implementation_interface_contract")
    if not isinstance(interface_contract, dict) or is_not_applicable_reason(interface_contract):
        issues.append(
            {
                "severity": "blocking",
                "rule": "missing_implementation_interface_contract",
                "task_id": task_id,
                "message": "production_ready claims require an implementation_interface_contract",
            }
        )

    required_lists = {
        "validation_evidence": "missing_productionization_validation_evidence",
        "no_overclaim": "missing_productionization_no_overclaim",
        "reliability_failure_modes": "missing_productionization_reliability_failure_modes",
    }
    for field_name, rule in required_lists.items():
        if not has_nonempty_list(gate.get(field_name)):
            issues.append(
                {
                    "severity": "blocking",
                    "rule": rule,
                    "task_id": task_id,
                    "message": f"production_ready gate is missing {field_name}",
                }
            )

    operational = gate.get("operational_readiness")
    if not isinstance(operational, dict):
        issues.append(
            {
                "severity": "blocking",
                "rule": "missing_productionization_operational_readiness",
                "task_id": task_id,
                "message": "production_ready gate requires operational_readiness with owner, rollback path, and runbook or observability refs",
            }
        )
    else:
        missing_operational = []
        for field_name in ("owner", "rollback_path"):
            if not has_nonempty_value(operational.get(field_name)):
                missing_operational.append(field_name)
        if not any(has_nonempty_list(operational.get(field_name)) for field_name in ("runbook_refs", "alerting_refs", "dashboard_refs", "slo_refs")):
            missing_operational.append("runbook_or_observability_refs")
        if missing_operational:
            issues.append(
                {
                    "severity": "blocking",
                    "rule": "missing_productionization_operational_readiness",
                    "task_id": task_id,
                    "message": "production_ready gate operational_readiness is missing " + ", ".join(missing_operational),
                }
            )

    security_privacy = gate.get("security_privacy")
    if not isinstance(security_privacy, dict) or not has_nonempty_value(security_privacy.get("redaction_posture")):
        issues.append(
            {
                "severity": "blocking",
                "rule": "missing_productionization_security_privacy",
                "task_id": task_id,
                "message": "production_ready gate requires security_privacy.redaction_posture",
            }
        )

    if issues:
        issues.append(
            {
                "severity": "blocking",
                "rule": "overclaimed_production_ready",
                "task_id": task_id,
                "message": "production_ready coverage_state is overclaimed until interface, evidence, rollback, reliability, security/privacy, and no-overclaim data are present",
            }
        )

    return issues


def slop_gate_payload(brief_path: Path) -> Dict[str, Any]:
    errors = validate_artifact(resolve_schema("build-brief"), brief_path)
    if errors:
        raise ValueError("build brief failed schema validation: " + "; ".join(errors))

    brief = read_json(brief_path)
    tasks = brief.get("sections", {}).get("8_task_tickets", [])
    issues: List[Dict[str, Any]] = []
    task_results = []
    for task in tasks:
        task_issues = slop_gate_issues_for_task(task)
        issues.extend(task_issues)
        gate = task.get("slop_quality_gate")
        if task_has_generated_output_surface(task):
            result = "blocked" if task_issues else "passed"
        elif isinstance(gate, dict) and gate.get("applicability") == "required":
            result = "passed"
        elif isinstance(gate, dict):
            result = "skipped"
        else:
            result = "not_applicable"
        task_results.append(
            {
                "task_id": task["task_id"],
                "generated_output_surface": task_has_generated_output_surface(task),
                "result": result,
                "slop_quality_gate": gate,
                "issues": task_issues,
            }
        )

    return {
        "status": "blocked" if issues else "pass",
        "build_brief_id": brief.get("brief_id"),
        "issues": issues,
        "tasks": task_results,
        "summary": {
            "tasks": len(tasks),
            "generated_output_surfaces": sum(1 for task in tasks if task_has_generated_output_surface(task)),
            "issues": len(issues),
        },
    }


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
                    if is_not_applicable_reason(value):
                        missing = False
                    elif field_name == "compatibility_contract":
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

            issues.extend(slop_gate_issues_for_task(task))
            issues.extend(productionization_gate_issues_for_task(task))

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
            "stable_task_identity": task.get("stable_task_identity"),
            "resume_fingerprint": task.get("resume_fingerprint"),
            "task_classification": task.get("task_classification"),
            "executable": task_executable(task),
            "blocks_implementation": task_blocks_implementation(task),
            "area": meta.get("area") or meta.get("area_label") or "unknown",
            "phase": index,
            "phase_label": meta.get("phase_label"),
            "target_project": meta.get("target_project"),
            "labels": meta.get("labels", []),
            "external_refs": meta.get("external_refs", []),
            "loop_contract_path": meta.get("loop_contract_path"),
            "loop_action_path": meta.get("loop_action_path"),
            "loop_maturity_report_path": meta.get("loop_maturity_report_path"),
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
            "construct_map_refs": task.get("construct_map_refs", []),
            "paved_road_refs": task.get("paved_road_refs", []),
            "intent_contract_refs": task.get("intent_contract_refs", []),
            "production_invariant_coverage": task.get("production_invariant_coverage", []),
            "evidence_responsibilities": task.get("evidence_responsibilities", []),
            "definition_of_done": task.get("definition_of_done", []),
            "failure_modes": task.get("failure_modes", []),
        }
        if task.get("implementation_interface_contract") is not None:
            artifact["implementation_interface_contract"] = task["implementation_interface_contract"]
        if task.get("productionization_gate") is not None:
            artifact["productionization_gate"] = task["productionization_gate"]
        if task.get("slop_quality_gate") is not None:
            artifact["slop_quality_gate"] = task["slop_quality_gate"]
        for optional_key in ("loop_contract_path", "loop_action_path", "loop_maturity_report_path"):
            if artifact.get(optional_key) is None:
                artifact.pop(optional_key, None)
        artifacts.append(artifact)

    dependency_links = []
    task_ids = {task["task_id"] for task in tasks}
    resolvable_dependency_ids = task_ids | terminal_side_effect_dependency_ids(state, target, brief_id)
    for task in tasks:
        for dependency in task.get("dependencies", []):
            if dependency not in resolvable_dependency_ids:
                raise ValueError(f"unresolved_dependency_alias: {task['task_id']} depends on {dependency}")
            dependency_links.append({"from": dependency, "to": task["task_id"], "type": "blocks"})

    result = {
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
    identity = workflow_identity_payload(state)
    if identity:
        result["run_identity"] = identity
    return result


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


def load_existing_work_items(path_arg: str | None, target: str) -> Dict[str, Dict[str, Any]]:
    if not path_arg:
        return {}
    path = cli_input_path(path_arg)
    payload = read_json(path)
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = (
            payload.get("work_items")
            or payload.get("artifacts")
            or payload.get("items")
            or payload.get("issues")
            or payload.get("tickets")
            or []
        )
    else:
        items = []

    by_external_id: Dict[str, Dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_target = item.get("target")
        if isinstance(item_target, str) and item_target != target:
            continue
        external_id = first_nonempty_text(item, ("external_id", "idempotency_key", "adlc_external_id"))
        if not external_id:
            continue
        by_external_id[external_id] = item
    return by_external_id


def state_work_item_links_by_external_id(state: Dict[str, Any] | None, target: str) -> Dict[str, Dict[str, Any]]:
    if not state:
        return {}
    links: Dict[str, Dict[str, Any]] = {}
    for item in state.get("work_item_links", []):
        if not isinstance(item, dict) or item.get("target") != target:
            continue
        external_id = item.get("external_id")
        if isinstance(external_id, str) and external_id.strip():
            links[external_id.strip()] = item
    return links


def emitted_work_items_by_external_id(state: Dict[str, Any] | None, target: str) -> Dict[str, Dict[str, Any]]:
    if not state:
        return {}
    tool_name = f"{target}-work-item-emitter"
    emitted: Dict[str, Dict[str, Any]] = {}
    for item in state.get("side_effects", []):
        if not isinstance(item, dict) or item.get("tool_name") != tool_name:
            continue
        if item.get("operation") != "upsert_artifact" or item.get("status") not in {"completed", "deduplicated"}:
            continue
        external_id = item.get("idempotency_key")
        if isinstance(external_id, str) and external_id.strip():
            emitted[external_id.strip()] = item
    return emitted


def work_item_from_artifact(artifact: Dict[str, Any], target: str, build_brief_id: str) -> Dict[str, Any]:
    external_id = artifact["idempotency_key"]
    item = {
        "external_id": external_id,
        "idempotency_key": external_id,
        "build_brief_id": build_brief_id,
        "task_id": artifact["id"],
        "title": artifact.get("title") or artifact["id"],
        "url": artifact.get("url") or f"dry-run://{target}/{build_brief_id}/{artifact['id']}",
        "artifact_type": artifact.get("artifact_type", "work_item"),
        "labels": artifact.get("labels", []),
    }
    if artifact.get("artifact_id"):
        item["artifact_id"] = artifact["artifact_id"]
    if artifact.get("artifact_ref"):
        item["artifact_ref"] = artifact["artifact_ref"]
    return item


def verifier_results_from_state(state: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not state:
        return []
    results: List[Dict[str, Any]] = []
    for item in state.get("task_fingerprints", []):
        if not isinstance(item, dict):
            continue
        verifier = item.get("primary_verifier")
        if not isinstance(verifier, str) or not verifier.strip():
            continue
        post_status = item.get("post_change_status")
        if post_status == "passed":
            status = "pass"
        elif post_status == "failed" or item.get("status") == "failed":
            status = "fail"
        else:
            status = "not_run"
        evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []
        if not evidence:
            evidence = [f"workflow-state task_fingerprints:{item.get('task_id', 'unknown')}"]
        results.append(
            {
                "name": verifier,
                "status": status,
                "summary": str(item.get("status") or status),
                "evidence_refs": [str(value) for value in evidence if str(value).strip()],
            }
        )
    return results


def status_update_from_state(
    state: Dict[str, Any] | None,
    state_path: Path | None,
    build_brief_path: Path | None = None,
) -> Dict[str, Any]:
    now = utc_now()
    if not state:
        refs = [rel_path(build_brief_path)] if build_brief_path else ["adlc:sync-work-item"]
        return {
            "status": "planned",
            "phase": "pr_prep",
            "evidence_refs": refs,
            "next_action": "review emitted work item payload",
            "updated_at": now,
        }

    status = str(state.get("status") or "planned")
    if status == "awaiting_approval":
        sync_status = "needs_human"
    elif status in {"planned", "executing", "waiting_on_external", "completed", "failed"}:
        sync_status = status
    else:
        sync_status = "planned"
    evidence_refs = []
    if state_path:
        evidence_refs.append(rel_path(state_path))
    if build_brief_path:
        evidence_refs.append(rel_path(build_brief_path))
    if not evidence_refs:
        evidence_refs.append("adlc:workflow-state")

    blockers = []
    stop_reason = state.get("stop_reason")
    if isinstance(stop_reason, str) and stop_reason.strip():
        blockers.append(
            {
                "code": stop_reason,
                "summary": f"ADLC run is stopped on {stop_reason}",
                "evidence_refs": evidence_refs,
            }
        )

    next_action = state.get("checkpoint", {}).get("next_action")
    if isinstance(next_action, dict):
        next_action_text = str(next_action.get("phase") or next_action.get("status") or "resume workflow")
    elif isinstance(next_action, str) and next_action.strip():
        next_action_text = next_action
    elif state.get("status") == "completed":
        next_action_text = "human review final evidence"
    else:
        next_action_text = f"continue ADLC phase {state.get('phase', 'unknown')}"

    update = {
        "status": sync_status,
        "phase": str(state.get("phase") or "pr_prep"),
        "blockers": blockers,
        "verifier_results": verifier_results_from_state(state),
        "next_action": next_action_text,
        "evidence_refs": evidence_refs,
        "updated_at": now,
    }
    if isinstance(stop_reason, str) and stop_reason.strip():
        update["stop_reason"] = stop_reason
    return update


def normalize_sync_update(update: Dict[str, Any], external_id: str, run_identity: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(update)
    normalized.setdefault("updated_at", utc_now())
    normalized.setdefault("blockers", [])
    normalized.setdefault("verifier_results", [])
    normalized.setdefault("evidence_refs", ["adlc:sync-work-item"])
    normalized.setdefault("next_action", "review ADLC sync state")
    normalized.setdefault("phase", "pr_prep")
    normalized.setdefault("status", "planned")
    if "update_id" not in normalized:
        normalized["update_id"] = "sync-update-" + stable_hash(
            "|".join(
                [
                    external_id,
                    str(run_identity.get("brief_id", "")),
                    str(run_identity.get("run_id", "")),
                    str(run_identity.get("session_id", "")),
                    str(normalized.get("phase", "")),
                    str(normalized.get("status", "")),
                    json.dumps(normalized.get("evidence_refs", []), sort_keys=True),
                    str(normalized.get("sequence", "")),
                ]
            )
        )
    return normalized


def sync_item_from_payload(payload: Dict[str, Any], state: Dict[str, Any] | None) -> Dict[str, Any]:
    target = payload["target"]
    work_item = dict(payload["work_item"])
    run_identity = dict(payload["run_identity"])
    if state:
        identity = workflow_identity_payload(state) or {}
        for key in ("brief_id", "run_id", "session_id", "resume_count", "attempt"):
            if key in identity:
                run_identity.setdefault(key, identity[key])
    status_update = normalize_sync_update(payload["status_update"], work_item["external_id"], run_identity)
    return {
        "target": target,
        "work_item": work_item,
        "run_identity": run_identity,
        "status_update": status_update,
    }


def sync_items_from_build_brief(
    brief_path: Path,
    target: str,
    state: Dict[str, Any] | None,
    state_path: Path | None,
) -> List[Dict[str, Any]]:
    payload = normalized_work_item_payload(brief_path, target, state)
    run_identity = workflow_identity_payload(state) if state else None
    if not run_identity:
        run_identity = {
            "brief_id": payload["build_brief_id"],
            "run_id": new_run_id(),
            "session_id": new_session_id(),
            "resume_count": 0,
            "attempt": 1,
        }
    status_update = status_update_from_state(state, state_path, brief_path)
    items = []
    for artifact in payload.get("artifacts", []):
        work_item = work_item_from_artifact(artifact, target, payload["build_brief_id"])
        item_update = normalize_sync_update(dict(status_update), work_item["external_id"], run_identity)
        generated = {
            "contract_version": "1.0.0",
            "target": target,
            "work_item": work_item,
            "run_identity": run_identity,
            "status_update": item_update,
        }
        errors = validate_artifact_payload(resolve_schema("work-item-sync"), generated)
        if errors:
            raise ValueError("generated work item sync failed schema validation: " + "; ".join(errors))
        items.append(
            {
                "target": target,
                "work_item": work_item,
                "run_identity": run_identity,
                "status_update": item_update,
            }
        )
    return items


def existing_work_item_for(
    external_id: str,
    state_links: Dict[str, Dict[str, Any]],
    emitted_items: Dict[str, Dict[str, Any]],
    existing_items: Dict[str, Dict[str, Any]],
) -> Tuple[str | None, Dict[str, Any] | None]:
    if external_id in state_links:
        return "state_work_item_links", state_links[external_id]
    if external_id in emitted_items:
        return "side_effects", emitted_items[external_id]
    if external_id in existing_items:
        return "existing_work_items", existing_items[external_id]
    return None, None


def operation_for_sync_item(
    item: Dict[str, Any],
    state_links: Dict[str, Dict[str, Any]],
    emitted_items: Dict[str, Dict[str, Any]],
    existing_items: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    target = item["target"]
    work_item = item["work_item"]
    run_identity = item["run_identity"]
    status_update = item["status_update"]
    external_id = work_item["external_id"]
    source, existing = existing_work_item_for(external_id, state_links, emitted_items, existing_items)
    operation = "append" if existing else "create"
    reason = f"matched_{source}" if existing else "no_existing_external_id"
    if existing:
        for key in ("artifact_id", "artifact_ref"):
            value = first_nonempty_text(existing, (key, "id", "key", "identifier", "number", "url"))
            if value and key not in work_item:
                work_item[key] = value
    sync_idempotency_key = f"{external_id}:sync:{status_update['update_id']}"
    return {
        "target": target,
        "operation": operation,
        "reason": reason,
        "external_id": external_id,
        "idempotency_key": work_item["idempotency_key"],
        "sync_idempotency_key": sync_idempotency_key,
        "work_item": work_item,
        "run_identity": run_identity,
        "status_update": status_update,
        "existing_work_item": existing,
    }


def sync_summary(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for operation in operations:
        key = operation["operation"]
        counts[key] = counts.get(key, 0) + 1
    return {
        "total": len(operations),
        "operations": counts,
    }


def record_sync_side_effects(
    state: Dict[str, Any],
    target: str,
    operations: List[Dict[str, Any]],
    status: str,
    provider_result: Dict[str, Any] | None = None,
) -> None:
    provider_by_key = provider_results_by_idempotency_key(provider_result)
    existing_terminal = {
        item.get("idempotency_key")
        for item in state.get("side_effects", [])
        if item.get("status") in {"completed", "deduplicated"}
    }
    links_by_external_id = state_work_item_links_by_external_id(state, target)
    now = utc_now()
    for operation in operations:
        sync_key = operation["sync_idempotency_key"]
        provider_item = provider_by_key.get(sync_key)
        side_effect_status = "deduplicated" if sync_key in existing_terminal else normalized_side_effect_status(
            provider_item.get("status") if provider_item else None,
            status,
        )
        artifact_id = first_nonempty_text(
            provider_item,
            ("artifact_id", "key", "identifier", "number", "id"),
        ) or operation["work_item"].get("artifact_id") or operation["work_item"].get("task_id") or operation["external_id"]
        artifact_ref = first_nonempty_text(
            provider_item,
            ("artifact_ref", "url", "html_url", "web_url"),
        ) or operation["work_item"].get("artifact_ref") or operation["work_item"].get("url")
        state.setdefault("side_effects", []).append(
            {
                "idempotency_key": sync_key,
                "brief_id": state.get("brief_id"),
                "run_id": state.get("run_id"),
                "session_id": state.get("session_id"),
                "tool_name": f"{target}-work-item-sync",
                "operation": f"{operation['operation']}_work_item_status",
                "status": side_effect_status,
                "artifact_id": artifact_id,
                "artifact_ref": artifact_ref,
                "timestamp": now,
                **({"error": provider_item.get("error")} if provider_item and provider_item.get("error") else {}),
            }
        )
        link_status = {
            "create": "created",
            "update": "updated",
            "append": "appended",
            "noop": "deduplicated",
            "escalate": "blocked",
            "find": "deduplicated",
        }.get(operation["operation"], "updated")
        if side_effect_status == "failed":
            link_status = "failed"
        link = {
            "target": target,
            "external_id": operation["external_id"],
            "idempotency_key": operation["idempotency_key"],
            "brief_id": state.get("brief_id"),
            "run_id": state.get("run_id"),
            "session_id": state.get("session_id"),
            "build_brief_id": operation["work_item"].get("build_brief_id"),
            "task_id": operation["work_item"].get("task_id"),
            "artifact_id": artifact_id,
            "artifact_ref": artifact_ref,
            "title": operation["work_item"].get("title"),
            "operation": operation["operation"],
            "status": link_status,
            "last_sync_idempotency_key": sync_key,
            "status_update": operation["status_update"],
            "evidence_refs": operation["status_update"].get("evidence_refs", []),
            "updated_at": now,
        }
        links_by_external_id[operation["external_id"]] = {k: v for k, v in link.items() if v is not None}
    state["work_item_links"] = list(links_by_external_id.values())


def sync_work_item_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if not args.work_item and not args.build_brief:
        raise ValueError("one of --work-item or --build-brief is required")
    if args.work_item and args.build_brief:
        raise ValueError("--work-item and --build-brief are mutually exclusive")

    workspace = resolve_workspace(args.workspace)
    state_path = resolve_under_workspace(args.state, workspace, DEFAULT_STATE_PATH)
    state = ensure_workflow_identity(load_workflow_state(state_path)) if state_path.exists() else None

    if args.work_item:
        work_item_path = cli_input_path(args.work_item)
        errors = validate_artifact(resolve_schema("work-item-sync"), work_item_path)
        if errors:
            raise ValueError("work item sync failed schema validation: " + "; ".join(errors))
        request_payload = read_json(work_item_path)
        target = request_payload["target"]
        items = [sync_item_from_payload(request_payload, state)]
    else:
        target = args.target
        if target not in WORK_ITEM_TARGETS:
            raise ValueError("--target is required with --build-brief")
        brief_path = cli_input_path(args.build_brief)
        items = sync_items_from_build_brief(brief_path, target, state, state_path if state_path.exists() else None)

    if target not in WORK_ITEM_TARGETS:
        raise ValueError(f"unsupported work-item target: {target}")

    state_links = state_work_item_links_by_external_id(state, target)
    emitted_items = emitted_work_items_by_external_id(state, target)
    existing_items = load_existing_work_items(args.existing_work_items, target)
    operations = [
        operation_for_sync_item(item, state_links, emitted_items, existing_items)
        for item in items
    ]

    dry_run = args.dry_run or not args.allow_mutation
    provider_payload = {
        "contract_version": "1.0.0",
        "target": target,
        "operation": "sync_work_items",
        "operations": operations,
        "summary": sync_summary(operations),
    }
    run_identity = items[0]["run_identity"] if items else workflow_identity_payload(state)
    result: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "dry_run": dry_run,
        "target": target,
        "state_path": rel_path(state_path),
        "run_identity": run_identity,
        "operations": operations,
        "summary": provider_payload["summary"],
        "provider_status": {
            "status": "dry_run_only" if dry_run else "pending",
            "reason": "provider_command_not_supplied" if dry_run and not args.provider_command else "provider_not_called",
        },
    }
    if args.existing_work_items:
        result["existing_work_items_ref"] = rel_path(cli_input_path(args.existing_work_items))
    if dry_run:
        return 0, result

    if not args.provider_command:
        raise ValueError("--provider-command is required with --allow-mutation")
    if not args.tool_registry:
        raise ValueError("--tool-registry is required with --allow-mutation")
    if state is None:
        first_identity = items[0]["run_identity"]
        state = new_workflow_state(
            brief_id=str(first_identity["brief_id"]),
            workspace=workspace,
            phase="pr_prep",
        )
        state["run_id"] = str(first_identity["run_id"])
        state["session_id"] = str(first_identity["session_id"])

    audit_path = cli_input_path(args.audit_trail) if args.audit_trail else workspace / ".adlc" / "work_item_sync_permission_audit.json"
    admission_exit, admission = action_admit_payload(
        tool_registry_path=cli_input_path(args.tool_registry),
        tool_name=f"{target}-work-item-sync",
        action="sync_work_item",
        phase=state.get("phase", "pr_prep"),
        state_path=state_path if state_path.exists() else None,
        brief_id=state.get("brief_id"),
        run_id=state.get("run_id"),
        session_id=state.get("session_id"),
        allow_mutation=True,
        human_approved=args.human_approved,
        approval_ref=args.approval_ref,
        audit_trail_path=audit_path,
    )
    result["admission"] = admission
    if admission_exit != 0:
        result["provider_status"] = {"status": "blocked", "reason": admission.get("stop_reason") or admission["status"]}
        return 1, result

    append_permission_log(
        workspace,
        {
            "tool": f"{target}-work-item-sync",
            "brief_id": state.get("brief_id"),
            "run_id": state.get("run_id"),
            "session_id": state.get("session_id"),
            "provider": args.provider_command,
            "action": "sync_work_item",
            "tier": admission.get("permission_tier"),
            "decision": "approved",
            "decided_by": "action-admit",
            "timestamp": utc_now(),
            "rationale": "ADLC sync-work-item mutation admitted by action-admit.",
        },
    )
    provider_result = invoke_provider_command(args.provider_command, provider_payload, workspace)
    provider_failed = provider_result.get("status") == "failed"
    partial_failure = not provider_failed and provider_result_has_failed_items(provider_result)
    default_side_effect_status = "failed" if provider_failed else "completed"
    record_sync_side_effects(state, target, operations, default_side_effect_status, provider_result)
    if partial_failure:
        provider_result["status"] = "failed"
        provider_result["stop_reason"] = "external_mutation_partial"
    elif provider_failed and provider_result_has_failed_items(provider_result):
        provider_result.setdefault("stop_reason", "external_mutation_partial")
    state["updated_at"] = utc_now()
    state.setdefault("checkpoint", {})["last_work_item_sync"] = {
        "target": target,
        "summary": sync_summary(operations),
        "provider_result": provider_result,
    }
    save_workflow_state(state_path, state)
    result["provider_result"] = provider_result
    result["provider_status"] = {
        "status": provider_result.get("status", "completed"),
        "reason": provider_result.get("stop_reason") or provider_result.get("error"),
    }
    result["state"] = state
    return (1 if provider_failed or partial_failure else 0), result


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
                "brief_id": state.get("brief_id"),
                "run_id": state.get("run_id"),
                "session_id": state.get("session_id"),
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
    state = ensure_workflow_identity(load_workflow_state(state_path)) if state_path.exists() else None

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
        payload["run_identity"] = workflow_identity_payload(state)
        result["run_identity"] = payload["run_identity"]

    append_permission_log(
        workspace,
        {
            "tool": f"{args.target}-work-item-emitter",
            "brief_id": state.get("brief_id"),
            "run_id": state.get("run_id"),
            "session_id": state.get("session_id"),
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


def cli_input_path(raw_path: str, base: Path | None = None) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base or Path.cwd()) / path


def required_test_ids(contract: Dict[str, Any]) -> List[str]:
    selection = contract.get("test_selection", {})
    items = []
    for key in ("mandatory_floor", "required_from_task_signals"):
        value = selection.get(key, [])
        if isinstance(value, list):
            items.extend(value)
    ids = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


def provided_required_test_ids(test_plan: Dict[str, Any]) -> set:
    provided = set()
    for test in test_plan.get("generated_tests", []):
        if not isinstance(test, dict):
            continue
        for key in ("covers_required_tests", "coverage_tags"):
            values = test.get(key, [])
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str):
                        provided.add(value)
    return provided


def executed_required_test_ids(test_results: Dict[str, Any]) -> set:
    executed = set()
    for result in test_results.get("results", []):
        if not isinstance(result, dict):
            continue
        if result.get("exit_code") != 0:
            continue
        required_test_id = result.get("required_test_id")
        if isinstance(required_test_id, str):
            executed.add(required_test_id)
    return executed


def loop_test_selection_payload(
    contract_path: Path,
    test_plan_path: Path,
    test_results_path: Path | None = None,
    require_test_results: bool = False,
) -> Dict[str, Any]:
    contract_errors = validate_artifact(resolve_schema("loop-contract"), contract_path)
    if contract_errors:
        raise ValueError("loop contract failed schema validation: " + "; ".join(contract_errors))
    if test_results_path:
        test_result_errors = validate_artifact(resolve_schema("loop-test-result"), test_results_path)
        if test_result_errors:
            raise ValueError("loop test result failed schema validation: " + "; ".join(test_result_errors))
    contract = read_json(contract_path)
    test_plan = read_json(test_plan_path)
    test_results = read_json(test_results_path) if test_results_path else {}

    required = required_test_ids(contract)
    provided = provided_required_test_ids(test_plan)
    executed = executed_required_test_ids(test_results) if test_results else set()
    missing = [test_id for test_id in required if test_id not in provided]
    missing_executed = [test_id for test_id in required if test_id not in executed] if require_test_results else []
    generated_tests = test_plan.get("generated_tests", [])
    untagged = [
        test.get("test_name") or test.get("test_path") or "<unknown>"
        for test in generated_tests
        if isinstance(test, dict) and not test.get("coverage_tags")
    ]
    issues = []
    if missing:
        issues.append(
            {
                "rule": "missing_required_tests",
                "message": "test plan omits required loop tests",
                "missing_required_tests": missing,
            }
        )
    if missing_executed:
        issues.append(
            {
                "rule": "missing_executed_required_tests",
                "message": "executed test results omit passed evidence for required loop tests",
                "missing_executed_required_tests": missing_executed,
            }
        )
    if untagged:
        issues.append(
            {
                "rule": "missing_coverage_tags",
                "message": "generated tests must carry machine-readable coverage_tags",
                "tests": untagged,
            }
        )

    return {
        "status": "blocked" if issues else "pass",
        "contract_id": contract.get("contract_id"),
        "required_tests": required,
        "provided_required_tests": sorted(provided),
        "executed_required_tests": sorted(executed),
        "missing_required_tests": missing,
        "missing_executed_required_tests": missing_executed,
        "issues": issues,
        "test_plan": rel_path(test_plan_path),
        "test_results": rel_path(test_results_path) if test_results_path else None,
        "require_test_results": require_test_results,
    }


def command_loop_test_selection(args: argparse.Namespace) -> int:
    try:
        test_results_arg = getattr(args, "require_test_results", None)
        require_test_results = bool(test_results_arg)
        test_results_path = args.test_results
        if isinstance(test_results_arg, str):
            test_results_path = test_results_arg
        elif test_results_arg is True and not test_results_path:
            raise ValueError("--require-test-results needs a path or --test-results")
        payload = loop_test_selection_payload(
            cli_input_path(args.loop_contract),
            cli_input_path(args.test_plan),
            cli_input_path(test_results_path) if test_results_path else None,
            require_test_results=require_test_results,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['contract_id']}: loop test selection {payload['status']}")
    return 0 if payload["status"] == "pass" else 1


def clamp_nonnegative_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def token_budget_health_from_ratio(ratio: float, thresholds: Dict[str, Any]) -> Tuple[str, str, str]:
    warn_at = float(thresholds.get("warn_at", 0.5))
    alert_at = float(thresholds.get("alert_at", 0.8))
    hard_stop_at = float(thresholds.get("hard_stop_at", 1.0))
    if ratio >= hard_stop_at:
        return "exhausted", "blocked", "hard_stop_at"
    if ratio >= alert_at:
        return "alert", "wrap_up", "alert_at"
    if ratio >= warn_at:
        return "warning", "warning", "warn_at"
    return "healthy", "proceed", "warn_at"


def worse_budget_health(left: str, right: str) -> str:
    order = {
        "healthy": 0,
        "warning": 1,
        "alert": 2,
        "exhausted": 3,
        "stale": 4,
    }
    return left if order.get(left, 0) >= order.get(right, 0) else right


def decision_for_budget_health(status: str, threshold: str) -> Tuple[str, str, str | None]:
    if status == "stale":
        return "blocked", "artifact_status", "budget_stale"
    if status == "exhausted":
        return "blocked", "hard_stop_at" if threshold != "artifact_status" else "artifact_status", "budget_exhausted"
    if status == "alert":
        return "wrap_up", "alert_at" if threshold != "artifact_status" else "artifact_status", None
    if status == "warning":
        return "warning", "warn_at" if threshold != "artifact_status" else "artifact_status", None
    return "proceed", "warn_at", None


def loop_budget_check_payload(
    token_budget_path: Path,
    estimated_input_tokens: int,
    expected_output_tokens: int,
    phase: str | None = None,
    skill: str | None = None,
) -> Dict[str, Any]:
    errors = validate_artifact(resolve_schema("token-budget"), token_budget_path)
    if errors:
        raise ValueError("token budget failed schema validation: " + "; ".join(errors))

    budget = read_json(token_budget_path)
    estimated_input_tokens = clamp_nonnegative_int(estimated_input_tokens, "--estimated-input-tokens")
    expected_output_tokens = clamp_nonnegative_int(expected_output_tokens, "--expected-output-tokens")
    budget_limit = clamp_nonnegative_int(budget.get("budget_limit"), "budget_limit")
    tokens_used = clamp_nonnegative_int(budget.get("tokens_used"), "tokens_used")
    if budget_limit <= 0:
        raise ValueError("budget_limit must be positive")

    projected_total = tokens_used + estimated_input_tokens + expected_output_tokens
    budget_remaining = max(0, budget_limit - projected_total)
    projected_ratio = projected_total / budget_limit
    ratio_status, ratio_decision, ratio_threshold = token_budget_health_from_ratio(
        projected_ratio,
        budget.get("thresholds", {}),
    )
    artifact_status = budget.get("status")
    budget_health = ratio_status
    threshold = ratio_threshold
    if artifact_status in {"warning", "alert", "exhausted", "stale"}:
        budget_health = worse_budget_health(str(artifact_status), ratio_status)
        if budget_health == artifact_status:
            threshold = "artifact_status"
    decision, threshold, stop_reason = decision_for_budget_health(budget_health, threshold)

    evidence_refs = [rel_path(token_budget_path)]
    status_payload: Dict[str, Any] = {
        "status": budget_health,
        "decision": decision,
        "token_budget_ref": rel_path(token_budget_path),
        "tokens_used": tokens_used,
        "budget_limit": budget_limit,
        "projected_total_tokens": projected_total,
        "budget_remaining": budget_remaining,
        "threshold": threshold,
        "evidence_refs": evidence_refs,
    }
    if phase:
        status_payload["phase"] = phase
    if skill:
        status_payload["skill"] = skill
    if stop_reason:
        status_payload["stop_reason"] = stop_reason

    payload: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "status": decision,
        "budget_status": status_payload,
        "token_budget": rel_path(token_budget_path),
        "estimated_input_tokens": estimated_input_tokens,
        "expected_output_tokens": expected_output_tokens,
        "projected_total": projected_total,
        "budget_remaining": budget_remaining,
        "threshold": threshold,
    }
    if phase:
        payload["phase"] = phase
    if skill:
        payload["skill"] = skill
    if stop_reason:
        payload["stop_reason"] = stop_reason
    return payload


def command_loop_budget_check(args: argparse.Namespace) -> int:
    try:
        payload = loop_budget_check_payload(
            token_budget_path=cli_input_path(args.token_budget),
            estimated_input_tokens=args.estimated_input_tokens,
            expected_output_tokens=args.expected_output_tokens,
            phase=args.phase,
            skill=args.skill,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['token_budget']}: budget {payload['status']}")
    return 1 if payload["status"] == "blocked" else 0


WORKFLOW_TO_LEGACY_PHASE = {
    "triage": "phase_1_brief_prefill",
    "compound_preflight": "phase_1_brief_prefill",
    "research": "phase_0_codebase_research",
    "plan": "phase_1_brief_prefill",
    "plan_review": "phase_2_eval_council",
    "intent_validation": "phase_2_eval_council",
    "scaffold": "phase_3_scaffolding",
    "gen_tests": "phase_4_failing_tests",
    "context_assembly": "phase_5_codegen_context",
    "code": "phase_9_codegen_execution",
    "code_review": "phase_2_eval_council",
    "security": "phase_7_security_review",
    "qa": "phase_11_ci_cd_qa_prep",
    "test_strength": "phase_11_ci_cd_qa_prep",
    "slop_gate": "phase_11_ci_cd_qa_prep",
    "fixer": "phase_9_codegen_execution",
    "pr_prep": "phase_10_jira_confluence_prep",
    "learning_capture": "phase_13_monitoring_feedback",
    "engineer_review": "phase_2_eval_council",
    "done": "phase_13_monitoring_feedback",
    "escalate": "phase_13_monitoring_feedback",
}


def phase_candidates(phase: str) -> List[str]:
    candidates = [phase]
    legacy_phase = WORKFLOW_TO_LEGACY_PHASE.get(phase)
    if legacy_phase:
        candidates.append(legacy_phase)
    for workflow_phase, mapped_legacy_phase in WORKFLOW_TO_LEGACY_PHASE.items():
        if phase == mapped_legacy_phase:
            candidates.append(workflow_phase)
    return list(dict.fromkeys(candidates))


def permission_audit_trail_for_entry(
    session_id: str,
    brief_id: str,
    run_id: str | None,
    entry: Dict[str, Any],
    patterns: Iterable[str],
) -> Dict[str, Any]:
    pattern_list = sorted(set(pattern for pattern in patterns if pattern))
    trail = {
        "session_id": session_id,
        "brief_id": brief_id,
        "entries": [entry],
        "denial_summary": {
            "count": 0 if entry["decision"] == "approved" else 1,
            "patterns": pattern_list,
        },
    }
    if run_id:
        trail["run_id"] = run_id
    return trail


def merged_permission_audit_trail(path: Path, new_trail: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return new_trail
    errors = validate_artifact(resolve_schema("permission-audit-trail"), path)
    if errors:
        raise ValueError("permission audit trail failed schema validation: " + "; ".join(errors))
    existing = read_json(path)
    if existing.get("session_id") != new_trail["session_id"] or existing.get("brief_id") != new_trail["brief_id"]:
        raise ValueError("permission audit trail session_id and brief_id must match appended entry")
    existing_run_id = existing.get("run_id")
    new_run_id = new_trail.get("run_id")
    if existing_run_id and new_run_id and existing_run_id != new_run_id:
        raise ValueError("permission audit trail run_id must match appended entry")
    entries = [*existing.get("entries", []), *new_trail["entries"]]
    patterns = set(existing.get("denial_summary", {}).get("patterns", []))
    patterns.update(new_trail.get("denial_summary", {}).get("patterns", []))
    merged = {
        "session_id": new_trail["session_id"],
        "brief_id": new_trail["brief_id"],
        "entries": entries,
        "denial_summary": {
            "count": sum(1 for entry in entries if entry.get("decision") != "approved"),
            "patterns": sorted(patterns),
        },
    }
    if existing_run_id or new_run_id:
        merged["run_id"] = existing_run_id or new_run_id
    return merged


def write_permission_audit_trail(path: Path, trail: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trail, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("permission-audit-trail"), path)
    if errors:
        raise ValueError("permission audit trail failed schema validation: " + "; ".join(errors))


def action_stop_reason(status: str, issues: List[Dict[str, Any]]) -> str | None:
    if status == "admitted":
        return None
    for issue in issues:
        rule = issue.get("rule")
        if rule in {"budget_exhausted", "budget_stale", "budget_missing"}:
            return str(rule)
    if status == "escalate":
        return "permission_requires_escalation"
    return "permission_denied"


def action_admit_payload(
    tool_registry_path: Path,
    tool_name: str,
    action: str,
    phase: str | None = None,
    state_path: Path | None = None,
    brief_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    allow_mutation: bool = False,
    human_approved: bool = False,
    approval_ref: str | None = None,
    token_budget_path: Path | None = None,
    estimated_input_tokens: int = 0,
    expected_output_tokens: int = 0,
    skill: str | None = None,
    audit_trail_path: Path | None = None,
) -> Tuple[int, Dict[str, Any]]:
    registry_errors = validate_artifact(resolve_schema("tool-registry"), tool_registry_path)
    if registry_errors:
        raise ValueError("tool registry failed schema validation: " + "; ".join(registry_errors))
    registry = read_json(tool_registry_path)
    state = load_workflow_state(state_path) if state_path else {}

    effective_phase = phase or state.get("phase")
    if not isinstance(effective_phase, str) or not effective_phase.strip():
        raise ValueError("--phase is required unless --state provides phase")
    effective_phase = effective_phase.strip()
    effective_brief_id = brief_id or state.get("brief_id") or "UNKNOWN-BRIEF"
    effective_session_id = session_id or state.get("session_id") or "UNKNOWN-SESSION"
    effective_run_id = run_id or state.get("run_id")

    tools = {
        tool.get("name"): tool
        for tool in registry.get("tools", [])
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    }
    tool = tools.get(tool_name)
    phase_options = phase_candidates(effective_phase)
    blocking_issues: List[Dict[str, Any]] = []
    escalation_issues: List[Dict[str, Any]] = []

    if tool is None:
        side_effect_profile = "destructive"
        permission_tier = "requires_escalation"
        allowed_phases: List[str] = []
        blocking_issues.append(
            {
                "rule": "tool_not_registered",
                "message": f"tool is not present in the ADLC tool registry: {tool_name}",
            }
        )
    else:
        side_effect_profile = tool.get("side_effect_profile", "destructive")
        permission_tier = tool.get("permission_tier", "requires_escalation")
        allowed_phases = list(tool.get("available_phases", []))
        if not set(allowed_phases).intersection(phase_options):
            blocking_issues.append(
                {
                    "rule": "phase_not_allowed",
                    "message": f"tool {tool_name} is not available in phase {effective_phase}",
                    "allowed_phases": allowed_phases,
                    "phase_candidates": phase_options,
                }
            )

    if side_effect_profile in {"mutating", "destructive"} and not allow_mutation:
        blocking_issues.append(
            {
                "rule": "mutation_requires_allow_mutation",
                "message": f"{side_effect_profile} tool actions require --allow-mutation",
            }
        )
    if side_effect_profile == "destructive" and not human_approved:
        blocking_issues.append(
            {
                "rule": "destructive_requires_human_approval",
                "message": "destructive tool actions require explicit human approval",
            }
        )
    if permission_tier == "requires_approval" and not human_approved:
        blocking_issues.append(
            {
                "rule": "permission_requires_human_approval",
                "message": f"tool {tool_name} requires explicit human approval",
            }
        )
    if permission_tier == "requires_escalation":
        escalation_issues.append(
            {
                "rule": "permission_requires_escalation",
                "message": f"tool {tool_name} requires human escalation before execution",
            }
        )

    state_status = state.get("status") if isinstance(state, dict) else None
    if state_status == "awaiting_approval" and side_effect_profile != "read_only" and not human_approved:
        blocking_issues.append(
            {
                "rule": "workflow_awaiting_human_approval",
                "message": "workflow state is awaiting human approval",
            }
        )

    budget_check = None
    budget_status = state.get("budget_status") if isinstance(state.get("budget_status"), dict) else None
    if token_budget_path:
        budget_phase = WORKFLOW_TO_LEGACY_PHASE.get(effective_phase, effective_phase)
        budget_check = loop_budget_check_payload(
            token_budget_path,
            estimated_input_tokens,
            expected_output_tokens,
            phase=budget_phase,
            skill=skill,
        )
        budget_status = budget_check["budget_status"]
    if isinstance(budget_status, dict) and budget_status.get("decision") == "blocked":
        blocking_issues.append(
            {
                "rule": budget_status.get("stop_reason", "budget_blocked"),
                "message": "budget guard blocks the tool action before execution",
                "budget_status": budget_status,
            }
        )

    if blocking_issues:
        status = "denied"
    elif escalation_issues:
        status = "escalate"
    else:
        status = "admitted"

    timestamp = utc_now()
    issues = [*blocking_issues, *escalation_issues]
    reason = (
        "tool action admitted by ADLC policy"
        if status == "admitted"
        else "; ".join(issue["rule"] for issue in issues)
    )
    decision = {"admitted": "approved", "denied": "denied", "escalate": "escalated"}[status]
    stop_reason = action_stop_reason(status, issues)
    entry: Dict[str, Any] = {
        "decision_id": "decision:" + stable_hash("|".join([effective_session_id, effective_brief_id, effective_run_id or "", tool_name, action, effective_phase, timestamp])),
        "tool_name": tool_name,
        "action": action,
        "tier": permission_tier,
        "decision": decision,
        "reason": reason,
        "decided_by": "human" if human_approved and decision == "approved" else "policy",
        "timestamp": timestamp,
        "session_id": effective_session_id,
        "brief_id": effective_brief_id,
        "phase": effective_phase,
        "side_effect_profile": side_effect_profile,
        "policy_ref": rel_path(tool_registry_path),
    }
    if effective_run_id:
        entry["run_id"] = effective_run_id
    if stop_reason:
        entry["stop_reason"] = stop_reason
    if approval_ref:
        entry["human_approval_ref"] = approval_ref
    if budget_status and budget_status.get("token_budget_ref"):
        entry["budget_status_ref"] = str(budget_status["token_budget_ref"])

    trail = permission_audit_trail_for_entry(
        effective_session_id,
        effective_brief_id,
        effective_run_id,
        entry,
        (issue["rule"] for issue in issues),
    )
    if audit_trail_path:
        trail = merged_permission_audit_trail(audit_trail_path, trail)
        write_permission_audit_trail(audit_trail_path, trail)

    run_identity = {
        "brief_id": effective_brief_id,
        "session_id": effective_session_id,
    }
    if effective_run_id:
        run_identity["run_id"] = effective_run_id

    payload: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "status": status,
        "run_identity": run_identity,
        "tool_name": tool_name,
        "action": action,
        "phase": effective_phase,
        "phase_candidates": phase_options,
        "side_effect_profile": side_effect_profile,
        "permission_tier": permission_tier,
        "allow_mutation": allow_mutation,
        "human_approved": human_approved,
        "issues": issues,
        "budget_check": budget_check,
        "budget_status": budget_status,
        "stop_reason": stop_reason,
        "audit_trail": trail,
    }
    if audit_trail_path:
        payload["audit_trail_path"] = rel_path(audit_trail_path)
    if tool:
        payload["tool"] = {
            "name": tool["name"],
            "available_phases": allowed_phases,
            "side_effect_profile": side_effect_profile,
            "permission_tier": permission_tier,
        }
    return (0 if status == "admitted" else 1), payload


def command_action_admit(args: argparse.Namespace) -> int:
    try:
        state_path = cli_input_path(args.state) if args.state else None
        audit_trail_path = cli_input_path(args.audit_trail) if args.audit_trail else None
        token_budget_path = cli_input_path(args.token_budget) if args.token_budget else None
        exit_code, payload = action_admit_payload(
            tool_registry_path=cli_input_path(args.tool_registry),
            tool_name=args.tool,
            action=args.action,
            phase=args.phase,
            state_path=state_path,
            brief_id=args.brief_id,
            session_id=args.session_id,
            run_id=args.run_id,
            allow_mutation=args.allow_mutation,
            human_approved=args.human_approved,
            approval_ref=args.approval_ref,
            token_budget_path=token_budget_path,
            estimated_input_tokens=args.estimated_input_tokens,
            expected_output_tokens=args.expected_output_tokens,
            skill=args.skill,
            audit_trail_path=audit_trail_path,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['tool_name']}:{payload['action']} {payload['status']} in {payload['phase']}")
    return exit_code


def resolve_contract_token_budget_path(
    explicit_path: Path | None,
    contract: Dict[str, Any],
    contract_path: Path,
) -> Path | None:
    if explicit_path:
        return explicit_path
    budget_guard = contract.get("budget_guard")
    if not isinstance(budget_guard, dict):
        return None
    ref = budget_guard.get("token_budget_ref")
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref_path = Path(ref)
    if ref_path.is_absolute():
        return ref_path
    candidates = [
        (Path.cwd() / ref_path).resolve(),
        (ROOT / ref_path).resolve(),
        (contract_path.parent / ref_path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[1]


def action_budget_estimate(action: Dict[str, Any]) -> Dict[str, Any]:
    estimate = action.get("budget_estimate")
    if not isinstance(estimate, dict):
        return {
            "estimated_input_tokens": 0,
            "expected_output_tokens": 0,
            "phase": None,
            "skill": None,
        }
    return {
        "estimated_input_tokens": clamp_nonnegative_int(estimate.get("estimated_input_tokens", 0), "budget_estimate.estimated_input_tokens"),
        "expected_output_tokens": clamp_nonnegative_int(estimate.get("expected_output_tokens", 0), "budget_estimate.expected_output_tokens"),
        "phase": estimate.get("phase") if isinstance(estimate.get("phase"), str) else None,
        "skill": estimate.get("skill") if isinstance(estimate.get("skill"), str) else None,
    }


def missing_budget_status(contract: Dict[str, Any], reason: str = "budget_missing") -> Dict[str, Any]:
    return {
        "status": "missing",
        "decision": "blocked" if contract.get("autonomy_claim") == "self_autonomous" else "not_evaluated",
        "threshold": "missing",
        "stop_reason": "budget_missing",
        "evidence_refs": [reason],
    }


def latest_pending_control_event(state: Dict[str, Any]) -> Dict[str, Any] | None:
    for event in reversed(state.get("control_events", [])):
        if isinstance(event, dict) and event.get("status") == "pending":
            return event
    return None


def loop_action_validate_payload(
    contract_path: Path,
    action_path: Path,
    state_path: Path | None = None,
    token_budget_path: Path | None = None,
) -> Dict[str, Any]:
    contract_errors = validate_artifact(resolve_schema("loop-contract"), contract_path)
    action_errors = validate_artifact(resolve_schema("loop-action"), action_path)
    if contract_errors:
        raise ValueError("loop contract failed schema validation: " + "; ".join(contract_errors))
    if action_errors:
        raise ValueError("loop action failed schema validation: " + "; ".join(action_errors))
    contract = read_json(contract_path)
    action = read_json(action_path)
    state = load_workflow_state(state_path) if state_path else {}
    resolved_budget_path = resolve_contract_token_budget_path(token_budget_path, contract, contract_path)

    allowed = {
        tool.get("name"): set(tool.get("actions", []))
        for tool in contract.get("allowed_tools", [])
        if isinstance(tool, dict)
    }
    issues = []
    tool = action.get("tool")
    action_type = action.get("action_type")
    if tool not in allowed:
        issues.append({"rule": "tool_not_allowed", "message": f"tool is not allowed by Loop Contract: {tool}"})
    elif action_type not in allowed[tool]:
        issues.append(
            {
                "rule": "action_not_allowed_for_tool",
                "message": f"action {action_type} is not allowed for tool {tool}",
            }
        )

    pending_control = latest_pending_control_event(state)
    if pending_control and pending_control.get("event_type") in {"abort", "interrupt"} and action_type not in {"abort", "escalate"}:
        issues.append(
            {
                "rule": "blocked_by_control_event",
                "message": f"pending {pending_control.get('event_type')} control event blocks action",
            }
        )

    if action.get("safe_checkpoint_required"):
        checkpoint = state.get("safe_checkpoint")
        if not isinstance(checkpoint, dict) or checkpoint.get("idempotent") is not True:
            issues.append(
                {
                    "rule": "missing_safe_checkpoint",
                    "message": "action requires an idempotent safe checkpoint",
                }
            )

    if action_type == "run_tests":
        required = set(required_test_ids(contract))
        satisfied = set(action.get("satisfies_required_tests", []))
        missing = sorted(required - satisfied)
        if missing:
            issues.append(
                {
                    "rule": "action_skips_required_tests",
                    "message": "LLM-proposed action does not satisfy all required tests",
                    "missing_required_tests": missing,
                }
            )

    budget_check = None
    budget_status = state.get("budget_status") if isinstance(state.get("budget_status"), dict) else None
    if resolved_budget_path:
        estimate = action_budget_estimate(action)
        budget_check = loop_budget_check_payload(
            resolved_budget_path,
            estimate["estimated_input_tokens"],
            estimate["expected_output_tokens"],
            phase=estimate.get("phase"),
            skill=estimate.get("skill"),
        )
        budget_status = budget_check["budget_status"]
        if budget_check["status"] == "blocked":
            issues.append(
                {
                    "rule": budget_check.get("stop_reason", "budget_blocked"),
                    "message": "budget guard blocks the LLM-proposed action before execution",
                    "budget_status": budget_status,
                }
            )

    escalation_context = state.get("escalation_context") if isinstance(state, dict) else None
    if issues:
        status = "rejected"
    elif action_type == "escalate":
        status = "escalate"
    else:
        status = "admitted"

    return {
        "status": status,
        "contract_id": contract.get("contract_id"),
        "action_id": action.get("action_id"),
        "action_type": action_type,
        "tool": tool,
        "issues": issues,
        "escalation_context": escalation_context if status == "escalate" else None,
        "evidence_refs": action.get("evidence_refs", []),
        "budget_check": budget_check,
        "budget_status": budget_status,
    }


def command_loop_action_validate(args: argparse.Namespace) -> int:
    try:
        state_path = cli_input_path(args.state) if args.state else None
        payload = loop_action_validate_payload(
            cli_input_path(args.loop_contract),
            cli_input_path(args.action),
            state_path,
            cli_input_path(args.token_budget) if args.token_budget else None,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['action_id']}: loop action {payload['status']}")
    return 0 if payload["status"] in {"admitted", "escalate"} else 1


def dimension(score: int, evidence: str, refs: List[str], missing: List[str] | None = None) -> Dict[str, Any]:
    return {
        "score": score,
        "one_line_evidence": evidence,
        "evidence_refs": refs,
        "missing_mechanisms": missing or [],
    }


def maturity_verdict(
    scores: Dict[str, Dict[str, Any]],
    requested: str,
    budget_status: Dict[str, Any] | None = None,
) -> str:
    low_scores = [item["score"] for item in scores.values() if item["score"] <= 1]
    critical_low = any(
        scores[key]["score"] <= 1
        for key in ("win_condition_rigor", "test_selection_cannot_be_gamed", "failure_handling_escalation")
    )
    mostly_robust = sum(1 for item in scores.values() if item["score"] == 3) >= 5
    if low_scores and len(low_scores) >= 2:
        return "one_shot_in_disguise"
    if requested == "self_autonomous" and budget_status and budget_status.get("status") != "healthy":
        return "assisted_loop"
    if requested == "self_autonomous" and mostly_robust and not critical_low:
        return "self_autonomous"
    return "assisted_loop"


def loop_maturity_audit_payload(
    contract_path: Path,
    workflow_path: Path | None = None,
    state_path: Path | None = None,
    test_plan_path: Path | None = None,
    action_path: Path | None = None,
    test_results_path: Path | None = None,
    token_budget_path: Path | None = None,
) -> Dict[str, Any]:
    contract_errors = validate_artifact(resolve_schema("loop-contract"), contract_path)
    if contract_errors:
        raise ValueError("loop contract failed schema validation: " + "; ".join(contract_errors))
    if test_results_path:
        test_result_errors = validate_artifact(resolve_schema("loop-test-result"), test_results_path)
        if test_result_errors:
            raise ValueError("loop test result failed schema validation: " + "; ".join(test_result_errors))
    contract = read_json(contract_path)
    state = load_workflow_state(state_path) if state_path else {}
    test_plan = read_json(test_plan_path) if test_plan_path and test_plan_path.is_file() else {}
    test_results = read_json(test_results_path) if test_results_path and test_results_path.is_file() else {}

    test_required = required_test_ids(contract)
    test_missing = sorted(set(test_required) - provided_required_test_ids(test_plan)) if test_plan else test_required
    executed_missing = sorted(set(test_required) - executed_required_test_ids(test_results)) if test_results else test_required
    has_workflow = bool(workflow_path and workflow_path.is_file())
    has_progress = isinstance(state.get("loop_progress"), dict)
    has_control = bool(state.get("control_events")) and isinstance(state.get("safe_checkpoint"), dict)
    has_escalation = isinstance(state.get("escalation_context"), dict)
    supports_control = set(contract.get("control_channel", {}).get("supports", []))
    action_admission = {"status": "not_evaluated", "evidence_refs": []}
    budget_status = None
    contract_has_budget_guard = isinstance(contract.get("budget_guard"), dict)
    explicit_token_budget = token_budget_path is not None
    if action_path:
        action_payload = loop_action_validate_payload(contract_path, action_path, state_path, token_budget_path)
        action_admission = {
            "status": action_payload["status"],
            "evidence_refs": action_payload.get("evidence_refs", []),
        }
        budget_status = action_payload.get("budget_status")
    if contract.get("autonomy_claim") == "self_autonomous" and not contract_has_budget_guard and not explicit_token_budget:
        budget_status = missing_budget_status(contract, "self_autonomous Loop Contract missing budget_guard")
    if budget_status is None:
        resolved_budget_path = resolve_contract_token_budget_path(token_budget_path, contract, contract_path)
        if resolved_budget_path:
            budget_check = loop_budget_check_payload(resolved_budget_path, 0, 0)
            budget_status = budget_check["budget_status"]
    if budget_status is None:
        budget_status = missing_budget_status(contract, "token budget evidence missing")

    if test_missing:
        test_score = 1
        test_evidence = "Required tests are missing from the test plan."
        test_missing_mechanisms = [f"missing {item}" for item in test_missing]
    elif not test_results:
        test_score = 2
        test_evidence = "Required test floor is tag-covered, but executed result evidence is missing."
        test_missing_mechanisms = ["executed required-test evidence"]
    elif executed_missing:
        test_score = 1
        test_evidence = "Executed test results omit required passed evidence."
        test_missing_mechanisms = [f"missing executed {item}" for item in executed_missing]
    elif contract["test_selection"].get("additive_agent_tests") is True:
        test_score = 3
        test_evidence = "Required tests are tag-covered and backed by executed passed results."
        test_missing_mechanisms = []
    else:
        test_score = 1
        test_evidence = "Agent-selected tests are not additive-only."
        test_missing_mechanisms = ["additive agent test rule"]

    no_progress_after = contract.get("stop_escalate_rules", {}).get("no_progress_after")
    no_progress_count = state.get("no_progress_count", 0)
    robust_action = action_admission["status"] in {"admitted", "escalate", "not_evaluated"}
    control_score = 3 if has_control and {"steer", "abort", "interrupt", "escalate"}.issubset(supports_control) else (2 if has_control else 1)
    failure_score = (
        3
        if has_escalation and no_progress_after and isinstance(no_progress_count, int) and no_progress_count <= int(no_progress_after)
        else (2 if has_escalation and no_progress_after else 1)
    )
    scores = {
        "real_loop_vs_one_shot": dimension(
            3 if has_workflow and contract.get("feedback_channels") and has_progress else (2 if has_workflow and contract.get("feedback_channels") else 1),
            "Workflow graph and feedback channels are present." if has_workflow else "Workflow evidence is missing.",
            [rel_path(workflow_path)] if workflow_path else [],
            [] if has_workflow and has_progress else ["workflow graph evidence", "loop progress observations"],
        ),
        "win_condition_rigor": dimension(
            3 if len(contract.get("job_win_condition", {}).get("deterministic_checks", [])) >= 2 else (2 if contract.get("job_win_condition", {}).get("deterministic_checks") else 1),
            "Loop Contract declares deterministic done checks.",
            [rel_path(contract_path)],
            [],
        ),
        "test_selection_cannot_be_gamed": dimension(
            test_score,
            test_evidence,
            [rel_path(path) for path in (test_plan_path, test_results_path) if path],
            test_missing_mechanisms,
        ),
        "self_grading_risk": dimension(
            1 if contract.get("independent_truth", {}).get("type") == "agent_self_assessment" else (3 if contract.get("independent_truth", {}).get("evidence") else 2),
            "Independent truth is declared outside model self-assessment.",
            contract.get("independent_truth", {}).get("evidence", []),
            [],
        ),
        "feedback_fidelity": dimension(
            3 if contract.get("feedback_channels") and has_progress and robust_action else (2 if contract.get("feedback_channels") and has_progress else 1),
            "Feedback channels and workflow observations are modeled." if has_progress else "Workflow observations are not modeled.",
            [rel_path(state_path)] if state_path else [],
            [] if has_progress else ["loop progress observations"],
        ),
        "control_channel": dimension(
            control_score,
            "State-level control channel and safe checkpoint are modeled." if has_control else "Control channel state is missing.",
            [rel_path(state_path)] if state_path else [],
            [] if has_control else ["control events", "safe checkpoint"],
        ),
        "failure_handling_escalation": dimension(
            failure_score,
            "No-progress escalation context is modeled." if has_escalation else "Escalation context is missing.",
            [rel_path(state_path)] if state_path else [],
            [] if has_escalation else ["escalation context"],
        ),
    }
    verdict = maturity_verdict(scores, contract.get("autonomy_claim", "assisted_loop"), budget_status)

    budget_blocks_autonomy = (
        contract.get("autonomy_claim") == "self_autonomous"
        and isinstance(budget_status, dict)
        and budget_status.get("status") != "healthy"
    )
    if budget_blocks_autonomy:
        highest_gap = "Add healthy Loop Budget Guard evidence before claiming self-autonomous loop maturity."
    elif test_missing:
        highest_gap = "Complete non-gameable test selection by covering all required tests."
    elif not test_results:
        highest_gap = "Add execution-backed Loop Test Result evidence for every required test."
    elif executed_missing:
        highest_gap = "Run and record passing evidence for every required Loop Contract test."
    elif control_score <= 1:
        highest_gap = "Add control events and safe checkpoint evidence."
    elif failure_score <= 1:
        highest_gap = "Add no-progress and escalation context evidence."
    else:
        highest_gap = "Move from fixture-level evidence to runtime enforcement across all autonomous loop phases."

    report = {
        "contract_version": "1.0.0",
        "report_id": f"report:{contract.get('contract_id')}",
        "loop_contract_id": contract.get("contract_id"),
        "maturity_verdict": verdict,
        "action_admission": action_admission,
        "budget_status": budget_status,
        "dimension_scores": scores,
        "highest_leverage_gap": highest_gap,
        "prioritized_gaps": {
            "blocks_autonomy": [highest_gap] if verdict != "self_autonomous" else [],
            "fragile_under_load": ["Runtime enforcement remains broader than fixture validation."],
            "polish": ["Render maturity reports for human review."],
        },
        "one_question": "Which ADLC workflow should be the first production self-autonomous loop rather than assisted loop?",
    }
    errors = validate_artifact_payload(resolve_schema("loop-maturity-report"), report)
    if errors:
        raise ValueError("generated loop maturity report failed schema validation: " + "; ".join(errors))
    return report


def validate_artifact_payload(schema_path: Path, artifact: Dict[str, Any]) -> List[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    try:
        return validate_artifact(schema_path, tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def workspace_rel_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return rel_path(path)


def parse_schema_aliases(metadata_path: Path) -> Dict[str, str]:
    module = compile(metadata_path.read_text(encoding="utf-8"), str(metadata_path), "exec", flags=ast.PyCF_ONLY_AST)  # type: ignore[name-defined]
    for node in module.body:  # type: ignore[attr-defined]
        if not isinstance(node, ast.Assign):  # type: ignore[name-defined]
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SCHEMA_ALIASES":  # type: ignore[name-defined]
                value = ast.literal_eval(node.value)  # type: ignore[name-defined]
                if not isinstance(value, dict):
                    raise ValueError("SCHEMA_ALIASES must be a dictionary")
                return {str(key): str(raw_value) for key, raw_value in value.items()}
    raise ValueError(f"SCHEMA_ALIASES assignment not found: {metadata_path}")


def schema_alias_for_path(path: Path) -> str:
    name = path.name
    suffix = ".schema.json"
    return name[: -len(suffix)] if name.endswith(suffix) else path.stem


def schema_alias_drift(workspace: Path) -> Dict[str, Any]:
    metadata_path = workspace / "scripts" / "adlc_runtime" / "metadata.py"
    schemas_dir = workspace / "docs" / "schemas"
    issues: List[Dict[str, Any]] = []
    if not metadata_path.is_file():
        issues.append({"rule": "missing_metadata_py", "path": workspace_rel_path(metadata_path, workspace)})
        return {"detected": True, "rule": "schema_alias_missing", "metadata_path": workspace_rel_path(metadata_path, workspace), "schema_count": 0, "alias_count": 0, "missing_aliases": [], "stale_aliases": [], "issues": issues}
    if not schemas_dir.is_dir():
        issues.append({"rule": "missing_schema_directory", "path": workspace_rel_path(schemas_dir, workspace)})
        return {"detected": True, "rule": "schema_alias_missing", "metadata_path": workspace_rel_path(metadata_path, workspace), "schema_count": 0, "alias_count": 0, "missing_aliases": [], "stale_aliases": [], "issues": issues}

    aliases = parse_schema_aliases(metadata_path)
    schema_files = sorted(path for path in schemas_dir.glob("*.schema.json") if path.is_file())
    schema_refs = [workspace_rel_path(path, workspace) for path in schema_files]
    aliased_refs = set(aliases.values())
    missing_aliases = [
        {
            "rule": "schema_alias_missing",
            "alias": schema_alias_for_path(path),
            "path": workspace_rel_path(path, workspace),
        }
        for path in schema_files
        if workspace_rel_path(path, workspace) not in aliased_refs
    ]
    stale_aliases = [
        {
            "rule": "schema_alias_stale",
            "alias": alias,
            "path": target,
        }
        for alias, target in sorted(aliases.items())
        if target.startswith("docs/schemas/") and target not in set(schema_refs)
    ]
    issues.extend(missing_aliases)
    issues.extend(stale_aliases)
    return {
        "detected": bool(issues),
        "rule": "schema_alias_missing",
        "metadata_path": workspace_rel_path(metadata_path, workspace),
        "schema_count": len(schema_files),
        "alias_count": len(aliases),
        "missing_aliases": missing_aliases,
        "stale_aliases": stale_aliases,
        "issues": issues,
    }


def render_schema_alias_block(aliases: Dict[str, str]) -> List[str]:
    lines = ["SCHEMA_ALIASES = {\n"]
    for alias in sorted(aliases):
        lines.append(f"    {json.dumps(alias)}: {json.dumps(aliases[alias])},\n")
    lines.append("}\n")
    return lines


def replace_schema_alias_block(metadata_path: Path, aliases: Dict[str, str]) -> None:
    text = metadata_path.read_text(encoding="utf-8")
    module = compile(text, str(metadata_path), "exec", flags=ast.PyCF_ONLY_AST)  # type: ignore[name-defined]
    start_line = None
    end_line = None
    for node in module.body:  # type: ignore[attr-defined]
        if not isinstance(node, ast.Assign):  # type: ignore[name-defined]
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SCHEMA_ALIASES":  # type: ignore[name-defined]
                start_line = node.lineno - 1
                end_line = getattr(node, "end_lineno", None)
                break
        if start_line is not None:
            break
    if start_line is None or end_line is None:
        raise ValueError("unable to locate SCHEMA_ALIASES line range")
    lines = text.splitlines(keepends=True)
    lines[start_line:end_line] = render_schema_alias_block(aliases)
    metadata_path.write_text("".join(lines), encoding="utf-8")


def apply_schema_alias_repair(workspace: Path, drift: Dict[str, Any]) -> Dict[str, Any]:
    metadata_path = workspace / drift["metadata_path"]
    aliases = parse_schema_aliases(metadata_path)
    added: List[Dict[str, str]] = []
    for issue in drift.get("missing_aliases", []):
        alias = str(issue.get("alias") or "")
        target = str(issue.get("path") or "")
        if not alias or not target or alias in aliases:
            continue
        aliases[alias] = target
        added.append({"alias": alias, "path": target})
    if added:
        replace_schema_alias_block(metadata_path, aliases)
    return {
        "changed": bool(added),
        "changed_files": [drift["metadata_path"]] if added else [],
        "added_aliases": added,
    }


def default_control_plane_verifiers(workspace: Path) -> List[str]:
    if (workspace / "bin" / "adlc").is_file():
        return ["bin/adlc health-check --json"]
    if (workspace / "scripts" / "adlc_runtime" / "metadata.py").is_file():
        return ["python3 -m py_compile scripts/adlc_runtime/metadata.py"]
    return []


def verifier_status(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "not_run"
    return "fail" if any(item.get("exit_code") != 0 for item in results) else "pass"


def git_head_payload(workspace: Path) -> Dict[str, Any]:
    result = subprocess.run(["git", "-C", str(workspace), "rev-parse", "--short", "HEAD"], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return {"present": False, "head": None, "stderr": result.stderr[-1000:]}
    return {"present": True, "head": result.stdout.strip()}


def graph_freshness_payload(workspace: Path) -> Dict[str, Any]:
    graph = graph_report_payload(workspace)
    head = git_head_payload(workspace)
    graph["head_commit"] = head.get("head")
    built = graph.get("built_from_commit")
    graph["stale"] = bool(graph.get("present") and built and head.get("head") and not str(head["head"]).startswith(str(built)) and not str(built).startswith(str(head["head"])))
    return graph


def ensure_control_plane_state(state_path: Path, workspace: Path, brief_id: str, evidence_refs: List[str]) -> Dict[str, Any]:
    if state_path.exists():
        state = ensure_workflow_identity(load_workflow_state(state_path))
    else:
        state = new_workflow_state(brief_id=brief_id, workspace=workspace, phase="code")
    state["phase"] = "code"
    state["status"] = "planned"
    state["step"] = "dogfood-control-plane-drift"
    state["loop_progress"] = {
        "iteration_count": int(state.get("loop_progress", {}).get("iteration_count", 0)) + 1 if isinstance(state.get("loop_progress"), dict) else 1,
        "last_progress_signal": "control_plane_drift_scan",
        "last_observation": "schema alias drift scan executed",
        "evidence_refs": evidence_refs or ["adlc:control-plane-drift-loop"],
    }
    state["no_progress_count"] = 0
    state["safe_checkpoint"] = {
        "checkpoint_id": "checkpoint:" + stable_hash(str(state_path)),
        "phase": "code",
        "idempotent": True,
        "retryable": True,
        "rollback_plan": "discard the metadata.py schema-alias edit or rerun from the saved workflow state",
        "evidence_refs": evidence_refs or ["adlc:control-plane-drift-loop"],
    }
    state["escalation_context"] = {
        "trigger": "human_review_after_dogfood_repair",
        "phase": "engineer_review",
        "requested_decision": "review deterministic control-plane drift repair before merge",
        "no_progress_after": 2,
        "recent_observations": ["control-plane drift loop is bounded to schema alias repair"],
        "context_refs": evidence_refs or ["adlc:control-plane-drift-loop"],
    }
    state["updated_at"] = utc_now()
    return state


def control_plane_loop_contract(required_verifiers: List[str]) -> Dict[str, Any]:
    required_tests = [
        {
            "id": "required:control-plane-verifier",
            "command": command,
            "coverage_tags": ["control-plane", "schema-alias-drift"],
        }
        for command in (required_verifiers or ["python3 -m py_compile scripts/adlc_runtime/metadata.py"])
    ]
    return {
        "contract_version": "1.0.0",
        "contract_id": "adlc-control-plane-drift-loop",
        "autonomy_claim": "assisted_loop",
        "job_win_condition": {
            "job": "Detect and repair bounded ADLC control-plane drift.",
            "done_when": "Schema alias drift is repaired, verifier commands pass, and the workflow stops for human review.",
            "deterministic_checks": required_verifiers or ["python3 -m py_compile scripts/adlc_runtime/metadata.py"],
            "semantic_intent_check": "Human review confirms the repair stayed within the schema alias control-plane boundary.",
        },
        "allowed_tools": [
            {"name": "adlc-control-plane", "actions": ["repair"]},
            {"name": "human-escalation", "actions": ["escalate", "abort", "steer"]},
        ],
        "feedback_channels": [
            {"after_action": "drift_scan", "observes": ["missing_alias_count", "stale_alias_count", "metadata_path"]},
            {"after_action": "repair", "observes": ["changed_files", "added_aliases", "verifier_status"]},
        ],
        "stop_escalate_rules": {
            "max_iterations": 1,
            "no_progress_after": 1,
            "escalate_when": ["dirty_checkout", "action_not_admitted", "verifier_failed", "human_review_required"],
        },
        "test_selection": {
            "mandatory_floor": required_tests,
            "required_from_task_signals": required_tests,
            "additive_agent_tests": True,
        },
        "safe_bail_state": {
            "state": "workflow state and report artifacts are saved before mutation",
            "rollback": "revert metadata.py or discard the repair worktree",
            "idempotency": "re-running the alias repair is a no-op once aliases are present",
        },
        "progress_signal": {
            "signals": ["missing_alias_count_decreased", "verifier_status_passed", "state_updated"],
            "no_progress_rule": "one failed repair or unchanged missing-alias count escalates to human review",
        },
        "control_channel": {
            "supports": ["steer", "abort", "interrupt", "escalate"],
            "safe_checkpoint_required": True,
        },
        "independent_truth": {
            "type": "schema",
            "evidence": ["docs/schemas/control-plane-drift-report.schema.json", "scripts/adlc_runtime/metadata.py"],
        },
        "redaction_posture": "Only bounded command output and artifact refs are captured; no secrets are read.",
    }


def control_plane_loop_action(drift: Dict[str, Any], required_verifiers: List[str]) -> Dict[str, Any]:
    missing = drift.get("missing_aliases", [])
    return {
        "contract_version": "1.0.0",
        "action_id": "action:repair-schema-alias-drift:" + stable_hash(json.dumps(missing, sort_keys=True)),
        "proposed_by": "tool",
        "action_type": "repair",
        "tool": "adlc-control-plane",
        "rationale": "Schema files without SCHEMA_ALIASES entries are unreachable through schema aliases and drift from the control-plane contract.",
        "expected_observation": "Missing schema aliases are added to scripts/adlc_runtime/metadata.py and verifier commands pass.",
        "required_preconditions": ["safe_checkpoint", "action_admission", "clean_repair_workspace"],
        "satisfies_required_tests": ["required:control-plane-verifier"],
        "control_event_type": None,
        "safe_checkpoint_required": True,
        "rollback_note": "Revert the metadata.py alias additions or discard the repair worktree.",
        "evidence_refs": [drift.get("metadata_path", "scripts/adlc_runtime/metadata.py")],
        "budget_estimate": {
            "estimated_input_tokens": 0,
            "expected_output_tokens": 0,
            "projected_total_tokens": 0,
            "phase": "code",
            "skill": "drift-maintenance",
            "evidence_refs": ["deterministic local command"],
        },
    }


def write_artifact(path: Path, payload: Dict[str, Any], schema_alias: str | None = None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if schema_alias:
        errors = validate_artifact(resolve_schema(schema_alias), path)
        if errors:
            raise ValueError(f"{schema_alias} artifact failed schema validation: " + "; ".join(errors))
    return rel_path(path)


def control_plane_work_item_sync_payload(
    args: argparse.Namespace,
    state: Dict[str, Any],
    drift: Dict[str, Any],
    evidence_refs: List[str],
    status: str,
    next_action: str,
) -> Dict[str, Any]:
    external_id = f"adlc-control-plane-drift:{drift.get('rule', 'unknown')}"
    return {
        "contract_version": "1.0.0",
        "target": args.target,
        "work_item": {
            "external_id": external_id,
            "idempotency_key": external_id,
            "build_brief_id": state["brief_id"],
            "task_id": "ADLC-GOAL-7-CONTROL-PLANE-DRIFT",
            "artifact_type": "control-plane-drift",
            "title": "ADLC control-plane drift: schema alias parity",
            "labels": ["adlc", "dogfood", "control-plane", "drift"],
        },
        "run_identity": {
            "brief_id": state["brief_id"],
            "run_id": state["run_id"],
            "session_id": state["session_id"],
            "resume_count": state.get("resume_count", 0),
            "attempt": state.get("attempt", 1),
        },
        "status_update": {
            "status": status,
            "phase": "code",
            "blockers": [
                {
                    "code": issue["rule"],
                    "summary": f"{issue.get('alias', issue.get('path', 'control-plane drift'))}: {issue.get('path', '')}",
                    "evidence_refs": [issue.get("path", drift.get("metadata_path", ""))],
                }
                for issue in drift.get("issues", [])
                if isinstance(issue, dict)
            ],
            "verifier_results": [],
            "evidence_refs": evidence_refs or [drift.get("metadata_path", "scripts/adlc_runtime/metadata.py")],
            "next_action": next_action,
            "updated_at": utc_now(),
        },
    }


def control_plane_mutation_admission(args: argparse.Namespace, state_path: Path, state: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    if not args.tool_registry:
        raise ValueError("--tool-registry is required with --allow-mutation")
    audit_path = cli_input_path(args.audit_trail) if args.audit_trail else state_path.parent / "control_plane_permission_audit.json"
    return action_admit_payload(
        tool_registry_path=cli_input_path(args.tool_registry),
        tool_name="adlc-control-plane",
        action="repair_schema_alias_drift",
        phase="code",
        state_path=state_path if state_path.exists() else None,
        brief_id=state.get("brief_id"),
        run_id=state.get("run_id"),
        session_id=state.get("session_id"),
        allow_mutation=True,
        human_approved=args.human_approved,
        approval_ref=args.approval_ref,
        audit_trail_path=audit_path,
    )


def control_plane_drift_loop_payload(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    workspace = resolve_workspace(args.workspace)
    state_path = resolve_under_workspace(args.state, workspace, ".adlc/control_plane_drift_state.json")
    output_path = resolve_under_workspace(args.output, workspace, ".adlc/outputs/control_plane_drift_loop.json")
    artifact_dir = output_path.parent / "control_plane_drift"
    verifier_commands = args.verifier or default_control_plane_verifiers(workspace)
    evidence_refs: List[str] = []
    graph = graph_freshness_payload(workspace)
    if graph.get("report"):
        evidence_refs.append(str(graph["report"]))
    state = ensure_control_plane_state(state_path, workspace, args.brief_id or "ADLC-GOAL-7-CONTROL-PLANE-DRIFT", evidence_refs)
    save_workflow_state(state_path, state)
    evidence_refs.append(rel_path(state_path))

    pre_results, pre_evidence = run_verifier_commands(verifier_commands, workspace, artifact_dir / "pre_verification.json") if verifier_commands else ([], [])
    evidence_refs.extend(pre_evidence)
    drift = schema_alias_drift(workspace)
    evidence_refs.append(drift.get("metadata_path", "scripts/adlc_runtime/metadata.py"))
    dirty_before = git_dirty_status(workspace)

    next_action = "human review control-plane drift loop evidence" if not drift["detected"] else "review planned schema alias repair"
    work_item_request = control_plane_work_item_sync_payload(args, state, drift, evidence_refs, "planned" if drift["detected"] else "completed", next_action)
    work_item_ref = write_artifact(artifact_dir / "work_item_sync.json", work_item_request, "work-item-sync")
    sync_args = argparse.Namespace(
        work_item=work_item_ref,
        build_brief=None,
        target=args.target,
        workspace=str(workspace),
        state=str(state_path),
        existing_work_items=args.existing_work_items,
        dry_run=True,
        allow_mutation=False,
        provider_command=None,
        tool_registry=None,
        audit_trail=None,
        human_approved=False,
        approval_ref=None,
        json=True,
    )
    _, sync_payload = sync_work_item_payload(sync_args)

    contract = control_plane_loop_contract(verifier_commands)
    contract_ref = write_artifact(artifact_dir / "loop_contract.json", contract, "loop-contract")
    action = control_plane_loop_action(drift, verifier_commands)
    action_ref = write_artifact(artifact_dir / "loop_action.json", action, "loop-action")
    action_validation = loop_action_validate_payload(cli_input_path(contract_ref), cli_input_path(action_ref), state_path)

    repair: Dict[str, Any] = {
        "applied": False,
        "changed_files": [],
        "added_aliases": [],
        "dirty_before": dirty_before,
    }
    final_results: List[Dict[str, Any]] = []
    final_evidence: List[str] = []
    issues: List[Dict[str, Any]] = list(drift.get("issues", []))
    stop_reason = None
    status = "no_drift"
    exit_code = 0

    if not drift["detected"]:
        state["phase"] = "engineer_review"
        state["status"] = "awaiting_approval"
        state["stop_reason"] = "human_gate"
        state["updated_at"] = utc_now()
        append_history(state, {"phase": "control_plane_drift_loop", "status": "no_drift", "artifact_ref": rel_path(output_path)})
        save_workflow_state(state_path, state)
    elif args.dry_run:
        status = "planned"
        stop_reason = "dry_run"
        append_history(state, {"phase": "control_plane_drift_loop", "status": "planned", "artifact_ref": rel_path(output_path)})
        save_workflow_state(state_path, state)
    else:
        if verifier_status(pre_results) == "fail":
            status = "blocked"
            stop_reason = "pre_verification_failed"
            issues.append({"rule": "pre_verification_failed", "message": "pre-repair verifier failed"})
            exit_code = 1
        elif action_validation["status"] != "admitted":
            status = "blocked"
            stop_reason = "action_not_admitted"
            issues.extend(action_validation.get("issues", []))
            exit_code = 1
        elif dirty_before.get("dirty"):
            status = "blocked"
            stop_reason = dirty_before.get("reason", "dirty_checkout")
            issues.append({"rule": stop_reason, "message": "repair workspace is not clean", "git": dirty_before})
            exit_code = 1
        elif not args.allow_mutation:
            status = "blocked"
            stop_reason = "action_not_admitted"
            issues.append({"rule": "action_not_admitted", "message": "schema alias repair requires --allow-mutation and --tool-registry"})
            exit_code = 1
        else:
            admission_exit, admission = control_plane_mutation_admission(args, state_path, state)
            repair["admission"] = admission
            if admission_exit != 0:
                status = "blocked"
                stop_reason = admission.get("stop_reason") or admission["status"]
                issues.extend(admission.get("issues", []))
                exit_code = 1
            else:
                repair_result = apply_schema_alias_repair(workspace, drift)
                repair.update(repair_result)
                repair["applied"] = bool(repair_result["changed"])
                if repair_result["changed"]:
                    record_local_side_effect(state, "adlc-control-plane", "repair_schema_alias_drift", "ADLC-GOAL-7-CONTROL-PLANE-DRIFT", ",".join(repair_result["changed_files"]))
                post_drift = schema_alias_drift(workspace)
                repair["post_drift"] = post_drift
                final_results, final_evidence = run_verifier_commands(verifier_commands, workspace, artifact_dir / "final_verification.json") if verifier_commands else ([], [])
                evidence_refs.extend(final_evidence)
                if post_drift["detected"]:
                    status = "fail"
                    stop_reason = "drift_still_detected"
                    issues.extend(post_drift.get("issues", []))
                    exit_code = 1
                elif verifier_status(final_results) == "fail":
                    status = "fail"
                    stop_reason = "verifier_failed"
                    issues.append({"rule": "verifier_failed", "message": "post-repair verifier failed"})
                    exit_code = 1
                else:
                    status = "needs_human"
                    stop_reason = "human_gate"
                    state["phase"] = "engineer_review"
                    state["status"] = "awaiting_approval"
                    state["stop_reason"] = "human_gate"
                    state["loop_progress"]["last_progress_signal"] = "schema_alias_drift_repaired"
                    state["loop_progress"]["last_observation"] = "schema alias drift repaired and verifier commands passed"
                    state["loop_progress"]["evidence_refs"] = evidence_refs
                    state["updated_at"] = utc_now()
                    append_history(state, {"phase": "control_plane_drift_loop", "status": "needs_human", "artifact_ref": rel_path(output_path), "changed_files": repair_result["changed_files"]})
                    save_workflow_state(state_path, state)

    report = {
        "contract_version": "1.0.0",
        "loop_id": "adlc-control-plane-drift-loop",
        "status": status,
        "dry_run": bool(args.dry_run),
        "human_review_required": status in {"needs_human", "no_drift", "planned"},
        "run_identity": workflow_identity_payload(state),
        "workspace": str(workspace),
        "state_ref": rel_path(state_path),
        "graph": graph,
        "verification": {
            "pre": {"status": verifier_status(pre_results), "commands": verifier_commands, "results": pre_results},
            "final": {"status": verifier_status(final_results), "commands": verifier_commands, "results": final_results},
        },
        "drift": drift,
        "work_item_sync": {"request_ref": work_item_ref, "summary": sync_payload.get("summary"), "operations": sync_payload.get("operations", [])},
        "loop_contract_ref": contract_ref,
        "proposed_action": {"action_ref": action_ref, "action_id": action["action_id"]},
        "action_validation": action_validation,
        "repair": repair,
        "evidence_refs": sorted(set(str(ref) for ref in evidence_refs if str(ref).strip())),
        "next_action": "human review deterministic repair evidence before merge",
        "warnings": ["graph_report_stale"] if graph.get("stale") else [],
        "issues": issues,
    }
    if stop_reason:
        report["stop_reason"] = stop_reason
    report_ref = write_artifact(output_path, report, "control-plane-drift-report")
    report["report_ref"] = report_ref
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return exit_code, report


def command_control_plane_drift_loop(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = control_plane_drift_loop_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['loop_id']}: {payload['status']}")
    return exit_code


def command_loop_maturity_audit(args: argparse.Namespace) -> int:
    try:
        output_path = cli_input_path(args.output) if args.output else None
        payload = loop_maturity_audit_payload(
            contract_path=cli_input_path(args.loop_contract),
            workflow_path=cli_input_path(args.workflow) if args.workflow else None,
            state_path=cli_input_path(args.state) if args.state else None,
            test_plan_path=cli_input_path(args.test_plan) if args.test_plan else None,
            action_path=cli_input_path(args.action) if args.action else None,
            test_results_path=cli_input_path(args.test_results) if args.test_results else None,
            token_budget_path=cli_input_path(args.token_budget) if args.token_budget else None,
        )
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['loop_contract_id']}: {payload['maturity_verdict']}")
    return 0


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


def command_sync_work_item(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = sync_work_item_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        mode = "dry-run" if payload["dry_run"] else "mutated"
        print(f"{payload['target']}: {payload['summary']['total']} work item sync operation(s) ({mode})")
    return exit_code


def command_queue_status(args: argparse.Namespace) -> int:
    try:
        payload = queue_status_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        summary = payload["summary"]
        print(f"{payload['queue_id']}: {summary['total']} task(s), {summary['active']} active, {summary['blocked']} blocked")
    return 0


def command_queue_claim(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = queue_transition_payload(args, "claim")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: {payload['operation']} {payload['status']}")
    return exit_code


def command_queue_release(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = queue_transition_payload(args, "release")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: {payload['operation']} {payload['status']}")
    return exit_code


def command_queue_complete(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = queue_transition_payload(args, "complete")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: {payload['operation']} {payload['status']}")
    return exit_code


def command_queue_block(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = queue_transition_payload(args, "block")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: {payload['operation']} {payload['status']}")
    return exit_code


def command_queue_escalate(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = queue_transition_payload(args, "escalate")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: {payload['operation']} {payload['status']}")
    return exit_code


def command_worktree_prepare(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = worktree_prepare_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: worktree prepare {payload['status']}")
    return exit_code


def command_worktree_status(args: argparse.Namespace) -> int:
    try:
        payload = worktree_status_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['queue_id'] or '-'}: {payload['summary']['total']} worktree ref(s)")
    return 0


def command_worktree_cleanup(args: argparse.Namespace) -> int:
    try:
        exit_code, payload = worktree_cleanup_payload(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        write_json(payload)
    else:
        print(f"{payload['task_id']}: worktree cleanup {payload['status']}")
    return exit_code


def command_slop_gate(args: argparse.Namespace) -> int:
    try:
        brief_path = Path(args.build_brief)
        if not brief_path.is_absolute():
            brief_path = ROOT / brief_path
        payload = slop_gate_payload(brief_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        write_json(payload)
    else:
        print(
            f"{payload['build_brief_id']}: slop gate {payload['status']} "
            f"({payload['summary']['generated_output_surfaces']} generated-output surfaces, "
            f"{payload['summary']['issues']} issues)"
        )
    return 0 if payload["status"] == "pass" else 1


def mcp_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": command_mcp_name("list-agents"),
            "description": command_description("list-agents"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "json": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": command_mcp_name("list-phases"),
            "description": command_description("list-phases"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "json": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": command_mcp_name("validate-artifact"),
            "description": command_description("validate-artifact"),
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
            "name": command_mcp_name("health-check"),
            "description": command_description("health-check"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "include_optional": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": command_mcp_name("ci"),
            "description": command_description("ci"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "suite": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(DEFAULT_CI_SUITE_ORDER)},
                    },
                },
            },
        },
        {
            "name": command_mcp_name("action-admit"),
            "description": command_description("action-admit"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tool_registry", "tool", "action"],
                "properties": {
                    "tool_registry": {"type": "string", "minLength": 1},
                    "tool": {"type": "string", "minLength": 1},
                    "action": {"type": "string", "minLength": 1},
                    "phase": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "brief_id": {"type": "string", "minLength": 1},
                    "run_id": {"type": "string", "minLength": 1},
                    "session_id": {"type": "string", "minLength": 1},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                    "token_budget": {"type": "string", "minLength": 1},
                    "estimated_input_tokens": {"type": "integer", "minimum": 0, "default": 0},
                    "expected_output_tokens": {"type": "integer", "minimum": 0, "default": 0},
                    "skill": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                    "audit_trail": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("run-phase"),
            "description": command_description("run-phase"),
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
                    "build_brief": {"type": "string", "minLength": 1},
                    "verifier": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "allow_noop": {"type": "boolean", "default": False},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                    "max_refs": {"type": "integer", "minimum": 1, "default": 8},
                    "runtime": {"type": "string", "enum": list(SUPPORTED_RUNTIMES)},
                    "tools": {"type": "string"},
                    "schema": {"type": "string"},
                    "label": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": command_mcp_name("resume-workflow"),
            "description": command_description("resume-workflow"),
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
            "name": command_mcp_name("emit-work-items"),
            "description": command_description("emit-work-items"),
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
        {
            "name": command_mcp_name("sync-work-item"),
            "description": command_description("sync-work-item"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "work_item": {"type": "string", "minLength": 1},
                    "build_brief": {"type": "string", "minLength": 1},
                    "target": {"type": "string", "enum": list(WORK_ITEM_TARGETS)},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "existing_work_items": {"type": "string", "minLength": 1},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "provider_command": {"type": "string"},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-status"),
            "description": command_description("queue-status"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-claim"),
            "description": command_description("queue-claim"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "agent_id": {"type": "string", "minLength": 1},
                    "worktree_ref": {"type": "string", "minLength": 1},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-release"),
            "description": command_description("queue-release"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-complete"),
            "description": command_description("queue-complete"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "evidence": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-block"),
            "description": command_description("queue-block"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id", "reason", "next_action"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                    "next_action": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "evidence": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("queue-escalate"),
            "description": command_description("queue-escalate"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id", "reason", "next_action"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                    "next_action": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "evidence": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("worktree-prepare"),
            "description": command_description("worktree-prepare"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "worktree_root": {"type": "string", "minLength": 1},
                    "worktree_path": {"type": "string", "minLength": 1},
                    "base_ref": {"type": "string", "minLength": 1},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("worktree-status"),
            "description": command_description("worktree-status"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "worktree_root": {"type": "string", "minLength": 1},
                    "worktree_path": {"type": "string", "minLength": 1},
                    "base_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("worktree-cleanup"),
            "description": command_description("worktree-cleanup"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["queue", "task_id"],
                "properties": {
                    "queue": {"type": "string", "minLength": 1},
                    "task_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "worktree_root": {"type": "string", "minLength": 1},
                    "worktree_path": {"type": "string", "minLength": 1},
                    "base_ref": {"type": "string", "minLength": 1},
                    "force": {"type": "boolean", "default": False},
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("compound-context"),
            "description": command_description("compound-context"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "workspace": {"type": "string", "minLength": 1},
                    "input": {"type": "string", "minLength": 1},
                    "build_brief": {"type": "string", "minLength": 1},
                    "max_refs": {"type": "integer", "minimum": 1, "default": 8},
                },
            },
        },
        {
            "name": command_mcp_name("control-plane-drift-loop"),
            "description": command_description("control-plane-drift-loop"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "brief_id": {"type": "string", "minLength": 1},
                    "workspace": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "output": {"type": "string", "minLength": 1},
                    "target": {"type": "string", "enum": list(WORK_ITEM_TARGETS), "default": "linear"},
                    "existing_work_items": {"type": "string", "minLength": 1},
                    "verifier": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "dry_run": {"type": "boolean", "default": True},
                    "allow_mutation": {"type": "boolean", "default": False},
                    "tool_registry": {"type": "string", "minLength": 1},
                    "audit_trail": {"type": "string", "minLength": 1},
                    "human_approved": {"type": "boolean", "default": False},
                    "approval_ref": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("slop-gate"),
            "description": command_description("slop-gate"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["build_brief"],
                "properties": {
                    "build_brief": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("loop-test-selection"),
            "description": command_description("loop-test-selection"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["loop_contract", "test_plan"],
                "properties": {
                    "loop_contract": {"type": "string", "minLength": 1},
                    "test_plan": {"type": "string", "minLength": 1},
                    "test_results": {"type": "string", "minLength": 1},
                    "require_test_results": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": command_mcp_name("loop-budget-check"),
            "description": command_description("loop-budget-check"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["token_budget", "estimated_input_tokens", "expected_output_tokens"],
                "properties": {
                    "token_budget": {"type": "string", "minLength": 1},
                    "estimated_input_tokens": {"type": "integer", "minimum": 0},
                    "expected_output_tokens": {"type": "integer", "minimum": 0},
                    "phase": {"type": "string", "minLength": 1},
                    "skill": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                },
            },
        },
        {
            "name": command_mcp_name("loop-action-validate"),
            "description": command_description("loop-action-validate"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["loop_contract", "action"],
                "properties": {
                    "loop_contract": {"type": "string", "minLength": 1},
                    "action": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "token_budget": {"type": "string", "minLength": 1},
                },
            },
        },
        {
            "name": command_mcp_name("loop-maturity-audit"),
            "description": command_description("loop-maturity-audit"),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["loop_contract"],
                "properties": {
                    "loop_contract": {"type": "string", "minLength": 1},
                    "workflow": {"type": "string", "minLength": 1},
                    "state": {"type": "string", "minLength": 1},
                    "test_plan": {"type": "string", "minLength": 1},
                    "test_results": {"type": "string", "minLength": 1},
                    "action": {"type": "string", "minLength": 1},
                    "token_budget": {"type": "string", "minLength": 1},
                    "output": {"type": "string", "minLength": 1},
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
    if name == "adlc_health_check":
        payload = health_check_payload(include_optional=bool(arguments.get("include_optional", False)))
        return tool_result(payload, is_error=payload["summary"]["failed_required"] != 0)
    if name == "adlc_ci":
        suites_arg = arguments.get("suite")
        suites = suites_arg if isinstance(suites_arg, list) else None
        exit_code, payload = ci_payload(suites)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_action_admit":
        for key in ("tool_registry", "tool", "action"):
            if not isinstance(arguments.get(key), str):
                raise ValueError(f"adlc_action_admit requires string argument: {key}")
        exit_code, payload = action_admit_payload(
            tool_registry_path=cli_input_path(arguments["tool_registry"], ROOT),
            tool_name=arguments["tool"],
            action=arguments["action"],
            phase=arguments.get("phase") if isinstance(arguments.get("phase"), str) else None,
            state_path=cli_input_path(arguments["state"], ROOT) if isinstance(arguments.get("state"), str) else None,
            brief_id=arguments.get("brief_id") if isinstance(arguments.get("brief_id"), str) else None,
            session_id=arguments.get("session_id") if isinstance(arguments.get("session_id"), str) else None,
            run_id=arguments.get("run_id") if isinstance(arguments.get("run_id"), str) else None,
            allow_mutation=bool(arguments.get("allow_mutation", False)),
            human_approved=bool(arguments.get("human_approved", False)),
            approval_ref=arguments.get("approval_ref") if isinstance(arguments.get("approval_ref"), str) else None,
            token_budget_path=cli_input_path(arguments["token_budget"], ROOT) if isinstance(arguments.get("token_budget"), str) else None,
            estimated_input_tokens=clamp_nonnegative_int(arguments.get("estimated_input_tokens", 0), "estimated_input_tokens"),
            expected_output_tokens=clamp_nonnegative_int(arguments.get("expected_output_tokens", 0), "expected_output_tokens"),
            skill=arguments.get("skill") if isinstance(arguments.get("skill"), str) else None,
            audit_trail_path=cli_input_path(arguments["audit_trail"], ROOT) if isinstance(arguments.get("audit_trail"), str) else None,
        )
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_run_phase":
        args = argparse.Namespace(
            phase=arguments.get("phase"),
            brief_id=arguments.get("brief_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            input=arguments.get("input"),
            output=arguments.get("output"),
            build_brief=arguments.get("build_brief"),
            verifier=arguments.get("verifier") if isinstance(arguments.get("verifier"), list) else [],
            allow_noop=arguments.get("allow_noop", False),
            allow_mutation=arguments.get("allow_mutation", False),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            max_refs=arguments.get("max_refs", 8),
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
        return tool_result(resume_workflow_payload(arguments.get("workspace"), arguments.get("state")))
    if name == "adlc_compound_context":
        args = argparse.Namespace(
            workspace=arguments.get("workspace"),
            input=arguments.get("input"),
            build_brief=arguments.get("build_brief"),
            max_refs=arguments.get("max_refs", 8),
            json=True,
        )
        return tool_result(compound_context_payload(args))
    if name == "adlc_control_plane_drift_loop":
        args = argparse.Namespace(
            brief_id=arguments.get("brief_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            output=arguments.get("output"),
            target=arguments.get("target") or "linear",
            existing_work_items=arguments.get("existing_work_items"),
            verifier=arguments.get("verifier") if isinstance(arguments.get("verifier"), list) else [],
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            json=True,
        )
        exit_code, payload = control_plane_drift_loop_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
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
    if name == "adlc_sync_work_item":
        args = argparse.Namespace(
            work_item=arguments.get("work_item"),
            build_brief=arguments.get("build_brief"),
            target=arguments.get("target"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            existing_work_items=arguments.get("existing_work_items"),
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            provider_command=arguments.get("provider_command"),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            json=True,
        )
        exit_code, payload = sync_work_item_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_queue_status":
        args = argparse.Namespace(
            queue=arguments.get("queue"),
            workspace=arguments.get("workspace"),
            json=True,
        )
        return tool_result(queue_status_payload(args))
    if name in {"adlc_queue_claim", "adlc_queue_release", "adlc_queue_complete", "adlc_queue_block", "adlc_queue_escalate"}:
        operation = {
            "adlc_queue_claim": "claim",
            "adlc_queue_release": "release",
            "adlc_queue_complete": "complete",
            "adlc_queue_block": "block",
            "adlc_queue_escalate": "escalate",
        }[name]
        args = argparse.Namespace(
            queue=arguments.get("queue"),
            task_id=arguments.get("task_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            agent_id=arguments.get("agent_id"),
            worktree_ref=arguments.get("worktree_ref"),
            reason=arguments.get("reason"),
            next_action=arguments.get("next_action"),
            evidence=arguments.get("evidence") if isinstance(arguments.get("evidence"), list) else [],
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            json=True,
        )
        if not isinstance(args.task_id, str):
            raise ValueError(f"{name} requires string argument: task_id")
        exit_code, payload = queue_transition_payload(args, operation)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_worktree_prepare":
        args = argparse.Namespace(
            queue=arguments.get("queue"),
            task_id=arguments.get("task_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            worktree_root=arguments.get("worktree_root"),
            worktree_path=arguments.get("worktree_path"),
            base_ref=arguments.get("base_ref"),
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            json=True,
        )
        if not isinstance(args.task_id, str):
            raise ValueError("adlc_worktree_prepare requires string argument: task_id")
        exit_code, payload = worktree_prepare_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_worktree_status":
        args = argparse.Namespace(
            queue=arguments.get("queue"),
            task_id=arguments.get("task_id"),
            workspace=arguments.get("workspace"),
            worktree_root=arguments.get("worktree_root"),
            worktree_path=arguments.get("worktree_path"),
            base_ref=arguments.get("base_ref"),
            json=True,
        )
        return tool_result(worktree_status_payload(args))
    if name == "adlc_worktree_cleanup":
        args = argparse.Namespace(
            queue=arguments.get("queue"),
            task_id=arguments.get("task_id"),
            workspace=arguments.get("workspace"),
            state=arguments.get("state"),
            worktree_root=arguments.get("worktree_root"),
            worktree_path=arguments.get("worktree_path"),
            base_ref=arguments.get("base_ref"),
            force=arguments.get("force", False),
            dry_run=arguments.get("dry_run", True),
            allow_mutation=arguments.get("allow_mutation", False),
            tool_registry=arguments.get("tool_registry"),
            audit_trail=arguments.get("audit_trail"),
            human_approved=arguments.get("human_approved", False),
            approval_ref=arguments.get("approval_ref"),
            json=True,
        )
        if not isinstance(args.task_id, str):
            raise ValueError("adlc_worktree_cleanup requires string argument: task_id")
        exit_code, payload = worktree_cleanup_payload(args)
        return tool_result(payload, is_error=exit_code != 0)
    if name == "adlc_slop_gate":
        build_brief = arguments.get("build_brief")
        if not isinstance(build_brief, str):
            raise ValueError("adlc_slop_gate requires string argument: build_brief")
        brief_path = Path(build_brief)
        if not brief_path.is_absolute():
            brief_path = ROOT / brief_path
        payload = slop_gate_payload(brief_path)
        return tool_result(payload, is_error=payload["status"] != "pass")
    if name == "adlc_loop_test_selection":
        loop_contract = arguments.get("loop_contract")
        test_plan = arguments.get("test_plan")
        test_results = arguments.get("test_results")
        if not isinstance(loop_contract, str) or not isinstance(test_plan, str):
            raise ValueError("adlc_loop_test_selection requires string arguments: loop_contract, test_plan")
        payload = loop_test_selection_payload(
            cli_input_path(loop_contract, ROOT),
            cli_input_path(test_plan, ROOT),
            cli_input_path(test_results, ROOT) if isinstance(test_results, str) else None,
            require_test_results=bool(arguments.get("require_test_results", False)),
        )
        return tool_result(payload, is_error=payload["status"] != "pass")
    if name == "adlc_loop_budget_check":
        token_budget = arguments.get("token_budget")
        if not isinstance(token_budget, str):
            raise ValueError("adlc_loop_budget_check requires string argument: token_budget")
        payload = loop_budget_check_payload(
            cli_input_path(token_budget, ROOT),
            arguments.get("estimated_input_tokens", 0),
            arguments.get("expected_output_tokens", 0),
            phase=arguments.get("phase") if isinstance(arguments.get("phase"), str) else None,
            skill=arguments.get("skill") if isinstance(arguments.get("skill"), str) else None,
        )
        return tool_result(payload, is_error=payload["status"] == "blocked")
    if name == "adlc_loop_action_validate":
        loop_contract = arguments.get("loop_contract")
        action = arguments.get("action")
        state = arguments.get("state")
        token_budget = arguments.get("token_budget")
        if not isinstance(loop_contract, str) or not isinstance(action, str):
            raise ValueError("adlc_loop_action_validate requires string arguments: loop_contract, action")
        payload = loop_action_validate_payload(
            cli_input_path(loop_contract, ROOT),
            cli_input_path(action, ROOT),
            cli_input_path(state, ROOT) if isinstance(state, str) else None,
            cli_input_path(token_budget, ROOT) if isinstance(token_budget, str) else None,
        )
        return tool_result(payload, is_error=payload["status"] == "rejected")
    if name == "adlc_loop_maturity_audit":
        loop_contract = arguments.get("loop_contract")
        if not isinstance(loop_contract, str):
            raise ValueError("adlc_loop_maturity_audit requires string argument: loop_contract")
        output = arguments.get("output")
        payload = loop_maturity_audit_payload(
            contract_path=cli_input_path(loop_contract, ROOT),
            workflow_path=cli_input_path(arguments["workflow"], ROOT) if isinstance(arguments.get("workflow"), str) else None,
            state_path=cli_input_path(arguments["state"], ROOT) if isinstance(arguments.get("state"), str) else None,
            test_plan_path=cli_input_path(arguments["test_plan"], ROOT) if isinstance(arguments.get("test_plan"), str) else None,
            test_results_path=cli_input_path(arguments["test_results"], ROOT) if isinstance(arguments.get("test_results"), str) else None,
            action_path=cli_input_path(arguments["action"], ROOT) if isinstance(arguments.get("action"), str) else None,
            token_budget_path=cli_input_path(arguments["token_budget"], ROOT) if isinstance(arguments.get("token_budget"), str) else None,
        )
        if isinstance(output, str):
            output_path = cli_input_path(output, ROOT)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return tool_result(payload, is_error=payload["maturity_verdict"] == "one_shot_in_disguise")
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

    def add_queue_base_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--queue", help="Work Queue JSON path. Defaults to .adlc/work_queue.json under --workspace.")
        command.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
        command.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
        command.add_argument("--dry-run", action="store_true", help="Plan operation without mutating queue, state, or worktrees.")
        command.add_argument("--allow-mutation", action="store_true", help="Permit local queue or worktree mutation after action admission.")
        command.add_argument("--tool-registry", help="Tool Registry JSON path used by action-admit before mutation.")
        command.add_argument("--audit-trail", help="Permission Audit Trail JSON path to create or append.")
        command.add_argument("--human-approved", action="store_true", help="Record that a human approved the requested local mutation.")
        command.add_argument("--approval-ref", help="Human approval ticket, comment, or transcript reference.")
        command.add_argument("--json", action="store_true", help="Emit JSON.")

    def add_worktree_plan_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--worktree-root", help="Directory used for generated worktree paths.")
        command.add_argument("--worktree-path", help="Explicit worktree path.")
        command.add_argument("--base-ref", help="Git base ref for new worktrees. Defaults to HEAD.")

    def add_tool_phase_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--build-brief", help="Build Brief JSON path for deterministic tool nodes.")
        command.add_argument("--verifier", action="append", help="Verifier command for the qa tool node. Can be passed multiple times.")
        command.add_argument("--allow-noop", action="store_true", help="Permit documented no-op execution for tool nodes that otherwise fail closed.")
        command.add_argument("--allow-mutation", action="store_true", help="Permit local mutating tool-node writes after action admission.")
        command.add_argument("--tool-registry", help="Tool Registry JSON path used by action-admit before mutating tool-node writes.")
        command.add_argument("--audit-trail", help="Permission Audit Trail JSON path to create or append for mutating tool-node writes.")
        command.add_argument("--human-approved", action="store_true", help="Record that a human approved the requested tool-node mutation.")
        command.add_argument("--approval-ref", help="Human approval ticket, comment, or transcript reference.")
        command.add_argument("--max-refs", type=int, default=8, help="Maximum compound-context refs for compound_preflight.")

    list_agents = subparsers.add_parser("list-agents", help=command_description("list-agents"))
    list_agents.add_argument("--json", action="store_true", help="Emit JSON.")
    list_agents.set_defaults(func=command_list_agents)

    list_phases = subparsers.add_parser("list-phases", help=command_description("list-phases"))
    list_phases.add_argument("--json", action="store_true", help="Emit JSON.")
    list_phases.set_defaults(func=command_list_phases)

    validate = subparsers.add_parser("validate-artifact", help=command_description("validate-artifact"))
    validate.add_argument("--schema", required=True, help="Schema alias or path.")
    validate.add_argument("--input", required=True, help="Artifact JSON path.")
    validate.add_argument("--json", action="store_true", help="Emit JSON.")
    validate.set_defaults(func=command_validate_artifact)

    health = subparsers.add_parser("health-check", help=command_description("health-check"))
    health.add_argument("--include-optional", action="store_true", help="Include optional audit and PDF tooling checks.")
    health.add_argument("--json", action="store_true", help="Emit JSON.")
    health.set_defaults(func=command_health_check)

    ci = subparsers.add_parser("ci", help=command_description("ci"))
    ci.add_argument(
        "--suite",
        action="append",
        choices=DEFAULT_CI_SUITE_ORDER,
        help="Run only the named suite. Can be passed multiple times. Defaults to the full canonical suite.",
    )
    ci.add_argument("--json", action="store_true", help="Emit JSON.")
    ci.set_defaults(func=command_ci)

    action_admit = subparsers.add_parser("action-admit", help=command_description("action-admit"))
    action_admit.add_argument("--tool-registry", required=True, help="Tool Registry JSON path.")
    action_admit.add_argument("--tool", required=True, help="Concrete tool name requested by the harness.")
    action_admit.add_argument("--action", required=True, help="Concrete action or operation requested for the tool.")
    action_admit.add_argument("--phase", help="Current ADLC workflow phase. Defaults to --state phase when present.")
    action_admit.add_argument("--state", help="Workflow state path used for phase, session, brief, and budget context.")
    action_admit.add_argument("--brief-id", help="Build Brief id for the permission audit trail.")
    action_admit.add_argument("--run-id", help="Durable ADLC run id for the permission audit trail when --state is not supplied.")
    action_admit.add_argument("--session-id", help="Session id for the permission audit trail.")
    action_admit.add_argument("--allow-mutation", action="store_true", help="Explicitly allow mutating or destructive tool classes.")
    action_admit.add_argument("--human-approved", action="store_true", help="Record that a human approved the requested action.")
    action_admit.add_argument("--approval-ref", help="Human approval ticket, comment, or transcript reference.")
    action_admit.add_argument("--token-budget", help="Token Budget JSON path used as a hard-stop guard.")
    action_admit.add_argument("--estimated-input-tokens", type=int, default=0, help="Projected input tokens for this action.")
    action_admit.add_argument("--expected-output-tokens", type=int, default=0, help="Projected output tokens for this action.")
    action_admit.add_argument("--skill", help="Optional skill attribution for the budget check.")
    action_admit.add_argument("--audit-trail", help="Permission Audit Trail JSON path to create or append.")
    action_admit.add_argument("--json", action="store_true", help="Emit JSON.")
    action_admit.set_defaults(func=command_action_admit)

    loop_tests = subparsers.add_parser("loop-test-selection", help=command_description("loop-test-selection"))
    loop_tests.add_argument("--loop-contract", required=True, help="Loop Contract JSON path.")
    loop_tests.add_argument("--test-plan", required=True, help=".adlc/test_plan.json-compatible path.")
    loop_tests.add_argument("--test-results", help="Loop Test Result JSON path with executed required-test evidence.")
    loop_tests.add_argument(
        "--require-test-results",
        nargs="?",
        const=True,
        default=None,
        help="Require executed Loop Test Result evidence. Optionally pass the result JSON path.",
    )
    loop_tests.add_argument("--json", action="store_true", help="Emit JSON.")
    loop_tests.set_defaults(func=command_loop_test_selection)

    loop_action = subparsers.add_parser("loop-action-validate", help=command_description("loop-action-validate"))
    loop_action.add_argument("--loop-contract", required=True, help="Loop Contract JSON path.")
    loop_action.add_argument("--action", required=True, help="Loop Action JSON path.")
    loop_action.add_argument("--state", help="Workflow state path.")
    loop_action.add_argument("--token-budget", help="Token Budget JSON path. Defaults to loop_contract.budget_guard.token_budget_ref when present.")
    loop_action.add_argument("--json", action="store_true", help="Emit JSON.")
    loop_action.set_defaults(func=command_loop_action_validate)

    loop_budget = subparsers.add_parser("loop-budget-check", help=command_description("loop-budget-check"))
    loop_budget.add_argument("--token-budget", required=True, help="Token Budget JSON path.")
    loop_budget.add_argument("--estimated-input-tokens", required=True, type=int, help="Estimated input tokens for the next LLM call.")
    loop_budget.add_argument("--expected-output-tokens", required=True, type=int, help="Expected output tokens for the next LLM call.")
    loop_budget.add_argument("--phase", help="Optional ADLC phase attribution.")
    loop_budget.add_argument("--skill", help="Optional skill attribution.")
    loop_budget.add_argument("--json", action="store_true", help="Emit JSON.")
    loop_budget.set_defaults(func=command_loop_budget_check)

    loop_maturity = subparsers.add_parser("loop-maturity-audit", help=command_description("loop-maturity-audit"))
    loop_maturity.add_argument("--loop-contract", required=True, help="Loop Contract JSON path.")
    loop_maturity.add_argument("--workflow", help="Workflow graph path.")
    loop_maturity.add_argument("--state", help="Workflow state path.")
    loop_maturity.add_argument("--test-plan", help=".adlc/test_plan.json-compatible path.")
    loop_maturity.add_argument("--test-results", help="Loop Test Result JSON path with executed required-test evidence.")
    loop_maturity.add_argument("--action", help="Optional Loop Action JSON path to include admission status.")
    loop_maturity.add_argument("--token-budget", help="Token Budget JSON path. Defaults to loop_contract.budget_guard.token_budget_ref when present.")
    loop_maturity.add_argument("--output", help="Optional output report path.")
    loop_maturity.add_argument("--json", action="store_true", help="Emit JSON.")
    loop_maturity.set_defaults(func=command_loop_maturity_audit)

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
    add_tool_phase_arguments(run)
    run.add_argument("--dry-run", action="store_true", help="Plan and advance state without invoking runtime adapters.")
    run.add_argument("--json", action="store_true", help="Emit JSON.")
    run.set_defaults(func=command_run, phase=None)

    run_phase = subparsers.add_parser("run-phase", help=command_description("run-phase"))
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
    add_tool_phase_arguments(run_phase)
    run_phase.add_argument("--dry-run", action="store_true", help="Plan and advance state without invoking runtime adapters.")
    run_phase.add_argument("--json", action="store_true", help="Emit JSON.")
    run_phase.set_defaults(func=command_run_phase)

    resume = subparsers.add_parser("resume-workflow", help=command_description("resume-workflow"))
    resume.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    resume.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    resume.add_argument("--json", action="store_true", help="Emit JSON.")
    resume.set_defaults(func=command_resume_workflow)

    compound = subparsers.add_parser("compound-context", help=command_description("compound-context"))
    compound.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    compound.add_argument("--input", help="Input file path or text used to rank learning refs.")
    compound.add_argument("--build-brief", help="Build Brief JSON path used to emit task and verifier refs.")
    compound.add_argument("--max-refs", type=int, default=8, help="Maximum learning refs to return.")
    compound.add_argument("--json", action="store_true", help="Emit JSON.")
    compound.set_defaults(func=command_compound_context)

    control_drift = subparsers.add_parser("control-plane-drift-loop", help=command_description("control-plane-drift-loop"))
    control_drift.add_argument("--brief-id", help="Brief/run identity for the dogfood loop state.")
    control_drift.add_argument("--workspace", help="Workspace or git worktree root. Defaults to cwd.")
    control_drift.add_argument("--state", help="Workflow state path. Defaults to .adlc/control_plane_drift_state.json under workspace.")
    control_drift.add_argument("--output", help="Control-plane drift report path. Defaults to .adlc/outputs/control_plane_drift_loop.json under workspace.")
    control_drift.add_argument("--target", choices=WORK_ITEM_TARGETS, default="linear", help="Work-item target used for dry-run status sync.")
    control_drift.add_argument("--existing-work-items", help="Optional read-only tracker audit JSON used for stable-ID lookup.")
    control_drift.add_argument("--verifier", action="append", default=[], help="Verifier command to run before and after repair. May be repeated.")
    control_drift.add_argument("--dry-run", action="store_true", help="Plan the dogfood loop without mutating the repair workspace.")
    control_drift.add_argument("--allow-mutation", action="store_true", help="Permit deterministic schema-alias repair after action admission.")
    control_drift.add_argument("--tool-registry", help="Tool Registry JSON path used by action-admit before mutation.")
    control_drift.add_argument("--audit-trail", help="Permission Audit Trail JSON path to create or append.")
    control_drift.add_argument("--human-approved", action="store_true", help="Record that a human approved the requested repair mutation.")
    control_drift.add_argument("--approval-ref", help="Human approval ticket, comment, or transcript reference.")
    control_drift.add_argument("--json", action="store_true", help="Emit JSON.")
    control_drift.set_defaults(func=command_control_plane_drift_loop)

    emit = subparsers.add_parser("emit-work-items", help=command_description("emit-work-items"))
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

    sync = subparsers.add_parser("sync-work-item", help=command_description("sync-work-item"))
    sync_input = sync.add_mutually_exclusive_group(required=True)
    sync_input.add_argument("--work-item", help="Work Item Sync JSON path.")
    sync_input.add_argument("--build-brief", help="Build Brief JSON path used to derive work-item sync operations.")
    sync.add_argument("--target", choices=WORK_ITEM_TARGETS, help="Work-item target. Required with --build-brief.")
    sync.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    sync.add_argument("--state", help=f"Workflow state path. Defaults to {DEFAULT_STATE_PATH} under workspace.")
    sync.add_argument("--existing-work-items", help="Optional read-only tracker audit JSON used for stable-ID lookup.")
    sync.add_argument("--dry-run", action="store_true", help="Plan sync operations without external mutation.")
    sync.add_argument("--allow-mutation", action="store_true", help="Permit local provider mutation after action admission.")
    sync.add_argument("--provider-command", help="Local provider command that accepts the sync payload on stdin.")
    sync.add_argument("--tool-registry", help="Tool Registry JSON path used by action-admit before mutation.")
    sync.add_argument("--audit-trail", help="Permission Audit Trail JSON path to create or append.")
    sync.add_argument("--human-approved", action="store_true", help="Record that a human approved the requested sync mutation.")
    sync.add_argument("--approval-ref", help="Human approval ticket, comment, or transcript reference.")
    sync.add_argument("--json", action="store_true", help="Emit JSON.")
    sync.set_defaults(func=command_sync_work_item)

    queue_status = subparsers.add_parser("queue-status", help=command_description("queue-status"))
    queue_status.add_argument("--queue", help="Work Queue JSON path. Defaults to .adlc/work_queue.json under --workspace.")
    queue_status.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    queue_status.add_argument("--json", action="store_true", help="Emit JSON.")
    queue_status.set_defaults(func=command_queue_status)

    queue_claim = subparsers.add_parser("queue-claim", help=command_description("queue-claim"))
    queue_claim.add_argument("--task-id", required=True, help="Stable queue task ID to claim.")
    queue_claim.add_argument("--agent-id", help="Agent or harness ID taking the claim.")
    queue_claim.add_argument("--worktree-ref", help="Optional worktree path/ref to record on the claim.")
    add_queue_base_arguments(queue_claim)
    queue_claim.set_defaults(func=command_queue_claim)

    queue_release = subparsers.add_parser("queue-release", help=command_description("queue-release"))
    queue_release.add_argument("--task-id", required=True, help="Stable queue task ID to release.")
    add_queue_base_arguments(queue_release)
    queue_release.set_defaults(func=command_queue_release)

    queue_complete = subparsers.add_parser("queue-complete", help=command_description("queue-complete"))
    queue_complete.add_argument("--task-id", required=True, help="Stable queue task ID to complete.")
    queue_complete.add_argument("--evidence", action="append", help="Verifier command, artifact path, or evidence ref proving completion.")
    add_queue_base_arguments(queue_complete)
    queue_complete.set_defaults(func=command_queue_complete)

    queue_block = subparsers.add_parser("queue-block", help=command_description("queue-block"))
    queue_block.add_argument("--task-id", required=True, help="Stable queue task ID to block.")
    queue_block.add_argument("--reason", required=True, help="Structured block reason.")
    queue_block.add_argument("--next-action", required=True, help="Next action needed to unblock the task.")
    queue_block.add_argument("--evidence", action="append", help="Evidence ref for the block.")
    add_queue_base_arguments(queue_block)
    queue_block.set_defaults(func=command_queue_block)

    queue_escalate = subparsers.add_parser("queue-escalate", help=command_description("queue-escalate"))
    queue_escalate.add_argument("--task-id", required=True, help="Stable queue task ID to escalate.")
    queue_escalate.add_argument("--reason", required=True, help="Structured escalation reason.")
    queue_escalate.add_argument("--next-action", required=True, help="Human action needed.")
    queue_escalate.add_argument("--evidence", action="append", help="Evidence ref for the escalation.")
    add_queue_base_arguments(queue_escalate)
    queue_escalate.set_defaults(func=command_queue_escalate)

    worktree_prepare = subparsers.add_parser("worktree-prepare", help=command_description("worktree-prepare"))
    worktree_prepare.add_argument("--task-id", required=True, help="Stable queue task ID to isolate.")
    add_queue_base_arguments(worktree_prepare)
    add_worktree_plan_arguments(worktree_prepare)
    worktree_prepare.set_defaults(func=command_worktree_prepare)

    worktree_status = subparsers.add_parser("worktree-status", help=command_description("worktree-status"))
    worktree_status.add_argument("--queue", help="Work Queue JSON path.")
    worktree_status.add_argument("--task-id", help="Optional queue task ID to inspect.")
    worktree_status.add_argument("--workspace", help="Workspace root. Defaults to cwd.")
    add_worktree_plan_arguments(worktree_status)
    worktree_status.add_argument("--json", action="store_true", help="Emit JSON.")
    worktree_status.set_defaults(func=command_worktree_status)

    worktree_cleanup = subparsers.add_parser("worktree-cleanup", help=command_description("worktree-cleanup"))
    worktree_cleanup.add_argument("--task-id", required=True, help="Stable queue task ID whose worktree should be cleaned.")
    worktree_cleanup.add_argument("--force", action="store_true", help="Force git worktree removal after explicit admission.")
    add_queue_base_arguments(worktree_cleanup)
    add_worktree_plan_arguments(worktree_cleanup)
    worktree_cleanup.set_defaults(func=command_worktree_cleanup)

    slop_gate = subparsers.add_parser("slop-gate", help=command_description("slop-gate"))
    slop_gate.add_argument("--build-brief", required=True, help="Build Brief JSON path.")
    slop_gate.add_argument("--json", action="store_true", help="Emit JSON.")
    slop_gate.set_defaults(func=command_slop_gate)

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
