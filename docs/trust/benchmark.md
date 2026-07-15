# Public Fix benchmark

ADLC's first public benchmark measures whether its documented Fix controls work on one versioned invoice-allocation defect. It does not compare ADLC with another framework or declare a winner. The complete method, scoring rules, failure denominator, and privacy boundary are in [`benchmarks/methodology.md`](https://github.com/bigeasyfreeman/adlc/blob/v0.9.2/benchmarks/methodology.md).

Replay the three-run configuration from a source checkout:

```bash
python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json
```

The runner refuses an unpinned fixture, records every attempted run, validates each run report and the summary against schemas, scans redacted artifacts for secret-like values, and reports median plus spread. It scores task completion, red-before-green verifier validity, interrupt/resume integrity, completion-claim accuracy, scope control, human decisions, time, tokens, and cost. Missing evidence, a blocked/failed/timeout terminal class, or any false calculated control cannot pass.

The initial configuration invokes the disclosed Codex model. Every attempt persists the session that stopped at approval, resumes that exact session for the repair, and uses a different read-only Codex session for review. The [`v0.1.0` candidate report](https://github.com/bigeasyfreeman/adlc/blob/v0.9.2/docs/evidence/benchmarks/v0.1.0/benchmark-report.json) preserves all three attempts and their redacted raw artifacts; a separate clean three-run replay and publication attestation are stored beside it. All six candidate attempts passed, but the [provider support matrix](support-matrix.md) remains the canonical source for provider-support labels.

`doc_honesty_section`: This page describes a scoped, rerunnable control benchmark and links its raw evidence and method.

`no_overclaim`: The benchmark does not claim universal superiority, future provider/model behavior, adoption, cost savings, compliance, autonomous code quality, or GA readiness.

`limitations`: Results apply only to the named fixture, product/source version, environment, Codex/model version, live harness, execution date, and six-run publication sample. They do not predict future provider behavior.
