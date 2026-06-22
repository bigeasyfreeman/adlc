# Agent-Native Interface

## Purpose

Define the minimum contract an external agent or orchestrator needs to discover, run, validate, and manage ADLC without hand-reading the repository.

## Machine-Readable Anchors

| Anchor | Role |
|---|---|
| `skills/manifest.json` | Agent inventory, DAG node ownership, skill bindings, labels, and runtime model map |
| `WORKFLOW.md` | Runtime backend command templates for `claude`, `codex`, `cursor`, `antigravity`, and `factory` |
| `WORKFLOW.dot` | Phase ordering and transition shape |
| `docs/schemas/*.schema.json` | Boundary validation for manifests, Build Briefs, agent outputs, workflow state, work queues, permissions, logs, and tool registry |
| `docs/solutions/` | Optional compound engineering learning store consumed as compact `learning_refs` |
| `docs/architecture/decisions/` | Optional architecture memory entries consumed and audited as boundary evidence |
| `tests/smoke/adapters/*.sh` | Runtime-specific `invoke_agent` and `preflight` adapter contracts |
| `bin/adlc` | Thin local CLI for discovery, workflow inspection, schema validation, workflow state transitions, dry-run/runtime phase execution, emitter payloads, and MCP stdio exposure |
| `docs/specs/emitter-contract.md` | Normalized work-item and document emitter contract for MCP-backed integrations |
| `docs/specs/executable-tool-nodes.md` | Deterministic tool-node execution, artifact, and fail-closed mutation contract |
| `docs/specs/control-plane-drift-loop.md` | First bounded ADLC dogfood loop for control-plane drift detection and repair |
| `docs/specs/learning-architecture-memory.md` | Learning, architecture memory, stale/overclaim, duplicate primitive, and champion/holdout contracts |
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
8. When a phase delegates decisions or actions to an LLM-driven loop, validate required-test coverage, executed required-test results, `budget_guard` evidence, action admission, and maturity evidence through the Loop Contract commands.
9. For work-item or document publishing, resolve a local MCP provider through the normalized capability bindings in `docs/specs/emitter-contract.md`.
10. Use stop reasons from `docs/specs/stop-reasons.md` and permission logging from `docs/specs/permission-logging.md` for machine-readable failure handling.

The local CLI exposes the native hooks directly:

```bash
bin/adlc list-agents --json
bin/adlc list-phases --json
bin/adlc health-check --json
bin/adlc ci --json
bin/adlc validate-artifact --schema build-brief --input .adlc/build_brief.json --json
bin/adlc run --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase triage --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase context_assembly --build-brief .adlc/build_brief.json --workspace . --json
bin/adlc run-phase qa --workspace . --verifier 'pytest tests/test_task.py' --json
bin/adlc run-phase learning_capture --input .adlc/pr_prep_output.json --workspace . --dry-run --json
bin/adlc resume-workflow --workspace . --json
bin/adlc compound-context --workspace . --build-brief .adlc/build_brief.json --json
bin/adlc architecture-memory --input .adlc/architecture_decisions.json --workspace . --dry-run --json
bin/adlc memory-health --workspace . --changed-path scripts/adlc_runtime/cli.py --primitive-proposals .adlc/primitive_proposals.json --json
bin/adlc champion-holdout --input .adlc/champion_holdout.json --json
bin/adlc control-plane-drift-loop --workspace . --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --dry-run --json
bin/adlc action-admit --tool-registry .adlc/tool_registry.json --tool Read --action read_file --phase research --brief-id BRF-123 --run-id ADLC-RUN-123 --session-id SESSION-123 --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --require-test-results .adlc/loop_test_result.json --json
bin/adlc loop-budget-check --token-budget .adlc/token_budget.json --estimated-input-tokens 2000 --expected-output-tokens 4000 --phase phase_5_codegen_context --skill codegen-context --json
bin/adlc loop-action-validate --loop-contract docs/loop-contracts/task.json --action .adlc/loop_action.json --state .adlc/workflow_state.json --token-budget .adlc/token_budget.json --json
bin/adlc loop-maturity-audit --loop-contract docs/loop-contracts/task.json --workflow WORKFLOW.dot --state .adlc/workflow_state.json --test-plan .adlc/test_plan.json --test-results .adlc/loop_test_result.json --token-budget .adlc/token_budget.json --json
bin/adlc emit-work-items --target linear --build-brief .adlc/build_brief.json --dry-run --json
bin/adlc sync-work-item --build-brief .adlc/build_brief.json --target linear --state .adlc/workflow_state.json --dry-run --json
bin/adlc sync-work-item --work-item .adlc/work_item_sync.json --state .adlc/workflow_state.json --dry-run --json
bin/adlc queue-status --queue .adlc/work_queue.json --json
bin/adlc queue-claim --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --workspace . --dry-run --json
bin/adlc queue-complete --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --evidence '.adlc/loop_test_result.json' --dry-run --json
bin/adlc queue-block --queue .adlc/work_queue.json --task-id TASK-123 --reason file_collision --next-action 'split file ownership' --dry-run --json
bin/adlc queue-escalate --queue .adlc/work_queue.json --task-id TASK-123 --reason human_review_required --next-action 'review architecture boundary' --dry-run --json
bin/adlc worktree-prepare --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc worktree-status --queue .adlc/work_queue.json --workspace . --json
bin/adlc worktree-cleanup --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc mcp-tools --json
bin/adlc mcp-serve
```

