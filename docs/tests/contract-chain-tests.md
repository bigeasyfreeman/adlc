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
