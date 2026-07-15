# Benchmark method and evidence status

A public ADLC benchmark must use a versioned fixture, at least three runs per claimed configuration, fixed success predicates, redacted replayable traces, exact ADLC/provider/model versions, duration and cost ranges, all failures, and clean-checkout replay instructions.

The benchmark must separately score installation, discovery, invocation, loop behavior, interruption/resume, verifier strength, independent audit, and end-to-end outcome. A deterministic fixture cannot upgrade a live-provider invocation cell.

Current evidence is the [provider support matrix](support-matrix.md) and the [deterministic Fix replay](../../tests/acceptance/run_public_fix_loop.sh). MIG012 owns the versioned public demo and replayable benchmark; no comparative or superiority result is claimed before that gate passes.

`doc_honesty_section`: This page defines the benchmark contract and points to current scoped evidence.

`no_overclaim`: It does not claim benchmark completion, superiority, cost savings, or market value.

`limitations`: Provider behavior and pricing can drift after evidence time.
