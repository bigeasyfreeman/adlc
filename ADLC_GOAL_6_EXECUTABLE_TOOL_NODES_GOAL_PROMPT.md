# ADLC Goal 6: Executable Tool Nodes

You are Codex working in the ADLC repository. This is Goal 6 of the ADLC loop-system maturity productionization sequence.

This prompt is a local execution artifact. Do not include this prompt file in the production commit unless the user explicitly asks. Commit only production runtime, schema, tests, and docs needed by the shipped tool.

Remote sync boundary: the remote branch should contain only the productionized working ADLC. Keep `graphify-out/` and local prompt artifacts local, even when they are useful for the run. Do not push Graphify output, one-off audits, or local execution prompts as part of Goal 6 closeout.

## Current Shipped Baseline

Treat these as already shipped and do not redo them unless a regression requires a small compatibility fix.

- Goal 1, commit `0a36ff2`: ADLC control-plane verification.
  - `bin/adlc ci --json`
  - workflow-state phase parity in health-check
  - Build Brief schema compatibility
  - agent-native interface metadata
- Goal 2, commit `0b5109e`: ADLC action admission gate.
  - `bin/adlc action-admit`
  - MCP `adlc_action_admit`
  - tool-registry workflow/legacy phase admission
  - permission-audit-trail escalation/runtime evidence
  - CLI and contract tests
- Goal 3, commit `0908a7a`: Durable ADLC run identity and resumable state.
  - stable `run_id`, `session_id`, and `brief_id` evidence
  - resume continuity with explicit resume/attempt metadata
  - side-effect and permission-audit correlation
  - idempotency and stop-reason evidence
- Goal 4, commit `3d71292`: ADLC ticket state synchronization.
  - `bin/adlc sync-work-item`
  - MCP `adlc_sync_work_item`
  - schema-backed work-item sync payloads
  - `work_item_links[]` correlation in workflow state
  - side-effect and permission-audit evidence for dry-run and guarded mutation
  - stable work-item external IDs and idempotency keys
- Goal 5, commit `cecf325`: ADLC worktree and queue substrate.
  - `docs/schemas/work-queue.schema.json`
  - `queue-status`, `queue-claim`, `queue-release`, `queue-complete`, `queue-block`, and `queue-escalate`
  - `worktree-prepare`, `worktree-status`, and `worktree-cleanup`
  - dirty checkout and file-overlap guards
  - `queue_claims[]` and `worktree_refs[]` in workflow state
  - MCP exposure for queue and worktree operations

## Objective

Turn ADLC workflow tool nodes from described steps into runnable harness steps. ADLC should be able to run deterministic workflow phases, produce machine-readable phase artifacts, validate those artifacts, and fail closed when a tool node is missing a binding, missing required inputs, unsafe to mutate, or unable to prove its output.

The end state is:

- `bin/adlc run-phase <tool-node>` executes deterministic tool node behavior instead of only advancing workflow state
- tool-node dry-runs produce explicit execution plans, not fake completions
- tool-node write paths require the same action-admission, side-effect, and permission-audit discipline established in Goals 2-5
- every deterministic phase emits a stable artifact under `.adlc/` or a caller-provided output path
- emitted artifacts are schema-backed and referenced from workflow state
- `scaffold`, `context_assembly`, `qa`, `slop_gate`, and `learning_capture` have real deterministic bindings
- existing `compound_preflight` and `slop-gate` behavior remains compatible and is wired through the same phase-runner artifact path
- a harness can run a workflow phase and inspect output JSON without reading chat transcripts
- `bin/adlc ci --json` passes

## Design Boundary

This goal is the executable deterministic node layer. It is not the first dogfood repair loop and it is not the broader self-actioning meta-harness.

In scope:

- deterministic command bindings for workflow tool nodes
- phase artifact schemas and fixture coverage
- `run-phase` behavior changes for tool nodes
- workflow-state references to phase artifacts and execution results
- queue/worktree-aware safety for tool nodes that write files
- action admission for mutating tool-node operations
- side-effect and permission-audit evidence for mutating tool-node operations
- MCP and docs updates for harness consumption
- focused CLI, contract, fixture, and dry-run/write-intent tests

Out of scope:

