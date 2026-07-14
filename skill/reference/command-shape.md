# `/adlc shape`

## Purpose
Turn ambiguous intent into a bounded, decision-ready Build Brief without product mutation.

## Preconditions
The user outcome, target repository, and unresolved decisions can be stated or explicitly marked missing.

## Example
`/adlc shape add resumable export for account owners`

## Procedure
1. Separate facts, hypotheses, constraints, and open decisions.
2. Research only the affected surfaces and reuse existing contracts.
3. Draft criteria, verifier predicates, scope, compatibility, and honesty boundaries.
4. Validate the artifact and stop for intent approval.

## Outputs
A schema-valid brief or a concise decision request with evidence references.

## Stop states
`decision_ready`, `blocked_user_decision`, `blocked_research`, or `rejected`.

## Side effects
Local planning artifacts only; no product code or external tracker mutation.

## Approval points
Human intent validation is required before Build may mutate.

## Compatibility map
Wraps PRD, goal-prompt, and Build Brief agents; kernel: `bin/adlc goal-prompt`, `bin/adlc validate-artifact`.

## Troubleshooting
If intent stays ambiguous, narrow the smallest reversible slice and ask one blocking question.

## Honesty
doc_honesty_section: A valid brief records intended work, not shipped behavior.
no_overclaim: Shaping does not establish feasibility or user value.
limitations: Decisions remain provisional until the named owner approves them.
