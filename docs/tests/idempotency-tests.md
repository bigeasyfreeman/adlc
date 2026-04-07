# Idempotency Invariant Tests

## Harness Setup
- Use fixed `brief_id=BRF-123` and fixed side-effect store snapshot.
- Enforce key format from `docs/specs/idempotency-keys.md`.
- Mock external systems (JIRA, Confluence, Grafana, Git) with deterministic responses.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| IDEMP-01 | Duplicate create is deduplicated | Execute JIRA create twice with key `BRF-123:jira:TASK-7:create`. | Second response returns `status=deduplicated` and same `artifact_id`; no second external mutation call. | Two distinct ticket IDs are created or response omits idempotency metadata. |
| IDEMP-02 | Completed key replays artifact metadata | Seed store with `status=completed` for Confluence key; execute same operation. | Operation short-circuits and returns stored artifact ref without mutation call. | Operation mutates external system again. |
| IDEMP-03 | Failed non-retryable key is blocked | Seed store with `status=failed` and `retryable=false`; retry operation. | Harness returns blocked result with no mutation call. | Operation retries despite non-retryable flag. |
| IDEMP-04 | Failed retryable key retries once and records result | Seed store with `status=failed` and `retryable=true`; retry succeeds. | New result stored in `workflow-state.side_effects[]` with same key and terminal status. | Result not persisted, or key changes across retry. |
