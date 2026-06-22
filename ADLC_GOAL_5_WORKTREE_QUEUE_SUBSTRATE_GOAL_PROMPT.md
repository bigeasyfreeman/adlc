# ADLC Goal 5: Worktree And Queue Substrate

You are Codex working in the ADLC repository. This is Goal 5 of the ADLC loop-system maturity productionization sequence.

This prompt is a local execution artifact. Do not include this prompt file in the production commit unless the user explicitly asks. Commit only production runtime, schema, tests, and docs needed by the shipped tool.

Remote sync boundary: the remote branch should contain only the productionized working ADLC. Keep `graphify-out/` and local prompt artifacts local, even when they are useful for the run. Do not push Graphify output, one-off audits, or local execution prompts as part of Goal 5 closeout.

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

## Objective

Make safe parallel execution possible. ADLC should be able to queue work, claim tasks, prepare isolated git worktrees, detect collisions before agents write files, complete or block tasks, and expose current work state to a harness or LLM without relying on chat memory.

The end state is:

- ADLC has a schema-backed queue or inbox artifact for runnable work
- tasks can move through `queued`, `claimed`, `running`, `blocked`, `done`, `escalated`, and abandoned or released states
- task claims are stable and correlated to `brief_id`, `run_id`, `session_id`, and optional `work_item_external_id`
- claimed and running tasks declare expected file paths or path globs so ADLC can detect overlap
- worktree prepare/status/cleanup commands are available through `bin/adlc`
- dirty checkout and dirty worktree states fail closed before unsafe claim, prepare, or cleanup operations
- file-overlap checks prevent multiple agents from claiming or preparing colliding work
- queue and worktree status are machine-readable and visible through the agent-native/MCP surface
- `bin/adlc ci --json` passes

## Design Boundary

This goal is the queue and isolation substrate. It is not the broader self-actioning meta-harness.

In scope:

- queue or inbox schema
- task claim, release, complete, block, and escalate semantics
- worktree prepare, status, and cleanup semantics
- branch and worktree naming that is deterministic and traceable to task identity
- dirty-state checks for the current checkout and target worktree
- file-overlap checks across claimed and running tasks
- workflow-state correlation for active claims and worktree refs
- side-effect ledger and permission-audit evidence for queue/worktree mutations
- MCP and docs updates for harness consumption
- focused CLI, contract, fixture, and end-to-end dry-run tests

Out of scope:

- deterministic implementations for `qa`, `scaffold`, `context_assembly`, `slop_gate`, or `learning_capture`
- first ADLC dogfood repair loop
- learning memory, architecture decision memory, stale-learning refresh, or champion/holdout prompt loops
- packaged loop library
- broad task-candidate discovery, value/risk ranking, or autonomous dispatch
- scheduled automation, cron, daemon, auto-merge, deploy, or irreversible provider action
- tracker sync changes beyond using the already shipped Goal 4 work-item link fields where useful

