# ADLC Goal 4: Ticket And State Synchronization

You are Codex working in the ADLC repository. This is Goal 4 of the ADLC loop-system maturity productionization sequence.

This prompt is a local execution artifact. Do not include this prompt file in the production commit unless the user explicitly asks. Commit only production runtime, schema, tests, and docs needed by the shipped tool.

Remote sync boundary: the remote branch should contain only the productionized working ADLC. Keep `graphify-out/` and local prompt artifacts local, even when they are useful for the run. Do not push Graphify output, one-off audits, or local execution prompts as part of Goal 4 closeout.

## Current Shipped Baseline

Treat these as already shipped and do not redo them unless a regression requires a small compatibility fix.

- Goal 1, commit `0a36ff2`: ADLC control-plane verification.
  - `bin/adlc ci --json`
  - workflow-state phase parity in health-check
  - build-brief schema compatibility
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

## Objective

Make ADLC treat trackers as living state, not one-time output. Each ADLC run should be able to find or create the right work item, append current run findings and evidence, sync blocker/status/verifier/next-action state, and avoid duplicate tickets through stable IDs.

The end state is:

- ADLC can resolve an existing work item for a run, Build Brief, task, or candidate signal
- ADLC can create a new work item only when no matching stable ID exists
- ADLC can append run findings, evidence refs, verifier results, blockers, status, and next action to the right existing work item
- ADLC can emit deterministic dry-run payloads and, where an explicit local provider command already exists, perform guarded mutation
- duplicate tickets are prevented by stable external IDs and idempotency keys
- ticket status and ADLC workflow state stay correlated through `brief_id`, `run_id`, `session_id`, and work-item IDs
- `bin/adlc ci --json` passes

## Design Boundary

This is a synchronization layer between ADLC state and external tracker state. It is not the queue substrate, worktree substrate, or broad self-actioning meta-harness.

In scope:

- ticket/work-item identity schema and stable external IDs
- find-or-create semantics for existing normalized work-item emitters
- append-only run update payloads with evidence refs
- status synchronization between ADLC state and ticket state
- blocker, verifier result, and next-action synchronization
- duplicate prevention through deterministic idempotency keys
- guarded provider mutation only through existing explicit provider-command patterns
- CLI, MCP, schema, tests, and external-facing docs for tracker sync

Out of scope:

- worktree prepare/status/cleanup
- task claim/complete/escalate queue commands
- file-overlap and dirty-state collision checks
- deterministic `qa`, `scaffold`, `context_assembly`, `slop_gate`, or `learning_capture` tool nodes
- first dogfood repair loop
- learning memory, champion/holdout prompt loops, or packaged loop library
- broad self-actioning task candidate ranking
- cron, daemon, scheduled automation, auto-merge, deploy, or irreversible actions

Goal 4's exit gate is narrow: each run can update the right existing work item with current status and evidence.

## Required Preflight

1. Inspect branch and worktree.

```bash
git status --short
git log --oneline -5
```

Preserve unrelated user changes. Do not delete, revert, or rewrite untracked prompt artifacts or `graphify-out/`.

2. Read Graphify before source search.

```bash
sed -n '1,220p' graphify-out/GRAPH_REPORT.md
graphify query "ADLC emit work items external IDs ticket state synchronization provider command idempotency side effect ledger workflow state verifier results blockers next action" --budget 3000
```

If the graph is stale, note that and run `graphify update .` after the implementation. Do not treat stale graph output as production evidence.

3. Inspect current tracker and emitter primitives before editing.

```bash
rg -n "emit-work-items|external_id|provider_command|idempotency|side_effect|permission_audit|workflow_state|blocker|verifier|next_action|mcp" scripts docs/schemas docs/specs tests README.md
```

4. Run the current canonical gate before editing.

```bash
bin/adlc ci --json
```

If it fails, capture the exact failure and decide whether it is a pre-existing blocker or part of this goal.

## Implementation Order

### 1. Ticket Identity Contract

Define the stable identity model used to correlate ADLC runs and tracker work items.

Required behavior:

- every emitted or synced work item has a deterministic ADLC external ID
- identity can be derived from Build Brief, normalized task, or workflow state without relying on title text alone
- identity includes or links to `brief_id`, `run_id`, and `session_id` when state is supplied
- duplicate titles with different stable IDs remain distinct
- repeated sync of the same stable ID updates the same work item payload

Prefer extending existing emitter contracts and schemas over creating a second tracker abstraction.

### 2. Find-Or-Create And Update Semantics

Add a deterministic sync model for tracker state.

Required behavior:

- `find` by stable external ID before `create`
- `create` only when no existing external ID is found
- `update` or `append` when the work item already exists
- dry-run output clearly states the planned operation: `find`, `create`, `update`, `append`, `noop`, or `escalate`
- mutation requires the existing explicit provider-command path and action admission evidence
- missing provider capability fails closed with an actionable reason

