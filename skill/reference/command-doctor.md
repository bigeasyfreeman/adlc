# `/adlc doctor`

## Purpose
Verify the local installation, provider bundle, kernel, schemas, and credential posture without mutation.

## Preconditions
The intended provider, workspace, and executable environment are identified.

## Example
`/adlc doctor for Codex in this repository`

## Procedure
1. Run the deterministic health check and record binary provenance.
2. Verify schema aliases, wrapper availability, provider bundle presence, and native discovery.
3. Report credential availability without reading or printing secrets.
4. Separate installation, discovery, invocation, and loop readiness.

## Outputs
A dimension-by-dimension diagnostic with commands, versions, and repair guidance.

## Stop states
`healthy_local`, `missing_dependency`, `blocked_credentials`, `stale_bundle`, or `unsupported`.

## Side effects
None; this command is read-only.

## Approval points
Sign-in or credential repair requires user handoff; never request secrets in chat.

## Compatibility map
Kernel: `bin/adlc health-check`. No legacy public skill is replaced.

## Troubleshooting
Report the exact binary path and version when multiple installations disagree.

## Honesty
doc_honesty_section: A local health pass covers only the inspected dimensions.
no_overclaim: Installation does not prove invocation or loop conformance.
limitations: Missing credentials leave provider behavior untested.
