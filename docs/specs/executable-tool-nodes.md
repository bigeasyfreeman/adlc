# Executable Tool Nodes

## Purpose

ADLC tool nodes are deterministic harness steps. They do not ask an LLM whether the phase is done. They execute a bound local command or runtime function, emit a schema-backed result artifact, update workflow state with the artifact reference, and fail closed when required inputs or mutation admission are missing.

## Contract

Every executable tool-node result validates against `docs/schemas/tool-node-result.schema.json` and includes:

- phase, status, label, and run identity
- dry-run flag
- bounded inputs and outputs
- evidence refs
- warnings and structured issues
- `skip_reason` for skipped phases
- `stop_reason` for blocked or failed phases

Workflow state stores phase artifact refs in `phase_artifacts[]`. Harnesses should read those refs instead of scraping terminal output.

## Bound Nodes

| Node | Binding |
|---|---|
| `compound_preflight` | Runs `compound-context` and emits compact learning, graph, task, and verifier refs. |
| `scaffold` | Emits deterministic planned writes from Build Brief tasks. Write mode requires action admission. |
| `context_assembly` | Emits per-task context packages with intent, constraints, target files, verifier commands, queue claims, worktrees, and tracker refs. |
| `qa` | Runs required verifier commands and captures exit codes plus bounded log refs. |
| `slop_gate` | Reuses the deterministic generated-output slop gate. |
| `learning_capture` | Writes only verified, redacted reusable learning candidates and validates each entry. |

## Mutation Rules

Dry-run tool-node execution writes only ADLC state and phase artifacts. It does not claim a phase is complete.

Mutating tool-node work requires:

- `--allow-mutation`
- `--tool-registry`
- action admission for `adlc-tool-node`
- workflow run identity
- queue/worktree safety where the phase writes task-scoped project files

Missing admission returns `action_not_admitted`. Missing tool bindings return `missing_tool_binding`. Missing QA verifier commands return `missing_verifier_command`.

## Harness Flow

```bash
bin/adlc queue-claim --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc worktree-prepare --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc run-phase context_assembly --build-brief .adlc/build_brief.json --workspace . --json
bin/adlc run-phase qa --workspace . --verifier 'pytest tests/test_task.py' --json
bin/adlc queue-complete --queue .adlc/work_queue.json --task-id TASK-123 --evidence .adlc/outputs/qa.json --dry-run --json
bin/adlc sync-work-item --state .adlc/workflow_state.json --work-item .adlc/work_item_sync.json --dry-run --json
```

Tool nodes do not schedule themselves and do not choose the next task. A harness or human decides which phase to run; ADLC proves what the phase did.
