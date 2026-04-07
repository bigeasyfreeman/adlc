# Crash Recovery Invariant Tests

## Harness Setup
- Use deterministic checkpoint store snapshots and fixed side-effect records.
- Use `resumeWorkflow(briefId)` contract from `docs/specs/workflow-checkpoints.md`.
- Validate terminal stop reasons against `docs/specs/stop-reasons.md`.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| CRASH-01 | Resume after crash with completed side effect | Simulate crash after external write with persisted idempotency key and checkpoint `status=executing`. | Resume deduplicates side effect, continues from saved phase, and emits `stop_reason=crash_recovered` when applicable. | Resume repeats external write or restarts from incorrect phase. |
| CRASH-02 | Corrupted checkpoint is unrecoverable | Corrupt latest checkpoint schema and call `resumeWorkflow(BRF-123)`. | Workflow stops with `stop_reason=skill_failed_unrecoverable` and no phase execution occurs. | Workflow proceeds despite corrupted checkpoint. |
| CRASH-03 | Recovery report is complete and machine-readable | Resume from partial run with known totals (`total=18`, `completed=12`, `failed=2`, `remaining=4`). | `recovery_report` matches expected counts and includes failure list field. | Missing report fields or count mismatch. |
| CRASH-04 | Incomplete tasks only are rerun | Set Phase 6 task queue with 3 completed and 2 incomplete workers before crash. | Resume reruns only incomplete workers; completed workers remain untouched. | Completed workers rerun or incomplete workers are skipped. |
