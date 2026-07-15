# `/adlc build`

## Purpose
Run the approved-intent Build loop to PR-ready evidence.

## Preconditions
An approved, schema-valid Build Brief names scope, verifier, files, gates, and compatibility posture.

## Example
`/adlc build ADLC-MIG-004`

## Procedure
1. Load `docs/loop-library/public-build.json`.
2. Confirm intent approval and create the failing architecture or acceptance verifier first.
3. Implement the smallest declared slice through existing workflow phases.
4. Run affected and canonical gates, independent review, and PR preparation.

## Outputs
A scoped diff, verifier evidence, independent findings, and a PR-ready package.

## Stop states
`pr_ready`, `blocked_human_approval`, `blocked_credentials`, `failed_verification`, or `escalated`.

## Side effects
Gated local code and test writes; external publication remains separate.

## Approval points
Require intent approval before mutation and human approval before publish, merge, release, or deploy.

## Compatibility map
Loop: `docs/loop-library/public-build.json`; wraps `skills/build-feature/SKILL.md`; kernel: `bin/adlc run`, `bin/adlc ci`.

## Troubleshooting
On verifier failure, preserve the failure and route diagnosis through `/adlc fix`.

## Honesty
doc_honesty_section: PR-ready means declared gates passed for the scoped commit.
no_overclaim: It does not mean merged, deployed, adopted, or generally available.
limitations: Provider behavior remains unproven until behavioral conformance runs.
