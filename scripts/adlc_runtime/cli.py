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
        next_action = resume_next_action_payload(state)
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
        "phase": state["phase"],
        "status": state["status"],
        "node": node_by_id.get(state["phase"]),
        "runnable": state["status"] == "planned" and state["phase"] not in {"done", "escalate"},
        "task_resume_status": task_fingerprint_summary(state),
        "loop_progress": state.get("loop_progress"),
        "no_progress_count": state.get("no_progress_count", 0),
        "control_events": state.get("control_events", []),
        "safe_checkpoint": state.get("safe_checkpoint"),
        "escalation_context": state.get("escalation_context"),
        "budget_status": state.get("budget_status"),
    }


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
    entry: Dict[str, Any],
    patterns: Iterable[str],
) -> Dict[str, Any]:
    pattern_list = sorted(set(pattern for pattern in patterns if pattern))
    return {
        "session_id": session_id,
        "brief_id": brief_id,
        "entries": [entry],
        "denial_summary": {
            "count": 0 if entry["decision"] == "approved" else 1,
            "patterns": pattern_list,
        },
    }


def merged_permission_audit_trail(path: Path, new_trail: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return new_trail
    errors = validate_artifact(resolve_schema("permission-audit-trail"), path)
    if errors:
        raise ValueError("permission audit trail failed schema validation: " + "; ".join(errors))
    existing = read_json(path)
    if existing.get("session_id") != new_trail["session_id"] or existing.get("brief_id") != new_trail["brief_id"]:
        raise ValueError("permission audit trail session_id and brief_id must match appended entry")
    entries = [*existing.get("entries", []), *new_trail["entries"]]
    patterns = set(existing.get("denial_summary", {}).get("patterns", []))
    patterns.update(new_trail.get("denial_summary", {}).get("patterns", []))
    return {
        "session_id": new_trail["session_id"],
        "brief_id": new_trail["brief_id"],
        "entries": entries,
        "denial_summary": {
            "count": sum(1 for entry in entries if entry.get("decision") != "approved"),
            "patterns": sorted(patterns),
        },
    }


def write_permission_audit_trail(path: Path, trail: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trail, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_artifact(resolve_schema("permission-audit-trail"), path)
    if errors:
        raise ValueError("permission audit trail failed schema validation: " + "; ".join(errors))


def action_admit_payload(
    tool_registry_path: Path,
    tool_name: str,
    action: str,
    phase: str | None = None,
    state_path: Path | None = None,
    brief_id: str | None = None,
    session_id: str | None = None,
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
    entry: Dict[str, Any] = {
        "decision_id": "decision:" + stable_hash("|".join([effective_session_id, effective_brief_id, tool_name, action, effective_phase, timestamp])),
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
    if approval_ref:
        entry["human_approval_ref"] = approval_ref
    if budget_status and budget_status.get("token_budget_ref"):
        entry["budget_status_ref"] = str(budget_status["token_budget_ref"])

    trail = permission_audit_trail_for_entry(
        effective_session_id,
        effective_brief_id,
        entry,
        (issue["rule"] for issue in issues),
    )
    if audit_trail_path:
        trail = merged_permission_audit_trail(audit_trail_path, trail)
        write_permission_audit_trail(audit_trail_path, trail)

    payload: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "status": status,
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
        next_action = resume_next_action_payload(state)
        state.setdefault("checkpoint", {})["next_action"] = next_action
        save_workflow_state(state_path, state)
        return tool_result({"state_path": rel_path(state_path), "state": state, "next_action": next_action})
    if name == "adlc_compound_context":
        args = argparse.Namespace(
            workspace=arguments.get("workspace"),
            input=arguments.get("input"),
            build_brief=arguments.get("build_brief"),
            max_refs=arguments.get("max_refs", 8),
            json=True,
        )
        return tool_result(compound_context_payload(args))
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
