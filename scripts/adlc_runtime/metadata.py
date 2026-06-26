"""Stable ADLC runtime metadata shared by CLI and MCP surfaces."""

from __future__ import annotations

from typing import Dict


SCHEMA_ALIASES = {
    "applicability-manifest": "docs/schemas/applicability-manifest.schema.json",
    "architecture-memory-report": "docs/schemas/architecture-memory-report.schema.json",
    "build-brief": "docs/schemas/build-brief.schema.json",
    "beads-status-report": "docs/schemas/beads-status-report.schema.json",
    "champion-holdout-report": "docs/schemas/champion-holdout-report.schema.json",
    "coder-output": "docs/schemas/coder-output.schema.json",
    "control-plane-drift-report": "docs/schemas/control-plane-drift-report.schema.json",
    "council-verdict": "docs/schemas/council-verdict-output.schema.json",
    "eval-council-verdict": "docs/schemas/eval-council-verdict.schema.json",
    "learning-entry": "docs/schemas/learning-entry.schema.json",
    "loop-action": "docs/schemas/loop-action.schema.json",
    "loop-contract": "docs/schemas/loop-contract.schema.json",
    "loop-design": "docs/schemas/loop-design.schema.json",
    "loop-design-validation-report": "docs/schemas/loop-design-validation-report.schema.json",
    "loop-maturity-report": "docs/schemas/loop-maturity-report.schema.json",
    "meta-harness-plan-report": "docs/schemas/meta-harness-plan-report.schema.json",
    "loop-template-catalog": "docs/schemas/loop-template-catalog.schema.json",
    "loop-template-install-report": "docs/schemas/loop-template-install-report.schema.json",
    "loop-test-result": "docs/schemas/loop-test-result.schema.json",
    "looper-status-report": "docs/schemas/looper-status-report.schema.json",
    "memory-health-report": "docs/schemas/memory-health-report.schema.json",
    "permission-audit-trail": "docs/schemas/permission-audit-trail.schema.json",
    "prd-template": "docs/schemas/prd-template.schema.json",
    "repo-map": "docs/schemas/repo-map.schema.json",
    "security-assessment": "docs/schemas/security-assessment.schema.json",
    "session-state": "docs/schemas/session-state.schema.json",
    "streaming-events": "docs/schemas/streaming-events.schema.json",
    "system-log": "docs/schemas/system-log.schema.json",
    "test-author-output": "docs/schemas/test-author-output.schema.json",
    "test-strength-output": "docs/schemas/test-strength-output.schema.json",
    "token-budget": "docs/schemas/token-budget.schema.json",
    "tool-node-result": "docs/schemas/tool-node-result.schema.json",
    "tool-registry": "docs/schemas/tool-registry.schema.json",
    "triage-output": "docs/schemas/triage-output.schema.json",
    "work-item-sync": "docs/schemas/work-item-sync.schema.json",
    "work-queue": "docs/schemas/work-queue.schema.json",
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
    "scaffold": "Read,Write,Bash,Glob,Grep",
    "gen_tests": "Read,Write,Bash",
    "context_assembly": "Read,Bash,Glob,Grep",
    "code": "Read,Write,Edit,Bash,Glob,Grep",
    "code_review": "Read",
    "security": "Read,Bash,Glob,Grep",
    "qa": "Read,Bash,Glob,Grep",
    "test_strength": "Read,Bash",
    "slop_gate": "Read,Bash",
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
    "ci": {
        "mcp_name": "adlc_ci",
        "description": "Run the canonical local ADLC verification suite and emit a structured summary.",
    },
    "action-admit": {
        "mcp_name": "adlc_action_admit",
        "description": "Admit, deny, or escalate a concrete tool action against the ADLC tool registry and permission policy.",
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
    "sync-work-item": {
        "mcp_name": "adlc_sync_work_item",
        "description": "Find, create, or append tracker work-item state from ADLC run evidence with guarded provider mutation.",
    },
    "queue-status": {
        "mcp_name": "adlc_queue_status",
        "description": "Inspect schema-backed ADLC work queue status, active claims, and blocked or completed work.",
    },
    "queue-claim": {
        "mcp_name": "adlc_queue_claim",
        "description": "Claim an ADLC queued task after deterministic dirty-state and file-overlap checks.",
    },
    "queue-release": {
        "mcp_name": "adlc_queue_release",
        "description": "Release a claimed ADLC queue task back to queued state with mutation evidence.",
    },
    "queue-complete": {
        "mcp_name": "adlc_queue_complete",
        "description": "Mark an ADLC queue task done with required verifier or evidence references.",
    },
    "queue-block": {
        "mcp_name": "adlc_queue_block",
        "description": "Block an ADLC queue task with a structured reason and next action.",
    },
    "queue-escalate": {
        "mcp_name": "adlc_queue_escalate",
        "description": "Escalate an ADLC queue task to human review with a structured reason and next action.",
    },
    "worktree-prepare": {
        "mcp_name": "adlc_worktree_prepare",
        "description": "Prepare or dry-run an isolated git worktree for a claimed queue task after safety checks.",
    },
    "worktree-status": {
        "mcp_name": "adlc_worktree_status",
        "description": "Inspect ADLC-linked git worktrees, queue task refs, dirty state, and cleanup eligibility.",
    },
    "worktree-cleanup": {
        "mcp_name": "adlc_worktree_cleanup",
        "description": "Remove or dry-run cleanup of an ADLC git worktree, refusing dirty work unless explicitly forced.",
    },
    "compound-context": {
        "mcp_name": "adlc_compound_context",
        "description": "Compute compact compound engineering context from docs/solutions, Graphify status, and optional Build Brief tasks.",
    },
    "architecture-memory": {
        "mcp_name": "adlc_architecture_memory",
        "description": "Validate and optionally write evidence-backed architecture decision memory entries.",
    },
    "memory-health": {
        "mcp_name": "adlc_memory_health",
        "description": "Audit learning and architecture memory for stale evidence, overclaim, and duplicate primitive risks.",
    },
    "beads-status": {
        "mcp_name": "adlc_beads_status",
        "description": "Read-only preflight of optional Beads (bd) task-graph integration; reports availability without mutation.",
    },
    "champion-holdout": {
        "mcp_name": "adlc_champion_holdout",
        "description": "Evaluate a prompt or skill challenger against champion and holdout scores before promotion.",
    },
    "loop-library": {
        "mcp_name": "adlc_loop_library",
        "description": "List or inspect packaged ADLC loop templates with required skills, gates, schemas, and installable contracts.",
    },
    "loop-template-install": {
        "mcp_name": "adlc_loop_template_install",
        "description": "Dry-run or install a packaged ADLC loop template into a workspace with schema-backed contracts and action admission.",
    },
    "meta-harness-plan": {
        "mcp_name": "adlc_meta_harness_plan",
        "description": "Rank repo, ticket, and signal candidates into a bounded ADLC meta-harness execution plan without dispatching agents.",
    },
    "control-plane-drift-loop": {
        "mcp_name": "adlc_control_plane_drift_loop",
        "description": "Run the first ADLC dogfood loop: detect control-plane drift, validate a repair action, optionally apply a guarded fix, verify, and stop for human review.",
    },
    "slop-gate": {
        "mcp_name": "adlc_slop_gate",
        "description": "Validate generated-output slop quality gate contracts for a Build Brief.",
    },
    "loop-test-selection": {
        "mcp_name": "adlc_loop_test_selection",
        "description": "Validate Loop Contract required tests and optionally require executed result evidence.",
    },
    "looper-status": {
        "mcp_name": "adlc_looper_status",
        "description": "Read-only preflight of optional Looper loop-design integration; reports availability without mutation.",
    },
    "loop-design-validate": {
        "mcp_name": "adlc_loop_design_validate",
        "description": "Validate a Looper-compatible ADLC Loop Design Contract before packaging or execution.",
    },
    "loop-contract-from-design": {
        "mcp_name": "adlc_loop_contract_from_design",
        "description": "Convert a validated Loop Design Contract into an ADLC Loop Contract artifact.",
    },
    "loop-action-validate": {
        "mcp_name": "adlc_loop_action_validate",
        "description": "Validate an LLM-proposed loop action against allowed tools, required tests, control events, and safe checkpoints.",
    },
    "loop-budget-check": {
        "mcp_name": "adlc_loop_budget_check",
        "description": "Evaluate a projected LLM loop action against a local token budget before the next model call.",
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