- broad task-candidate discovery, ranking, or autonomous dispatch
- scheduled loops, cron, daemons, auto-merge, deploy, or irreversible provider actions
- first ADLC dogfood repair loop
- learning memory refresh, architecture decision memory, or champion/holdout prompt loops
- packaged loop library
- live external provider mutations beyond existing Goal 4 sync boundaries
- large scaffolding generators that create application code outside a claimed queue/worktree context

Goal 6's exit gate is narrow: ADLC can run a workflow phase and produce machine-readable outputs instead of only advancing state.

## Required Preflight

1. Inspect branch and worktree.

```bash
git status --short --branch
git log --oneline -8
```

Preserve unrelated user changes. Do not delete, revert, or rewrite untracked prompt artifacts or `graphify-out/`.

2. Read Graphify before source search.

```bash
sed -n '1,220p' graphify-out/GRAPH_REPORT.md
graphify query "ADLC executable tool nodes run-phase scaffold context_assembly qa slop_gate learning_capture workflow state phase artifacts MCP" --budget 3000
```

If the graph is stale, note that and run the no-cost update command after production code/doc changes:

```bash
graphify update .
```

Do not run `graphify . --update` for this goal. In this environment that path can invoke Graphify's semantic LLM extraction and ask for provider-specific API keys unrelated to the active coding-agent runtime. ADLC does not require those keys. If Graphify asks for an unrelated provider key, stop that command, record it as a Graphify invocation mismatch, and continue with AST-only `graphify update .` plus repo-local validation evidence.

3. Inspect current phase-runner, workflow binding, tool-node docs, schemas, and Goal 5 queue/worktree surfaces before editing.

```bash
rg -n "run-phase|run_phase|node_type|tool node|compound_preflight|scaffold|context_assembly|qa|slop_gate|learning_capture|queue_claims|worktree_refs|action-admit|side_effect|permission_audit|mcp-tools" scripts docs/schemas docs/specs tests README.md WORKFLOW.md WORKFLOW.dot
```

4. Run the current canonical gate before editing.

```bash
bin/adlc ci --json
```

If it fails, capture the exact failure and decide whether it is a pre-existing blocker or part of this goal.

## Implementation Order

### 1. Tool-Node Execution Contract

Define the common contract for deterministic phase execution.

Required behavior:

- every executable tool node has an explicit binding discoverable from `WORKFLOW.md`, CLI metadata, or a small internal registry that is tested against `WORKFLOW.dot`
- missing tool-node command bodies fail closed with a structured reason such as `missing_tool_binding`
- `run-phase --dry-run` returns an execution plan and does not mark the node completed unless the caller explicitly asks for state planning only
- non-dry-run `run-phase` executes deterministic tool-node behavior for tool nodes instead of treating all tool nodes as automatic dry-runs
- tool-node output includes `contract_version`, `phase`, `status`, `label`, `run_identity`, `inputs`, `outputs`, `evidence_refs`, `warnings`, and `stop_reason` when blocked or failed
- successful tool-node output writes a stable artifact path, defaulting to `.adlc/outputs/<phase>.json`
- failed or blocked tool-node output is still machine-readable and includes the reason needed for queue block, ticket sync, or human escalation
- workflow state records the phase artifact reference and execution status without duplicating full logs

Do not let an LLM infer a tool node's completion. Completion must come from the deterministic command result and schema-valid artifact.

### 2. Artifact Schemas

Add schema coverage before relying on new phase outputs.

Required artifacts:

- a shared tool-node result schema, or equivalent phase-specific schemas with a common envelope
- scaffold plan/result artifact
- context assembly artifact
- QA result artifact
- learning capture result artifact
- slop gate artifact compatibility with the existing `slop-gate` payload

Required behavior:

- schema validation rejects missing phase identity, missing status, missing artifact refs, malformed run identity, unsupported labels, and missing evidence for pass/fail claims
- skipped phases must include a deterministic `skip_reason`
- failed phases must include a deterministic `stop_reason`
- output paths are relative to the workspace or explicitly marked absolute only when unavoidable
- artifacts can be consumed by `resume-workflow`, tracker sync, queue completion/block/escalation, and Goal 7 dogfood loops

Prefer optional schema fields over breaking existing fixtures. Do not remove support for existing Goal 1-5 workflow state.

### 3. Scaffold Node

Make `scaffold` produce a deterministic scaffold plan and guarded write path.

Required behavior:

