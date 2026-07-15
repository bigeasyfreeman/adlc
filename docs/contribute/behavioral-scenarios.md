# Behavioral scenario authoring

Behavioral scenarios should test observable loop contracts rather than prompt wording.

Each scenario names the provider/harness/version, fixture digest, loop, preconditions, expected red evidence, mutation boundary, required gates, interruption/recovery behavior, terminal state, and no-overclaim limitation. Preserve failed attempts and variance. Use at least three runs before a beta provider-behavior claim.

Deterministic fixtures belong under `tests/skill_behavior`, `tests/provider_conformance`, or `tests/acceptance` as appropriate. Published evidence belongs under `docs/evidence/` and must validate against its schema. Credentials and raw sensitive traces never belong in fixtures.

Run the scenario from a clean checkout and prove that it does not create an undeclared tracked diff.
