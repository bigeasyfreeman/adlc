# `/adlc fix`

## Purpose
Run the reproduction-first Fix loop from observed defect to PR-ready evidence.

## Preconditions
An observable failure, affected target, and authority boundary are available.

## Example
`/adlc fix the duplicate notification after resume`

## Procedure
1. Load `docs/loop-library/public-fix.json`.
2. Reproduce the defect and record a verifier that fails for the expected reason.
3. Diagnose the narrow cause and apply the smallest repair.
4. Prove the verifier changes red to green, run the affected suite, and obtain independent review.

## Outputs
Reproduction evidence, causal diagnosis, scoped repair, verifier results, and PR-ready evidence.

## Stop states
`pr_ready`, `not_reproduced`, `blocked_missing_evidence`, `failed_verification`, or `escalated`.

## Side effects
Local mutation begins only after reproduction evidence; external effects require separate approval.

## Approval points
Require approval for destructive recovery, privileged access, external writes, publish, merge, or deploy.

## Compatibility map
Loop: `docs/loop-library/public-fix.json`; wraps systematic-debugging, fix-loop, and fix-bug; kernel: `bin/adlc ci`, `bin/adlc completion-audit`. Load only the matching row of `register-engineering.md`; add `register-security.md` or `register-release.md` only when the reproduced defect crosses those boundaries.

## Troubleshooting
If asked to skip tests, stop honestly: reproduction and verifier evidence are mandatory.

## Honesty
doc_honesty_section: A green verifier proves only the named defect contract and affected gates.
no_overclaim: It does not prove unrelated behavior or production recovery.
limitations: Non-reproducible defects remain blocked, not fixed.