- consumes Build Brief, workflow state, optional queue task, and optional worktree ref
- dry-run emits the files/directories/templates it would create, why each exists, and which task or interface contract owns it
- write mode requires `--allow-mutation`, action admission, a clean claimed queue task when task-scoped writes are requested, and a clean worktree when a worktree ref is supplied
- generated file paths must stay inside the workspace and should be derived from Build Brief tasks or implementation-interface contracts
- unsafe or unclaimed writes fail closed with `missing_queue_claim`, `dirty_checkout`, `dirty_worktree`, `file_overlap`, or `action_not_admitted`
- output includes side-effect and permission-audit references for write intent

Do not add a broad application generator. Goal 6 only needs the deterministic scaffold harness and artifact shape needed by downstream agents.

### 4. Context Assembly Node

Make `context_assembly` produce per-task context packages.

Required behavior:

- consumes Build Brief, workflow state, optional queue task, optional work-item link, optional Graphify freshness status, and verifier refs
- emits one context package per task or per claimed task, with deterministic ordering
- inlines only task-relevant evidence: intent, constraints, target files, graph refs, paved-road refs, implementation-interface contracts, productionization gates, verifiers, compatibility constraints, queue/worktree identity, and tracker state refs
- output is bounded and uses artifact refs for large logs or docs
- missing required inputs fail closed with structured reasons
- no generated coding prompt should rely on chat history for core task context

The result should let a coding agent start from the context artifact and the claimed worktree without re-reading the whole repo.

### 5. QA Node

Make `qa` execute verifiers and emit a machine-readable result.

Required behavior:

- consumes verifier commands from Build Brief, workflow state, CLI flags, or environment in a documented precedence order
- runs lint/test/build commands deterministically with captured exit codes, bounded stdout/stderr excerpts, and artifact refs for full logs when needed
- missing verifier commands fail closed unless the caller explicitly sets a documented `--allow-noop` or equivalent test-only no-op path
- pass requires every required verifier to exit 0
- fail includes failing command, exit code, evidence refs, and suggested queue transition metadata
- output can be used as evidence for `queue-complete`, `sync-work-item`, and `resume-workflow`
- command execution must not require a live LLM provider

Do not claim QA passed from a dry-run. Dry-run only reports what would execute.

### 6. Slop Gate Node

Wire existing `slop-gate` behavior through the executable phase path.

Required behavior:

- `run-phase slop_gate` calls the existing deterministic slop gate implementation or an equivalent internal function
- generated-output inactive cases emit `skipped` with a deterministic skip reason
- generated-output active cases pass or fail from the existing slop gate checks
- failure payloads include `learning_candidates` or `slop_eval_case_candidates` only when the current implementation can produce them deterministically
- output is schema-valid and referenced from workflow state

Do not duplicate the existing slop-gate checker. Reuse it and harden the binding.

### 7. Learning Capture Node

Make `learning_capture` deterministic and evidence-gated.

Required behavior:

- runs only when pr prep or prior phase artifacts provide verified reusable learning candidates
- no candidates emits `skipped` with `no_verified_learning_candidates`
- candidates must reference verifier evidence, source files, stale conditions, and redaction status
- write mode creates or updates `docs/solutions/` entries only with action admission and mutation evidence
- every written learning entry is validated with `scripts/validate_learning_entry.py`
- secrets, credentials, local environment values, and unverified claims are rejected or escalated
- output records written paths, validation status, redaction status, and stale refresh conditions

Do not let learning capture become an LLM memory dump. It must write only verified, redacted, reusable lessons.

### 8. Queue, Worktree, And Tracker Correlation

Connect executable tool nodes to the Goal 4 and Goal 5 substrates.

Required behavior:

- tool-node outputs include `brief_id`, `run_id`, `session_id`, and task IDs when known
- task-scoped tool execution can read `queue_claims[]` and `worktree_refs[]` from workflow state
- mutating tool nodes can require a claimed task and matching worktree before writing
- phase output can be referenced by `queue-complete`, `queue-block`, `queue-escalate`, and `sync-work-item`
- `resume-workflow` exposes the latest phase artifact refs alongside queue/worktree status
- blocked tool-node results include enough structured data to update the right ticket or queue task without creating duplicates

ADLC owns run state. Tickets mirror state. The queue owns task availability and claim ownership. Tool-node artifacts prove what actually happened.

