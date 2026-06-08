# Agent-Native Interface

## Purpose

Define the minimum contract an external agent or orchestrator needs to discover, run, validate, and manage ADLC without hand-reading the repository.

## Machine-Readable Anchors

| Anchor | Role |
|---|---|
| `skills/manifest.json` | Agent inventory, DAG node ownership, skill bindings, labels, and runtime model map |
| `WORKFLOW.md` | Runtime backend command templates for `claude`, `codex`, `cursor`, `antigravity`, and `factory` |
| `WORKFLOW.dot` | Phase ordering and transition shape |
| `docs/schemas/*.schema.json` | Boundary validation for manifests, Build Briefs, agent outputs, workflow state, permissions, logs, and tool registry |
| `docs/solutions/` | Optional compound engineering learning store consumed as compact `learning_refs` |
| `tests/smoke/adapters/*.sh` | Runtime-specific `invoke_agent` and `preflight` adapter contracts |
| `bin/adlc` | Thin local CLI for discovery, workflow inspection, schema validation, workflow state transitions, dry-run/runtime phase execution, emitter payloads, and MCP stdio exposure |
| `docs/specs/emitter-contract.md` | Normalized work-item and document emitter contract for MCP-backed integrations |
| `.adlc/` | Per-run workspace state and artifacts such as `test_plan.json`, `loop_test_result.json`, `pre_change_run.txt`, and `test_strength_report.json` |

## Quick Hook Contract

An orchestrating agent can integrate with ADLC by following this sequence:

1. Read `skills/manifest.json` to discover agents, DAG nodes, labels, skills, and runtime-specific model mappings.
2. Read `WORKFLOW.dot` or `WORKFLOW.md` to order phases and select the runtime backend.
3. Set `ADLC_RUNTIME` and run the matching adapter preflight from `tests/smoke/stages/_invoke.sh`.
4. Invoke each agent through the runtime adapter command shape in `WORKFLOW.md`.
5. Run `bin/adlc compound-context` before research to collect compact learning refs, task refs, verifier refs, graph status, and no-op reasons.
6. Validate every phase output against the matching schema in `docs/schemas/` before advancing.
7. Persist phase artifacts under `.adlc/` using the schema-backed filenames expected by downstream agents.
8. When a phase delegates decisions or actions to an LLM-driven loop, validate required-test coverage, executed required-test results, action admission, and maturity evidence through the Loop Contract commands.
9. For work-item or document publishing, resolve a local MCP provider through the normalized capability bindings in `docs/specs/emitter-contract.md`.
10. Use stop reasons from `docs/specs/stop-reasons.md` and permission logging from `docs/specs/permission-logging.md` for machine-readable failure handling.

The local CLI exposes the native hooks directly:

```bash
bin/adlc list-agents --json
bin/adlc list-phases --json
bin/adlc health-check --json
bin/adlc validate-artifact --schema build-brief --input .adlc/build_brief.json --json
bin/adlc run --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase triage --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc resume-workflow --workspace . --json
bin/adlc compound-context --workspace . --build-brief .adlc/build_brief.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --require-test-results .adlc/loop_test_result.json --json
bin/adlc loop-action-validate --loop-contract docs/loop-contracts/task.json --action .adlc/loop_action.json --state .adlc/workflow_state.json --json
bin/adlc loop-maturity-audit --loop-contract docs/loop-contracts/task.json --workflow WORKFLOW.dot --state .adlc/workflow_state.json --test-plan .adlc/test_plan.json --test-results .adlc/loop_test_result.json --json
bin/adlc emit-work-items --target linear --build-brief .adlc/build_brief.json --dry-run --json
bin/adlc mcp-tools --json
bin/adlc mcp-serve
```

`mcp-serve` implements a minimal newline-delimited JSON-RPC stdio server with `initialize`, `tools/list`, and `tools/call` for ADLC discovery, health checks, validation, compound context preflight, loop test selection, LLM action admission, loop maturity audit, dry-run phase execution, resume inspection, and work-item emitter payload generation. Mutating work-item emission requires explicit `allow_mutation` plus a local `provider_command`.

## Current Native Level

ADLC is agent-native at the contract and harness layer:

- agents are file-addressable and registered in `skills/manifest.json`
- runtime invocation is adapter-backed rather than hardcoded to one vendor
- target installs get `.adlc/bin/adlc`, a wrapper that runs this checkout's deterministic runtime through `ADLC_ROOT`
- core artifacts are schema-validated JSON
- downstream integrations are normalized around MCP provider capability bindings
- smoke and contract tests exercise the same adapter and schema surfaces an orchestrator would use
- workflow state is persisted under `.adlc/workflow_state.json` and validated against `docs/schemas/workflow-state.schema.json`
- optional task-level fingerprints in workflow state let `resume-workflow` report completed, skipped, failed, and incomplete executable tasks
- optional Loop Contract fields in workflow state let `resume-workflow` report progress, no-progress count, pending control events, safe checkpoints, and escalation context
- `loop-test-result` artifacts let `loop-test-selection --require-test-results` and `loop-maturity-audit --test-results` distinguish tag-only coverage from executed required-test evidence
- `compound-context` keeps prior learnings compact by passing `docs/solutions` paths, summaries, source refs, verifier refs, and stale signals rather than full notes
- work-item emitter payloads preserve ADLC artifact taxonomy, decision contracts, verifier contracts, compatibility constraints, and evidence responsibilities

ADLC now has a thin workflow orchestration API for `adlc run`, `run-phase`, `resume-workflow`, and `emit-work-items`. It is still intentionally thin: agent execution delegates to existing runtime adapters, deterministic tool nodes only transition state in this slice, and external mutation is only available through an explicit local provider command.

## Recommended Thin Orchestrator Surface

The current thin orchestrator surface exposes:

| Command or Tool | Behavior |
|---|---|
| `list_agents` | Return agents from `skills/manifest.json` with DAG node, labels, skills, and runtime model map |
| `list_phases` | Return ordered DAG phases from `WORKFLOW.dot` |
| `validate_artifact` | Validate a named artifact against the appropriate schema |
| `health_check` | Check required runtime dependencies, schema aliases, and CLI wrapper availability |
| `compound_context` | Compute compact learning refs, graph status, task refs, verifier refs, and explicit no-op reasons |
| `loop_test_selection` | Check mandatory floor and task-signal required tests against `.adlc/test_plan.json` coverage tags, and optionally require executed `.adlc/loop_test_result.json` evidence |
| `loop_action_validate` | Admit, reject, or escalate an LLM-proposed action from allowed tools, required tests, state, and checkpoint evidence |
| `loop_maturity_audit` | Score loop maturity from Loop Contract, workflow, state, test-plan, executed test-result, and action evidence |
| `run_phase` | Invoke the configured runtime adapter for a single DAG phase |
| `resume_workflow` | Load workflow state, identify the next runnable phase, and continue |
| `emit_work_items` | Run a normalized dry-run or mutation against a configured MCP provider |

The next native layer should add deterministic implementations for tool nodes (`scaffold`, `context_assembly`, `qa`, `slop_gate`) and richer provider-specific MCP adapters. The current surface keeps ADLC easy for agents to manage while preserving the repo's existing vendor-neutral runtime adapters and schema-first contracts.
