# Public benchmark evidence

Versioned benchmark directories contain the summary report and every redacted raw attempt used in its denominator. Historical reports are append-only: a new product, fixture, provider, model, harness, or methodology version produces a new report instead of rewriting an old result.

The initial configuration is a live resumable Codex Fix benchmark. See [`benchmarks/methodology.md`](../../../benchmarks/methodology.md) for scoring, provider-call bounds, replay, redaction, and limitations. Candidate evidence is publishable only after schema validation, secret and private-path scanning, an independent clean three-run replay, a separate-session reconciliation review, and explicit human approval.

The `v0.1.0` candidate preserves a [primary report](v0.1.0/benchmark-report.json), [independent replay](v0.1.0/independent-replay/benchmark-report.json), and [publication attestation](v0.1.0/publication-attestation.json) for source commit `89140f4dbcc2454738435d6c44a41f70e39ba076`. Both sets passed 3/3 attempts with no blocked, failed, or timed-out attempt. Primary duration was 148–217 seconds with 297,353–550,517 observed tokens per attempt; replay duration was 163–233 seconds with 343,602–390,655 tokens. The harness reported zero marginal USD charge under the bundled account, which is not a claim that inference is economically free. These measurements do not transfer to another account, environment, fixture, configuration, or model version.

No benchmark in this directory supports a claim of universal superiority or GA readiness.