Expected CLI shape, adjusted to existing conventions if needed:

```bash
bin/adlc sync-work-item --build-brief .adlc/build_brief.json --state .adlc/workflow_state.json --dry-run --json
bin/adlc sync-work-item --work-item tests/fixtures/tracker_sync/run-update.json --state .adlc/workflow_state.json --dry-run --json
```

Do not add live provider mutation until dry-run, schema, idempotency, and permission behavior are covered.

### 3. Run Update Payloads

Add or harden append-only run update payloads.

Each update should carry:

- work-item stable ID
- `brief_id`, `run_id`, and `session_id`
- current ADLC phase or workflow status
- blockers and blocker reason codes
- verifier results and command evidence refs
- next action
- stop reason when present
- links or paths to relevant ADLC artifacts
- timestamp or monotonic sequence, using existing repo conventions

Avoid raw log dumps. Store bounded summaries and artifact refs.

### 4. Workflow State Correlation

Keep ticket state and ADLC state in sync.

Required behavior:

- workflow state records linked work-item IDs or external IDs
- resume output can expose linked work-item state or sync status
- side-effect ledger records ticket sync operations and idempotency keys
- permission audit records whether mutation was dry-run, denied, escalated, or allowed
- status transitions are deterministic and machine-readable

Do not make ticket status the source of truth for ADLC execution state. The tracker mirrors and reports state; ADLC owns the run state.

### 5. MCP And Provider Integration

Expose ticket sync through the agent-native surface.

Required behavior:

- `mcp-tools --json` lists the ticket sync tool or equivalent work-item update tool
- `mcp-serve` can perform the dry-run tool call
- provider mutation stays behind explicit local provider command and action admission
- missing provider command returns a structured no-provider or dry-run-only reason
- provider payloads remain normalized enough for Linear, GitHub Issues, Jira, or a future adapter

If an existing provider interface only supports create, add update/append payload semantics without pretending live update is supported.

### 6. Tests And Docs

Add focused tests. Do not rely on visual inspection.

Minimum CLI tests:

- dry-run create payload when no existing external ID exists
- dry-run update or append payload when the external ID already exists
- duplicate prevention through stable ID
- run update includes blockers, verifier results, next action, and identity
- missing provider command fails closed
- permission/admission evidence is present for mutating intent
- side-effect ledger includes ticket sync identity and idempotency

Minimum contract tests:

- work-item sync schema accepts valid create/update/append fixtures
- schema rejects missing stable ID, run identity, or update evidence
- existing emit-work-items fixtures continue to validate
- MCP tool list and dry-run call remain schema-compatible

Docs:

- update `docs/specs/emitter-contract.md`, `docs/specs/agent-native-interface.md`, or the most relevant external-facing docs so harness authors know how ticket/state sync works
- state clearly what is dry-run-only and what can mutate through provider command
- avoid autonomous overclaiming; this goal synchronizes tracker state, it does not execute fleet work

## Validation Gate

Run these before claiming completion:

```bash
git diff --check
bin/adlc ci --json
tests/test_adlc_cli.sh
tests/test_adlc_contracts.sh
```

Run targeted checks for the new artifacts:

```bash
bin/adlc validate-artifact --schema <work-item-sync-schema> --input tests/fixtures/tracker_sync/run-update.json --json
bin/adlc sync-work-item --work-item tests/fixtures/tracker_sync/run-update.json --state <workflow-state-fixture> --dry-run --json
bin/adlc mcp-tools --json
```

Update Graphify after production code/doc changes:

```bash
graphify update .
graphify query "How does ADLC synchronize ticket state with workflow state, append run evidence, prevent duplicate tickets, and fail closed without provider mutation?" --budget 3000
```

## Commit Boundary

Before committing:

```bash
git status --short
git diff --stat
git diff --check
```

Commit only production changes:

- `scripts/`
- `docs/schemas/`
- `docs/specs/`
- `README.md`
- `tests/`
- fixtures under `tests/fixtures/`

Do not commit local prompt artifacts, one-off audits, or graphify generated output unless the user explicitly asks.

When syncing to remote, push only committed production changes. Leave `graphify-out/` ignored/local and leave this prompt artifact uncommitted.

Suggested production commit message:

```text
Add ADLC ticket state synchronization
```

## Final Response Requirements

Report:

- changed production files
- ticket identity, find-or-create, update/append, status sync, and duplicate-prevention behavior
- exact validation commands and results
- whether Graphify was updated
- commit hash
- any unsupported states that remain

Do not say the goal is complete unless the validation gate passes or an external blocker is documented with the exact rerun path.
