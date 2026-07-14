# `/adlc learn`

## Purpose
Propose reusable guidance from verified evidence without silently changing canonical memory.

## Preconditions
A completed or honestly stopped run has evidence, provenance, and a redaction decision.

## Example
`/adlc learn from the verified resume regression`

## Procedure
1. Extract the reusable problem, evidence, scope, and invalidation conditions.
2. Reject secrets, unsupported claims, duplicates, and task-specific narration.
3. Validate the candidate and check memory health.
4. Present the proposal for promotion approval.

## Outputs
A local learning candidate with evidence refs, limitations, and promotion target.

## Stop states
`proposal_ready`, `not_reusable`, `blocked_redaction`, `duplicate`, or `approval_required`.

## Side effects
Local proposal only; canonical promotion is gated.

## Approval points
Require human approval before updating shared skills, memory, or published guidance.

## Compatibility map
Wraps feedback-loop, learning-capture, and learning-refresh; kernel: `bin/adlc memory-health`, `bin/adlc run-phase`.

## Troubleshooting
If evidence is stale or contradictory, keep the candidate local and record invalidation.

## Honesty
doc_honesty_section: A validated candidate is proposed guidance, not universal truth.
no_overclaim: One successful run does not establish a general pattern.
limitations: Promotion quality depends on independent evidence and future invalidation checks.
