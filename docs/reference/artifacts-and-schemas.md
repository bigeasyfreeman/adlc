# Artifacts and schemas

ADLC uses versioned JSON Schemas for briefs, workflow state, approvals, loop actions, test results, conformance reports, install manifests, completion audits, and other control-plane records.

Validate an artifact with:

```bash
bin/adlc validate-artifact --schema build-brief --input path/to/brief.json --json
```

Canonical schemas for this documentation version live under [`docs/schemas/`](https://github.com/bigeasyfreeman/adlc/tree/v0.9.2/docs/schemas). Runtime state belongs under the target’s ignored `.adlc/` directory. Planning, council, audit, and closeout process artifacts belong in ADLC-side storage computed by `bin/adlc process-artifact-path`; they should not leak into a target product diff.

Evidence references must resolve to real artifacts and remain scoped to the claim. A valid schema proves structure, not truth, freshness, or behavioral success.

Historical design documents are labeled in the [archive](https://github.com/bigeasyfreeman/adlc/tree/v0.9.2/docs/archive) and are not current operator contracts.

`doc_honesty_section`: Schema validation is one gate in an evidence chain.

`no_overclaim`: File existence and schema validity are not behavioral proof.

`limitations`: External systems can invalidate evidence after it is recorded; check timestamps, commits, and versions.
