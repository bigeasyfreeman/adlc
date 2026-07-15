# `/adlc review`

## Purpose
Return evidence-backed findings for one change without modifying it.

## Preconditions
A concrete diff, commit, PR, or artifact scope is available.

## Example
`/adlc review the current branch against main`

## Procedure
1. Load `docs/loop-library/public-review.json`.
2. Inspect scope, contracts, code paths, tests, and current verifier evidence.
3. Reproduce material concerns with read-only commands or temporary copies.
4. Report severity-ranked findings, open questions, and a merge recommendation.

## Outputs
Findings with file and line evidence, commands run, residual risks, and verdict.

## Stop states
`findings_ready`, `no_findings`, `blocked_missing_context`, or `escalated`.

## Side effects
Strictly read-only in the target: do not edit, commit, push, comment, label, or resolve threads.

## Approval points
Invoke a separate `/adlc fix` or `/adlc build` before any remediation mutation.

## Compatibility map
Loop: `docs/loop-library/public-review.json`; kernel: `bin/adlc completion-audit`, `bin/adlc pr-hygiene-scan`. Load the applicable review row from `register-engineering.md`, `register-security.md`, or `register-release.md`; do not load unrelated registers.

## Troubleshooting
If asked to “review and clean up,” finish the review only and offer the separate Fix command.

## Honesty
doc_honesty_section: No findings means no findings in the inspected scope.
no_overclaim: Review cannot prove absence of defects.
limitations: Missing runtime, credential, or deployment evidence remains unverified.
