# Public Fix benchmark methodology

## Question

This benchmark asks whether the documented ADLC Fix controls work on one pinned invoice-allocation defect. It does not compare ADLC with another framework and does not score prose written by the framework itself.

The published deterministic configuration installs the Codex bundle but does not invoke Codex, a model, or any hosted provider. Provider tokens and cost are therefore exactly zero. A future model-backed configuration must use a new versioned report and disclose its provider, model, harness, token range, cost range, and every failed or blocked attempt.

## Fixture and replay

The runner initializes `examples/fix-demo/starting/` as a Git repository with fixed commit metadata and refuses to continue unless the resulting commit matches `fixture.json`. The defect independently rounds proportional line allocations, causing a ten-cent invoice discount to reconcile to nine cents. The bounded repair uses largest-remainder allocation and changes only `src/invoice.py`.

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
| resume integrity | the completed idempotency key occurs exactly once after resume |
| claim accuracy | the separate-session deterministic completion audit passes |
| scope control | the product diff contains only the fixture's allowlisted path |
| human load | count of explicit approval decisions; duration is reported by run time |
| time and cost | median, minimum, maximum, and spread across every attempt |

Blocked, failed, and timed-out attempts remain in the denominator. A run cannot pass with missing raw evidence, a false calculated control, or an unsuccessful terminal status. `--verify-replay` additionally requires matching terminal classes and invariant fingerprints across all attempts.

## Evidence and privacy

Each attempt retains red/green verifier output, install health, public-facade admission, interrupted and resumed state, final diff, review, completion audit, and a schema-valid run report. Before persistence, the runner replaces workspace and ADLC-root paths, scans serialized artifacts for common credential patterns, and fails closed on a match. Public evidence requires a separate redaction review and immutable version publication.

## Honesty and limitations

The result applies only to the named fixture, ADLC version, source commit, environment, deterministic harness, and execution date. Passing results show that the measured ADLC controls held in those runs. They do not establish universal superiority, provider/model behavior, future reliability, traction, compliance certification, GA readiness, or the quality of autonomous code generation.
