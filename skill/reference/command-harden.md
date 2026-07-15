# `/adlc harden`

## Purpose
Run only the security, reliability, compatibility, and quality gates applicable to the current change.

## Preconditions
The changed surface and applicability evidence are known.

## Example
`/adlc harden this authentication change`

## Procedure
1. Derive applicable overlays from the Build Brief and changed files.
2. Run the existing deterministic checks and named specialist packs.
3. Record failures and evidence without repairing by default.
4. Route any authorized repair through Build or Fix.

## Outputs
An applicability record, gate results, findings, and residual risk.

## Stop states
`gates_passed`, `findings_ready`, `blocked_evidence`, or `escalated`.

## Side effects
Read-only by default; local repair requires explicit mutation authority.

## Approval points
Require approval before scans that access credentials, external systems, or destructive test environments.

## Compatibility map
Kernel: `bin/adlc convention-scan`, `bin/adlc slop-gate`; specialist legacy skills remain internal packs.

## Troubleshooting
If applicability is unclear, mark the gate unresolved rather than silently skipping it.

## Honesty
doc_honesty_section: Passing applicable gates is scoped evidence, not a security certification.
no_overclaim: Do not call the system secure, reliable, or compatible from this command alone.
limitations: Unavailable environments and credentials leave explicit untested cells.
