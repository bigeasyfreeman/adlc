# Public Fix benchmark methodology

## Question

This benchmark asks whether the documented ADLC Fix controls work on one pinned invoice-allocation defect. It does not compare ADLC with another framework and does not score prose written by the framework itself.

The published configuration invokes Codex with the disclosed model through the CLI. Each attempt uses three provider calls: a Fix turn that stops at mutation approval, a resume of that exact Codex session after approval, and a distinct read-only review session. The report records the provider and model versions, harness, token range, duration, every failed or blocked attempt, and the bundled-account marginal provider cost available to the runner. A zero marginal charge is not a claim that inference has no economic cost.

## Fixture and replay

The runner initializes `examples/fix-demo/starting/` as a Git repository with fixed commit metadata and refuses to continue unless the resulting commit matches `fixture.json`. The defect independently rounds proportional line allocations, causing a ten-cent invoice discount to reconcile to nine cents. No expected repair is stored in the fixture. Codex must diagnose and repair the defect while the harness permits changes only to `src/invoice.py`.

Replay:

```bash
python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json
```

Plan without execution:

```bash
python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --plan --json
```

## Measurements

Runner-calculated fields are kept separate from human rubric fields:

| Metric | Calculation |
|---|---|
| task completion | clean PR-ready target and completed terminal class |
| verifier validity | the intended test fails before and the same suite passes after |
| resume integrity | the repair turn resumes the exact persisted Codex session that stopped at approval |
| claim accuracy | a distinct read-only Codex review and the completion audit both pass |
| scope control | the product diff contains only the fixture's allowlisted path |
| human load | count of explicit approval decisions; duration is reported by run time |
| time and cost | median, minimum, maximum, and spread across every attempt |

Blocked, failed, and timed-out attempts remain in the denominator. A run cannot pass with missing raw evidence, a nonzero provider exit, a false calculated control, or an unsuccessful terminal status. `--verify-replay` additionally requires matching terminal classes and invariant fingerprints across all attempts; it does not require generated patches or prose to be byte-identical.

## Evidence and privacy

Each attempt retains install health, red/green verifier output, interrupted and resumed Codex traces, final diff, independent review, completion audit, and a schema-valid run report. Before persistence, the runner replaces workspace and ADLC-root paths, scans serialized artifacts for common credential and private-path patterns, and fails closed on a match. Candidate publication additionally requires a second clean three-run replay, a SHA-256 manifest binding every referenced raw artifact, and a separate-session reconciliation and redaction attestation tied to explicit human approval.

## Honesty and limitations

The result applies only to the named fixture, ADLC version, source commit, environment, provider/model version, harness, and execution date. Passing results show that the measured controls held in those runs. They do not establish universal superiority, future provider/model behavior, reliability outside the sample, traction, compliance certification, GA readiness, or general autonomous-code quality.
