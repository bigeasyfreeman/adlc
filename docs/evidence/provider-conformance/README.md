# Provider Conformance Evidence

ADLC does not currently claim a live-supported provider. Runtime adapters may
be implemented while conformance remains pending.

A provider becomes eligible for a public support claim only after the live
smoke harness produces a schema-valid
`provider-conformance-report` with:

- `overall: pass` and every stage passing;
- `evidence_status: current_conformance`;
- a clean source tree at the recorded commit;
- runtime, model, adapter path and digest, fixture digest, auth path, and run
  timestamps recorded; and
- the canonical `bin/adlc ci --json` gate passing at the same commit.

Smoke output under `tests/smoke/artifacts/` is ephemeral. After reviewing a
successful clean-tree report for secrets and local data, copy it here using a
name such as `YYYY-MM-DD-claude.json`, validate it again, and commit it with the
adapter claim it supports:

```bash
bin/adlc validate-artifact \
  --schema provider-conformance-report \
  --input tests/smoke/artifacts/smoke_report.json \
  --json
```

Candidate reports from dirty trees and failed reports are useful diagnostics,
but they do not establish provider support.
