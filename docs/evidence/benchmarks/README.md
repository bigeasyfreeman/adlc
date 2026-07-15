# Public benchmark evidence

Versioned benchmark directories contain the summary report and every redacted raw attempt used in its denominator. Historical reports are append-only: a new product, fixture, provider, model, harness, or methodology version produces a new report instead of rewriting an old result.

The initial configuration is a deterministic control replay with Codex installed but no provider or model invoked. See [`benchmarks/methodology.md`](../../../benchmarks/methodology.md) for scoring, replay, redaction, and limitations. A result is publishable only after schema validation, secret scanning, an independent clean-environment replay, and human redaction approval.

The `v0.1.0` candidate evidence preserves all three passing attempts and their raw artifacts. Its [summary report](v0.1.0/benchmark-report.json) names source commit `c596b4bfb8e19998647a9e421cd92451628226b3`, Python 3.9.6 on Darwin arm64, one human approval per run, and zero provider tokens or cost. The report records the observed median and spread; those measurements do not transfer to another environment or configuration.

No benchmark in this directory supports a claim of universal superiority or GA readiness.
