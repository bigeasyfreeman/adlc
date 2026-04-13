# Contract Chain Invariant Tests

## Harness Setup
- Use fixed contract fixtures for PRD, Repo Map, Build Brief, Eval Verdict, and Skill MCP I/O.
- Enforce version rules from `docs/specs/skill-contract-versioning.md` and `docs/specs/version-compatibility-matrix.md`.
- Validate every producer/consumer handoff in sequence.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| CHAIN-01 | Required `contract_version` exists at every hop | Run PRD → Build Brief → Eval Council → Skill invocation chain with 1.x fixtures. | Every input/output payload includes `contract_version`; chain completes. | Any hop omits `contract_version`. |
| CHAIN-02 | Major-version mismatch is rejected with canonical error | Send skill request with expected `1.x` and received `2.0.0`. | Skill returns `error=contract_version_incompatible` with `expected`, `received`, and `skill` fields. | Request is accepted or error shape differs from spec. |
| CHAIN-03 | Compatible minor/patch versions negotiate successfully | Send expected `1.x`, received `1.4.2` across two skills. | Skills resolve supported version and execute normally. | Skills reject compatible minor/patch versions. |
| CHAIN-04 | Matrix compatibility enforcement | Set Build Brief producer to `2.x` while downstream consumers remain `1.x`. | Harness marks chain blocked until compatibility matrix and consumers are updated. | Chain proceeds with incompatible producer/consumer majors. |
| CHAIN-05 | Applicability manifest is required and schema-valid | Run triage → planner with a fixture task and validate `applicability_manifest` against the dedicated schema. | Build Brief contains `task_classification`, `change_surface`, provenance, section policy, and `verification_spec`. | Brief omits the manifest or emits fields that do not validate. |
| CHAIN-06 | Build-validation tasks suppress non-applicable overlays | Send a canonical build-validation fixture through planning and council pre-check. | Security/observability overlays are either inactive with concrete reasons or active only when change-surface flags justify them. | Brief pads suppressed overlays with generic prose or contradicts its own narrow scope. |
| CHAIN-07 | Task verifier contract survives handoff | Pass a task with `task_classification=bugfix` and a `verification_spec` through planner → codegen-context → coder fixture chain. | The downstream task prompt preserves the same primary verifier and expected fail/pass behavior. | A downstream consumer drops or rewrites the verifier contract. |
| CHAIN-08 | Small issue benchmark stays covered | Validate `tests/fixtures/applicability-issue-set.json` against repo expectations. | The benchmark includes build-validation, lint-cleanup, bugfix, feature, and security-sensitive cases with explicit overlay/verifier expectations. | Benchmark drift drops a task class, omits contamination coverage, or loses overlay gating expectations. |