`mcp-serve` implements a minimal newline-delimited JSON-RPC stdio server with `initialize`, `tools/list`, and `tools/call` for ADLC discovery, health checks, validation, compound context preflight, architecture memory, memory health, champion/holdout evaluation, executable tool-node phase artifacts, control-plane drift dogfood, tool-registry action admission, loop test selection, loop budget checks, LLM action admission, loop maturity audit, dry-run phase execution, resume inspection, work-item emitter payload generation, work-item state synchronization, work queue status and lifecycle actions, and worktree prepare/status/cleanup. Mutating work-item emission requires explicit `allow_mutation` plus a local `provider_command`. Mutating work-item synchronization also requires `tool_registry` admission evidence before the local provider command can run. Mutating queue, worktree, tool-node, architecture-memory, and control-plane repair operations also require explicit `allow_mutation` and `tool_registry` admission evidence.

## Current Native Level

ADLC is agent-native at the contract and harness layer:

- agents are file-addressable and registered in `skills/manifest.json`
- runtime invocation is adapter-backed rather than hardcoded to one vendor
- target installs get `.adlc/bin/adlc`, a wrapper that runs this checkout's deterministic runtime through `ADLC_ROOT`
- core artifacts are schema-validated JSON
- downstream integrations are normalized around MCP provider capability bindings
- smoke and contract tests exercise the same adapter and schema surfaces an orchestrator would use
- workflow state is persisted under `.adlc/workflow_state.json` and validated against `docs/schemas/workflow-state.schema.json`
- workflow state carries durable `run_id`, `session_id`, `brief_id`, `resume_count`, and `attempt` evidence for resumable self-actioning runs
- permission audit trails and side-effect ledgers can correlate decisions and mutations back to the same run/session/brief identity
- workflow state can carry `work_item_links` so tracker items stay correlated with stable ADLC external IDs, run identity, verifier evidence, blockers, and next action across resumes
- workflow state can carry `queue_claims` and `worktree_refs` so a harness can see claimed, running, blocked, completed, escalated, and isolated work across resumes
- workflow state can carry `phase_artifacts` so a harness can inspect deterministic tool-node outputs across resumes
- `control-plane-drift-loop` provides the first bounded dogfood loop: it detects schema-alias drift, validates a repair action, applies only admitted metadata repair, reruns verifiers, syncs work state, and stops for human review
- `architecture-memory`, `memory-health`, and `champion-holdout` let a harness preserve evidence-backed architecture decisions, detect stale or overclaimed memory, block duplicate primitive proposals, and promote prompt or skill challengers only after holdout proof
- optional task-level fingerprints in workflow state let `resume-workflow` report completed, skipped, failed, and incomplete executable tasks
- optional Loop Contract fields in workflow state let `resume-workflow` report progress, no-progress count, pending control events, safe checkpoints, escalation context, and `budget_status`
- `loop-test-result` artifacts let `loop-test-selection --require-test-results` and `loop-maturity-audit --test-results` distinguish tag-only coverage from executed required-test evidence
- `compound-context` keeps prior learnings compact by passing `docs/solutions` paths, summaries, source refs, verifier refs, and stale signals rather than full notes
- work-item emitter payloads preserve ADLC artifact taxonomy, decision contracts, verifier contracts, compatibility constraints, and evidence responsibilities

ADLC now has a thin workflow orchestration API for `adlc run`, `run-phase`, `resume-workflow`, and `emit-work-items`. It is still intentionally thin: agent execution delegates to existing runtime adapters, deterministic tool nodes emit schema-backed phase artifacts, and external mutation is only available through an explicit local provider command.

## Recommended Thin Orchestrator Surface

The current thin orchestrator surface exposes:

| Command or Tool | Behavior |
|---|---|
| `list_agents` | Return agents from `skills/manifest.json` with DAG node, labels, skills, and runtime model map |
| `list_phases` | Return ordered DAG phases from `WORKFLOW.dot` |
| `validate_artifact` | Validate a named artifact against the appropriate schema |
| `health_check` | Check required runtime dependencies, schema aliases, and CLI wrapper availability |
| `compound_context` | Compute compact learning refs, graph status, task refs, verifier refs, and explicit no-op reasons |
| `architecture_memory` | Validate and optionally write evidence-backed architecture decision memory entries |
| `memory_health` | Audit learning and architecture memory for stale refs, overclaim, and duplicate primitive proposals |
| `champion_holdout` | Evaluate prompt or skill challengers against champion, holdout data, and must-pass rules |
| `control_plane_drift_loop` | Detect bounded ADLC control-plane drift, validate a repair action, optionally apply the admitted fix, verify, and stop for review |
| `loop_test_selection` | Check mandatory floor and task-signal required tests against `.adlc/test_plan.json` coverage tags, and optionally require executed `.adlc/loop_test_result.json` evidence |
| `loop_budget_check` | Check projected input/output tokens against `.adlc/token_budget.json`, then emit `budget_status`, `wrap_up`, or stop reason `budget_exhausted` |
| `loop_action_validate` | Admit, reject, or escalate an LLM-proposed action from allowed tools, required tests, state, and checkpoint evidence |
| `loop_maturity_audit` | Score loop maturity from Loop Contract, workflow, state, test-plan, executed test-result, action evidence, and budget evidence |
| `run_phase` | Invoke the configured runtime adapter for agent phases or execute deterministic tool nodes with phase artifacts |
| `resume_workflow` | Load workflow state, identify the next runnable phase, and continue |
| `emit_work_items` | Run a normalized dry-run or mutation against a configured MCP provider |
| `sync_work_item` | Find, create, or append tracker work-item state from ADLC run evidence and stable external IDs |
| `queue_status` | Inspect schema-backed queued, claimed, running, blocked, done, and escalated work |
| `queue_claim` | Claim a queued task after dirty-check and file-overlap gates pass |
| `queue_complete` | Mark a task done with required verifier or evidence refs |
| `queue_block` | Block a task with structured reason and next action |
| `queue_escalate` | Escalate a task to human review with structured reason and next action |
| `worktree_prepare` | Plan or create an isolated git worktree for a queue task after safety checks |
| `worktree_status` | Report linked task, branch/path, dirty state, and cleanup eligibility |
| `worktree_cleanup` | Remove or dry-run removal of an ADLC worktree, refusing dirty work unless explicitly forced |

The next native layer should add richer provider-specific MCP adapters and packaged loop templates. The current surface keeps ADLC easy for agents to manage while preserving the repo's existing vendor-neutral runtime adapters, executable tool-node artifacts, queue/worktree isolation substrate, and schema-first contracts.

## Executable Tool-Node Contract

`run-phase` executes deterministic tool nodes through schema-backed bindings:

- `compound_preflight` writes compact compound context refs.
- `scaffold` emits planned writes and requires action admission for file creation.
- `context_assembly` emits per-task context packages from Build Brief, queue, worktree, and tracker state.
- `qa` runs verifier commands and captures exit codes plus bounded log refs.
- `slop_gate` reuses the generated-output slop gate.
- `learning_capture` writes only verified, redacted reusable learning candidates.

Dry-run tool-node execution emits a `planned` result artifact and does not advance the phase. Non-dry-run execution advances only when the deterministic result returns a valid workflow label or unlabeled success route. Tool-node results validate against `tool-node-result` and are referenced from workflow state through `phase_artifacts[]`.

## Queue And Worktree Contract

ADLC work queues are JSON artifacts validated by `docs/schemas/work-queue.schema.json`. Each task carries a stable `task_id`, status, source ref, expected path ownership, optional verifier refs, optional tracker external ID, and optional claim/worktree metadata.

The queue substrate is deterministic:

- `queue-claim` requires a queued task, a clean git workspace, and no overlap with active `claimed` or `running` task paths.
- File ownership is compared through normalized file, directory, and glob path entries.
- `queue-complete` requires evidence when a task declares verifier refs or `evidence_required`.
- `queue-block` and `queue-escalate` require structured reasons and next actions.
- `worktree-prepare` refuses dirty source checkouts and path overlap before planning or creating a git worktree.
- `worktree-cleanup` refuses dirty target worktrees unless an explicit force path is used.

Dry-run is the default because these commands are designed for harnesses and LLMs to inspect first. Write mode requires `--allow-mutation` and action admission through a tool registry entry such as `adlc-queue` or `adlc-worktree`. Queue/worktree state remains ADLC-owned; tracker items from `work_item_links[]` can mirror task state but are not the source of truth.
