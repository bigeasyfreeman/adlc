# ADLC Goal 3: Durable Run Identity And Resumable State

You are Codex working in the ADLC repository. This is Goal 3 of the ADLC loop-system maturity productionization sequence.

This prompt is a local execution artifact. Do not include this prompt file in the production commit unless the user explicitly asks. Commit only production runtime, schema, tests, and docs needed by the shipped tool.

Remote sync boundary: the remote branch should contain only the productionized working ADLC. Keep `graphify-out/` and local prompt artifacts local, even when they are useful for the run. Do not push Graphify output, one-off audits, or local execution prompts as part of Goal 3 closeout.

Status note: Goal 3 was implemented and synced as production code at commit `0908a7a` (`Add durable ADLC run identity state`). Keep this file as a local historical execution artifact unless the user explicitly asks to commit local prompt artifacts.

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

Productionize durable ADLC run identity and state so every self-actioning run has a stable identity, resumable state, idempotent side-effect ledger, clear stop reasons, and machine-verifiable evidence.

The end state is:

- a fresh ADLC run persists a stable `run_id` and `session_id`
- resume preserves the same `run_id`, `session_id`, and `brief_id`
- resume increments explicit resume or attempt metadata
- side effects correlate to the same run/session/brief identity
- permission decisions correlate to the same run/session/brief identity
- idempotency keys remain stable across resume
- stop reasons are preserved and exposed in JSON
- `bin/adlc ci --json` passes

## Design Boundary

Keep this as an ADLC-native control-plane slice.

In scope:

- workflow-state identity fields
- session-state/schema compatibility if needed
- resume metadata
- side-effect ledger correlation
- permission-audit-trail correlation
- idempotency evidence
- stop-reason evidence
- CLI/MCP JSON output compatibility where these surfaces already exist
- focused docs for external users of the shipped productionization tool

Out of scope:

- scheduler or cron orchestration
- queue runners
- git worktree orchestration
- external ticket sync
- provider-specific rollback
- new planner architecture
- non-LLM deterministic task selection
- broad refactors of the runtime

Do not broaden this into Goal 4 or fleet orchestration. Goal 3 is identity, state, and evidence durability.

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
graphify query "durable ADLC run identity workflow state session state resume side effects idempotency permission audit stop reasons" --budget 3000
```

If the graph is stale, note that and run `graphify update .` after the implementation. Do not treat stale graph output as production evidence.

3. Inspect the current primitives before editing.

```bash
rg -n "new_workflow_state|resume-workflow|session_id|resume_count|side_effects|idempotency_key|permission_audit|stop_reason" scripts/adlc_runtime/cli.py docs/schemas tests README.md docs/specs
```

4. Run the current canonical gate before editing.

```bash
bin/adlc ci --json
```

If it fails, capture the exact failure and decide whether it is a pre-existing blocker or part of this goal.

## Implementation Order

### 1. Workflow State Identity

Add or harden durable workflow identity fields.

Required runtime behavior:

- fresh `bin/adlc run --json` creates `run_id`
- `run_id` is stable after it is written
- fresh state keeps existing `session_id` behavior
- `brief_id`, `run_id`, and `session_id` are present in JSON evidence
- old workflow-state fixtures continue to validate unless they intentionally test missing required fields

Prefer backward-compatible schema additions unless a stricter requirement is already enforced by existing fixtures.

Suggested shape:

```json
{
  "brief_id": "ADLC-GOAL-3",
  "run_id": "run:<stable-id>",
  "session_id": "session:<stable-id>",
  "resume_count": 0,
  "attempt": 1
}
```

Use the repo's existing ID conventions if they differ from this suggested shape.

### 2. Resume Semantics

Update `resume-workflow` so it proves continuity instead of creating a new logical run.

Required behavior:

- preserves `run_id`
- preserves `session_id`
- preserves `brief_id`
- increments `resume_count` or equivalent resume metadata
- increments or exposes explicit attempt metadata if added
- preserves existing progress/control/stop-reason fields
- exposes identity and stop state in `--json`

Add regression coverage for at least one fresh run followed by two resumes.

### 3. Side-Effect Correlation

Ensure side-effect records and emitter outputs can be traced to the run that produced them.

Required behavior:

- side-effect entries include or inherit `brief_id`, `run_id`, and `session_id`
- external mutation ledgers keep their current safety behavior
- dry-run emitters remain dry-run
- normalized work item idempotency keys stay stable across resume

Do not change idempotency key inputs unless required. If a key format must change, explain why and add compatibility evidence.

### 4. Permission Decision Correlation

Extend the Goal 2 admission evidence so permission decisions are correlated with the durable run identity.

Required behavior:

- `bin/adlc action-admit --state <workflow_state>` includes `brief_id`, `run_id`, and `session_id` in JSON evidence
- permission-audit-trail root and entries carry enough identity to correlate decisions back to the run
- action admission remains deterministic
- denied or escalated actions expose a machine-readable reason

If an action is denied or escalated, do not call it a successful action. The admission result should be explicit.

### 5. Stop Reasons

Stop reasons are part of the durable state contract.

Required behavior:

- workflow-state schema supports the stop reason fields already emitted by runtime
- phase runners preserve stop reason on state writes
- resume output exposes existing stop reason
- action-admission or budget denial output exposes a concrete machine-readable stop or denial reason when applicable

Good stop reasons include `human_gate`, `budget_exhausted`, `permission_denied`, `permission_requires_escalation`, and existing runtime-specific values.

### 6. Tests And Docs

Add focused tests. Do not rely on visual inspection.

Minimum CLI tests:

- fresh run emits `run_id`, `session_id`, and `brief_id`
- resume preserves `run_id` and `session_id`
- resume increments resume or attempt metadata
- side-effect entries correlate to the same identity
- idempotency keys remain stable across resume
- action-admit audit evidence includes identity when state is supplied
- stop reason survives resume and appears in JSON

Minimum contract tests:

- workflow-state schema accepts new identity fields
- permission-audit-trail schema accepts identity correlation fields
- existing fixtures still validate

Docs:

- update only the external-facing docs needed to describe durable identity/state evidence
- avoid marketing language and autonomous overclaiming

## Validation Gate

Run these before claiming completion:

```bash
git diff --check
bin/adlc ci --json
tests/test_adlc_cli.sh
tests/test_adlc_contracts.sh
```

Run targeted schema checks if you added or changed fixtures:

```bash
bin/adlc validate-artifact --schema workflow-state --input <fixture> --json
bin/adlc validate-artifact --schema permission-audit-trail --input <fixture> --json
```

Update Graphify after production code/doc changes:

```bash
graphify update .
graphify query "How does ADLC preserve durable run identity, resumable workflow state, side-effect idempotency, permission audit correlation, and stop reasons?" --budget 3000
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

Suggested commit message:

```text
Add durable ADLC run identity state
```

## Final Response Requirements

Report:

- changed production files
- what identity/state behavior now exists
- exact validation commands and results
- whether Graphify was updated
- commit hash
- any unsupported states that remain

Do not say the goal is complete unless the validation gate passes or an external blocker is documented with the exact rerun path.
