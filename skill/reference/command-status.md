# `/adlc status`

## Purpose
Explain persisted workflow state, evidence, blockers, and the next safe action.

## Preconditions
A workspace and optional workflow-state path are available.

## Example
`/adlc status for the interrupted Fix loop`

## Procedure
1. Read persisted state without incrementing counters or replaying actions.
2. Reconcile it with the current commit, dirty state, gates, and evidence refs.
3. Separate proved, contradicted, incomplete, and unverified requirements.
4. Name one next action and its approval needs.

## Outputs
A read-only state summary with checkpoint, blockers, evidence, and next action.

## Stop states
`status_ready`, `no_state`, `stale_state`, or `blocked_access`.

## Side effects
None; this command is read-only.

## Approval points
No approval for inspection; a proposed mutation requires its own command and gate.

## Compatibility map
Kernel: `bin/adlc status`. No legacy public skill is replaced.

## Troubleshooting
If state and repository disagree, report both and treat resume as blocked.

## Honesty
doc_honesty_section: Status reports observed state at a named time and commit.
no_overclaim: Transport or scheduler health does not prove the broader workflow succeeded.
limitations: Unreachable external systems remain unverified.
