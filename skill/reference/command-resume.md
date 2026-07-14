# `/adlc resume`

## Purpose
Continue persisted work from a safe checkpoint without replaying completed side effects.

## Preconditions
Persisted state, current repository identity, and prior approval posture can be reconciled.

## Example
`/adlc resume the interrupted workflow`

## Procedure
1. Read state and verify workspace, commit, task fingerprint, and dirty paths.
2. Inventory completed side-effect idempotency keys and the next runnable phase.
3. Revalidate expired approvals, credentials, and gates.
4. Continue only the next incomplete action and persist the new checkpoint.

## Outputs
A resumed action result or an exact blocked-state handoff.

## Stop states
`resumed`, `already_complete`, `blocked_state_drift`, `approval_required`, or `escalated`.

## Side effects
Uses the persisted mutation posture; completed effects must not replay.

## Approval points
Renew approval when target, authority, credentials, or irreversible action changed.

## Compatibility map
Kernel: `bin/adlc resume`. No legacy public skill is replaced.

## Troubleshooting
On mismatch, preserve state and route to Status rather than restarting from narration.

## Honesty
doc_honesty_section: Resume proves checkpoint continuity only when identities and effects reconcile.
no_overclaim: Continuing a session does not prove prior steps were correct.
limitations: Missing idempotency evidence blocks effectful replay.
