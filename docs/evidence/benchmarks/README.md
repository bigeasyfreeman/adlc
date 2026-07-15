# Public benchmark evidence

Versioned benchmark directories contain the summary report and every redacted raw attempt used in its denominator. Historical reports are append-only: a new product, fixture, provider, model, harness, or methodology version produces a new report instead of rewriting an old result.

The initial configuration is a live resumable Codex Fix benchmark. See [`benchmarks/methodology.md`](../../../benchmarks/methodology.md) for scoring, provider-call bounds, replay, redaction, and limitations. Candidate evidence is publishable only after schema validation, secret and private-path scanning, an independent clean three-run replay, a separate-session reconciliation review, and explicit human approval.

The `v0.1.0` directory is populated only from the final primary run, clean replay, and publication attestation. Its report records observed token and duration medians and spreads, plus the bundled-account marginal provider charge available to the harness. Those measurements do not transfer to another account, environment, fixture, configuration, or model version.

No benchmark in this directory supports a claim of universal superiority or GA readiness.
