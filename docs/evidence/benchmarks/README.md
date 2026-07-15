# Public benchmark evidence

Versioned benchmark directories contain the summary report and every redacted raw attempt used in its denominator. Historical reports are append-only: a new product, fixture, provider, model, harness, or methodology version produces a new report instead of rewriting an old result.

The initial configuration is a deterministic control replay with Codex installed but no provider or model invoked. See [`benchmarks/methodology.md`](../../../benchmarks/methodology.md) for scoring, replay, redaction, and limitations. A result is publishable only after schema validation, secret scanning, an independent clean-environment replay, and human redaction approval.

No benchmark in this directory supports a claim of universal superiority or GA readiness.
