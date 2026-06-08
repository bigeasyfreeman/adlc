"""Stable ADLC runtime metadata shared by CLI and MCP surfaces."""

from __future__ import annotations

from typing import Dict


SCHEMA_ALIASES = {
    "applicability-manifest": "docs/schemas/applicability-manifest.schema.json",
    "build-brief": "docs/schemas/build-brief.schema.json",
    "coder-output": "docs/schemas/coder-output.schema.json",
    "council-verdict": "docs/schemas/council-verdict-output.schema.json",
    "loop-action": "docs/schemas/loop-action.schema.json",
    "loop-contract": "docs/schemas/loop-contract.schema.json",
    "loop-maturity-report": "docs/schemas/loop-maturity-report.schema.json",
    "loop-test-result": "docs/schemas/loop-test-result.schema.json",
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
    "compound_preflight": "Read,Bash,Glob,Grep",
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
    "learning_capture": "Read,Write,Bash,Glob,Grep",
}

COMMAND_METADATA = {
    "list-agents": {
        "mcp_name": "adlc_list_agents",
        "description": "List ADLC agents from skills/manifest.json.",
    },
    "list-phases": {
        "mcp_name": "adlc_list_phases",
        "description": "List ADLC workflow nodes and edges from WORKFLOW.dot.",
    },
    "validate-artifact": {
        "mcp_name": "adlc_validate_artifact",
        "description": "Validate an ADLC artifact JSON file against a known schema alias or schema path.",
    },
    "health-check": {
        "mcp_name": "adlc_health_check",
        "description": "Check deterministic ADLC runtime dependencies, schema aliases, and CLI wrapper availability.",
    },
    "run-phase": {
        "mcp_name": "adlc_run_phase",
        "description": "Run or dry-run one ADLC workflow phase and persist workflow state.",
    },
    "resume-workflow": {
        "mcp_name": "adlc_resume_workflow",
        "description": "Load ADLC workflow state, increment resume_count, and return the next runnable action.",
    },
    "emit-work-items": {
        "mcp_name": "adlc_emit_work_items",
        "description": "Create a normalized ADLC work-item emitter payload, with explicit opt-in local provider mutation.",
    },
    "compound-context": {
        "mcp_name": "adlc_compound_context",
        "description": "Compute compact compound engineering context from docs/solutions, Graphify status, and optional Build Brief tasks.",
    },
    "slop-gate": {
        "mcp_name": "adlc_slop_gate",
        "description": "Validate generated-output slop quality gate contracts for a Build Brief.",
    },
    "loop-test-selection": {
        "mcp_name": "adlc_loop_test_selection",
        "description": "Validate Loop Contract required tests and optionally require executed result evidence.",
    },
    "loop-action-validate": {
        "mcp_name": "adlc_loop_action_validate",
        "description": "Validate an LLM-proposed loop action against allowed tools, required tests, control events, and safe checkpoints.",
    },
    "loop-maturity-audit": {
        "mcp_name": "adlc_loop_maturity_audit",
        "description": "Score loop-system maturity from a Loop Contract plus workflow, state, test-plan, test-result, and action evidence.",
    },
}


def command_metadata(cli_name: str) -> Dict[str, str]:
    return COMMAND_METADATA[cli_name]


def command_description(cli_name: str) -> str:
    return command_metadata(cli_name)["description"]


def command_mcp_name(cli_name: str) -> str:
    return command_metadata(cli_name)["mcp_name"]