Goal 5's exit gate is narrow: multiple agents can work without colliding, and ADLC can see what is claimed, running, blocked, done, or escalated.

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
graphify query "ADLC worktree queue task claim complete escalate dirty state file overlap workflow state side effects MCP" --budget 3000
```

If the graph is stale, note that and run `graphify update .` after the implementation. Do not treat stale graph output as production evidence.

3. Inspect current queue, workflow-state, side-effect, and MCP primitives before editing.

```bash
rg -n "worktree|queue|claim|complete|escalate|block|release|dirty|file overlap|work_item_links|sync-work-item|resume-workflow|mcp-tools|side_effect|permission_audit|workflow_state" scripts docs/schemas docs/specs tests README.md
```

4. Run the current canonical gate before editing.

```bash
bin/adlc ci --json
```

If it fails, capture the exact failure and decide whether it is a pre-existing blocker or part of this goal.

## Implementation Order

### 1. Queue And Inbox Contract

Define the durable work queue ADLC can read and update.

Required behavior:

- queue entries have stable `task_id` values
- queue entries include a human-readable title, source ref, status, priority or ordering, and optional `work_item_external_id`
- queue entries can reference `brief_id`, `run_id`, and `session_id` when known
- queue entries declare expected touched paths or path globs when claim isolation depends on file ownership
- queue entries declare verifier commands or evidence refs when the task already has known gates
- schema validation rejects missing task identity, unsupported status, invalid claim metadata, or malformed path ownership data
- repeated reads produce deterministic ordering

Prefer extending existing workflow-state and artifact conventions over inventing a second runtime database.

### 2. Claim Lifecycle

Add deterministic commands for claim state transitions.

Expected CLI shape, adjusted to existing conventions if needed:

```bash
bin/adlc queue-status --queue .adlc/work_queue.json --json
bin/adlc queue-claim --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --dry-run --json
bin/adlc queue-release --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --dry-run --json
bin/adlc queue-complete --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --evidence .adlc/loop_test_result.json --dry-run --json
bin/adlc queue-block --queue .adlc/work_queue.json --task-id TASK-123 --reason file_collision --state .adlc/workflow_state.json --dry-run --json
bin/adlc queue-escalate --queue .adlc/work_queue.json --task-id TASK-123 --reason human_review_required --state .adlc/workflow_state.json --dry-run --json
```

Required behavior:

- `queue-status` reports counts and entries for `queued`, `claimed`, `running`, `blocked`, `done`, and `escalated`
- `queue-claim` refuses missing tasks, already claimed tasks, completed tasks, blocked tasks without explicit release, and tasks whose expected paths overlap active claims
- claim metadata records agent/session identity, timestamp or monotonic sequence, expected paths, and optional worktree ref
- `queue-complete` requires verifier or evidence refs when the task declares them
- `queue-block` and `queue-escalate` require structured reasons and next action
- all mutating commands support deterministic dry-run output before write mode
- write mode records side effects and permission-audit evidence

Do not let the LLM decide that a conflicting claim is acceptable. Conflict handling must be deterministic and fail closed.

### 3. Worktree Contract

Add safe git worktree lifecycle commands.

Expected CLI shape, adjusted to existing conventions if needed:

```bash
bin/adlc worktree-prepare --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc worktree-status --workspace . --queue .adlc/work_queue.json --json
bin/adlc worktree-cleanup --workspace . --task-id TASK-123 --dry-run --json
```

Required behavior:

- worktree branch and path names are deterministic and include or derive from the stable task ID
- `worktree-prepare` refuses dirty source checkout state before preparing isolation
- `worktree-prepare` refuses path overlap with already claimed or running tasks
- `worktree-prepare` can dry-run without creating a branch or worktree
- write mode uses `git worktree` safely and never relies on destructive reset or checkout behavior
- `worktree-status` reports branch, path, base ref, dirty state, linked queue task, linked run identity, and cleanup eligibility
- `worktree-cleanup` refuses dirty, uncommitted, or unresolved worktrees unless an explicit force or abandon path is implemented and documented
- cleanup records whether the task is complete, blocked, escalated, released, or still running

If the repo cannot safely create a real worktree in tests, implement a dry-run and fixture-backed status path first, then add real worktree coverage with temp directories.

### 4. Collision And Dirty-State Checks

Build the safety checks as reusable deterministic primitives.

Required behavior:

- current checkout dirty state is checked before claim and prepare operations that assume a clean base
- target worktree dirty state is checked before cleanup
- expected path overlap is detected across active `claimed` and `running` tasks
- exact file paths and directory/glob ownership are normalized before comparison
- unsafe overlap returns a structured reason such as `file_overlap`, `dirty_checkout`, or `dirty_worktree`
- command output includes the conflicting task IDs and paths needed for human review
- warnings are not enough for collision states; unsafe states must fail closed

Keep these checks local and deterministic. Do not use an LLM verifier for collision decisions.

### 5. State Correlation

Connect queue/worktree operations to ADLC's existing run identity and tracker sync surfaces.

Required behavior:

- workflow state can record active claims or link to the queue artifact
- queue entries can link back to `work_item_links[]` from Goal 4 without making the tracker the source of truth
- side-effect ledger records queue and worktree operations with idempotency keys
- permission audit records whether the operation was dry-run, denied, escalated, or allowed
- `resume-workflow` or a closely related status command can expose active queue/worktree state
- task completion can carry verifier result refs without duplicating the full verifier payload

ADLC owns run state. Tickets mirror state. The queue owns task availability and claim ownership.

### 6. MCP And Harness Interface

Expose the new substrate through the agent-native surface.

Required behavior:

- `mcp-tools --json` lists queue status/claim/complete/block/escalate and worktree prepare/status/cleanup tools, or a smaller equivalent surface with the same capabilities
- `mcp-serve` can perform dry-run calls for the new tools
- mutating calls require explicit permission/action admission evidence
- command outputs are JSON-stable enough for an external harness to consume
- docs show how a harness would claim a task, prepare a worktree, verify status, complete or block the task, and clean up

Do not add an autonomous scheduler in this goal. A harness can call the tools, but Goal 5 does not decide which tasks should exist or when to run them.

### 7. Tests And Docs

Add focused tests. Do not rely on visual inspection.

Minimum CLI tests:

- queue schema validates a valid queue fixture
- queue schema rejects missing task ID, unsupported status, and malformed path ownership
- `queue-status` reports deterministic counts by status
- `queue-claim --dry-run` succeeds for a clean queued task
- `queue-claim --dry-run` fails for an already claimed task
- `queue-claim --dry-run` fails when expected paths overlap another active claim
- `queue-complete --dry-run` requires verifier/evidence refs when declared by the task
- `queue-block` and `queue-escalate` require structured reason and next action
- `worktree-prepare --dry-run` reports deterministic branch/path without creating files
- `worktree-prepare --dry-run` fails closed on dirty checkout evidence
- `worktree-status` reports linked queue task and dirty state
- `worktree-cleanup --dry-run` refuses dirty worktree evidence
- side-effect and permission-audit evidence exists for write-intent paths
- MCP tool list includes the new surfaces

Minimum contract tests:

- queue/inbox schema accepts valid fixtures and rejects invalid fixtures
- workflow-state schema accepts any new active claim or queue link fields
- side-effect ledger and permission-audit schemas accept new queue/worktree operation types
- existing Goal 1-4 fixtures continue to validate
- `bin/adlc ci --json` remains green

Docs:

- update `docs/specs/agent-native-interface.md`, README, or the most relevant harness-facing docs
- document dry-run versus write behavior
- document collision rules and dirty-state refusal behavior
- state explicitly that Goal 5 is the substrate for parallel work, not the full self-actioning meta-harness

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
bin/adlc validate-artifact --schema <work-queue-schema> --input tests/fixtures/work_queue/valid-queue.json --json
bin/adlc queue-status --queue tests/fixtures/work_queue/valid-queue.json --json
bin/adlc queue-claim --queue tests/fixtures/work_queue/valid-queue.json --task-id <claimable-task-id> --state <workflow-state-fixture> --dry-run --json
bin/adlc worktree-prepare --queue tests/fixtures/work_queue/valid-queue.json --task-id <claimable-task-id> --workspace <tmp-workspace> --dry-run --json
bin/adlc mcp-tools --json
```

Update Graphify after production code/doc changes:

```bash
graphify update .
graphify query "How does ADLC prevent parallel agents from colliding through queue claims, worktree isolation, dirty-state checks, and file-overlap checks?" --budget 3000
```

## Commit Boundary

Before committing production work:

```bash
git status --short
git diff --stat
git diff --check
```

Commit only production changes:

- `scripts/`
- `bin/`
- `docs/schemas/`
- `docs/specs/`
- `README.md`
- `tests/`
- fixtures under `tests/fixtures/`

Do not commit local prompt artifacts, one-off audits, or graphify generated output unless the user explicitly asks.

When syncing to remote, push only committed production changes. Leave `graphify-out/` ignored/local and leave this prompt artifact unpushed.

Suggested production commit message:

```text
Add ADLC worktree queue substrate
```

## Final Response Requirements

Report:

- changed production files
- queue schema and claim lifecycle behavior
- worktree prepare/status/cleanup behavior
- dirty-state and file-overlap refusal behavior
- MCP/harness-facing surfaces
- exact validation commands and results
- whether Graphify was updated
- commit hash
- any unsupported states that remain

Do not say the goal is complete unless the validation gate passes or an external blocker is documented with the exact rerun path.