### 9. MCP And Harness Interface

Expose the executable phase layer through the agent-native surface.

Required behavior:

- `mcp-tools --json` accurately describes `run_phase` inputs needed for deterministic tool-node execution
- `mcp-serve` can dry-run and, where safe, execute deterministic tool nodes with explicit arguments
- mutating tool-node calls require action admission and return structured denials when admission is missing
- output schemas are stable enough for an external harness to choose the next action
- docs show the harness flow: claim queue task, prepare worktree, assemble context, run QA or slop gate, complete/block/escalate, sync ticket state

Do not add a scheduler in this goal. A harness can call the tools, but Goal 6 does not decide what to run next.

### 10. Tests And Docs

Add focused tests. Do not rely on visual inspection.

Minimum CLI tests:

- `run-phase <tool-node> --dry-run --json` emits an execution plan without falsely claiming verifier success
- `run-phase qa` executes a passing verifier fixture and emits a schema-valid QA artifact
- `run-phase qa` fails closed on a failing verifier fixture with command evidence
- `run-phase qa` fails closed when no verifier command is available
- `run-phase context_assembly` emits deterministic per-task context packages from a Build Brief fixture
- `run-phase scaffold --dry-run` emits deterministic planned writes
- scaffold write intent requires action admission and queue/worktree safety when writing is requested
- `run-phase slop_gate` reuses the existing slop gate behavior
- `run-phase learning_capture` skips with no candidates and writes/validates with verified candidates in a guarded fixture path
- workflow state records phase artifact refs
- `resume-workflow` exposes latest executable phase output refs
- MCP tool list and dry-run call remain compatible

Minimum contract tests:

- new tool-node result schemas accept valid fixtures and reject missing status, phase, evidence, or run identity
- workflow-state schema accepts phase artifact refs
- existing Goal 1-5 fixtures continue to validate
- `WORKFLOW.dot`, `WORKFLOW.md`, and CLI bindings agree on executable tool nodes
- docs mention `scaffold`, `context_assembly`, `qa`, `slop_gate`, `learning_capture`, phase artifacts, action admission, queue/worktree safety, and fail-closed behavior

Docs:

- update `docs/specs/agent-native-interface.md`
- update `docs/specs/dag-binding.md` or add a focused executable-tool-node spec
- update `WORKFLOW.md` tool-node command bodies so they describe real bindings rather than aspirational comments
- update `README.md` only where external users need to understand the new harness surface

## Validation Gate

Run these before claiming completion:

```bash
git diff --check
bash tests/test_adlc_cli.sh
bash tests/test_adlc_contracts.sh
bin/adlc ci --json
```

Run targeted checks for the new surfaces:

```bash
bin/adlc list-phases --json
bin/adlc run-phase qa --brief-id GOAL-6-SMOKE --workspace . --dry-run --json
bin/adlc run-phase context_assembly --brief-id GOAL-6-SMOKE --workspace . --dry-run --json
bin/adlc run-phase scaffold --brief-id GOAL-6-SMOKE --workspace . --dry-run --json
bin/adlc run-phase slop_gate --brief-id GOAL-6-SMOKE --workspace . --build-brief <generated-output-brief-fixture> --json
bin/adlc run-phase learning_capture --brief-id GOAL-6-SMOKE --workspace . --dry-run --json
bin/adlc mcp-tools --json
```

Update Graphify after production code/doc changes:

```bash
graphify update .
graphify query "How does ADLC execute deterministic tool nodes, emit phase artifacts, connect them to queue worktree state, and fail closed on unsafe mutations?" --budget 3000
```

If Graphify reports no topology changes and leaves the report commit marker behind, say that plainly. Do not add unrelated provider API keys to satisfy Graphify; they are not part of the ADLC production runtime.

## Closeout Requirements

Before committing production changes:

- inspect `git status --short`
- stage only production runtime, schema, fixture, tests, and docs changes
- keep this prompt file local unless the user explicitly asks to commit it
- keep `graphify-out/` local
- restore generated timestamp drift in test reports or other non-production artifacts
- commit with a production-focused message such as `Add executable ADLC tool nodes`

The final answer must state:

- production commit hash, if committed
- exact validation commands and pass/fail results
- any Graphify freshness caveat
- whether any local prompt or graph artifacts remain intentionally unshipped
