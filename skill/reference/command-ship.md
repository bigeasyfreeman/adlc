# `/adlc ship`

## Purpose
Prepare a truthful PR or release package and stop at the external-action gate.

## Preconditions
The scoped commit, required verifier evidence, target, and release authority are known.

## Example
`/adlc ship this branch as a draft PR`

## Procedure
1. Verify branch scope, cleanliness, claims, and required gates.
2. Run completion and PR hygiene checks.
3. Draft the external package with limitations and rollback notes.
4. Stop before push, PR creation, merge, release, deploy, or communication unless approved.
5. Load `register-release.md` for delivery or operational readiness and `register-integrations.md` only for an explicitly requested external handoff. Never load the legacy `ship-content` skill.

## Outputs
A publish-ready package, exact pending action, and current evidence summary.

## Stop states
`approval_required`, `package_ready`, `blocked_gate`, `published_with_approval`, or `escalated`.

## Side effects
Local drafting only by default; approved external actions may change shared systems.

## Approval points
Human approval is mandatory for every external mutation and must name the action and target.

## Compatibility map
Wraps `skills/ship-content/SKILL.md`; kernel: `bin/adlc pr-hygiene-scan`, `bin/adlc completion-audit`.

## Troubleshooting
On stale checks or dirty scope, stop and report the exact invalidating evidence.

## Honesty
doc_honesty_section: Package-ready is not published, merged, released, or deployed.
no_overclaim: A successful push does not establish runtime health.
limitations: External state can change after local verification.
