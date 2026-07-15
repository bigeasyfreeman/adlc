# `/adlc init`

## Purpose
Discover applicable repository instructions and propose bounded ADLC-owned project context.

## Preconditions
The repository path and affected target are known; existing instruction files remain user-owned.

## Example
`/adlc init for this repository, targeting src/service`

## Procedure
1. Build the context manifest and inspect conflicts and missing decisions.
2. Run `bin/adlc repo-conventions --workspace <repo> --json`.
3. Preview `.adlc/PROJECT.md`, `.adlc/ENGINEERING.md`, and `.adlc/config.json`.
4. Write them only after review and only when none collide.

## Outputs
A source-attributed context manifest and, when approved, three new ADLC-owned context files.

## Stop states
`initialized`, `blocked_collision`, `blocked_missing_context`, or `failed_validation`.

## Side effects
No target change by default; approved initialization creates only absent `.adlc` context files.

## Approval points
Require human approval before writing reviewed context files.

## Compatibility map
Kernel: `bin/adlc repo-conventions`, `bin/adlc health-check`. No legacy public skill is replaced.

## Troubleshooting
On collision, report exact paths and preserve every existing byte; never force overwrite.

## Honesty
doc_honesty_section: Discovery proves only what the bounded manifest observed.
no_overclaim: Initialization does not prove provider installation or loop behavior.
limitations: Missing or stale repository instructions reduce context quality.
