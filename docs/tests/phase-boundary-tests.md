# Phase Boundary Invariant Tests

## Harness Setup
- Use ordered ADLC phase fixtures from `docs/specs/workflow-checkpoints.md` (Phase 0 through Phase 13).
- Enforce schema validation before/after each phase boundary.
- Record checkpoint transitions in deterministic timeline output.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| PHASE-01 | No phase skipping | Attempt transition from Phase 1 directly to Phase 3. | Transition is rejected; latest valid checkpoint remains Phase 1. | Phase 3 checkpoint is created without Phase 2 completion. |
| PHASE-02 | Boundary schema validation is mandatory | Inject invalid checkpoint payload at Phase 5 output (missing required field). | Boundary validator blocks Phase 6 start and emits schema failure. | Phase 6 starts with invalid Phase 5 output. |
| PHASE-03 | Resume starts at last executing/failed step | Seed latest checkpoint as `phase_6_parallel_codegen`, `status=failed`; call `resumeWorkflow(BRF-123)`. | Response resumes from Phase 6 and lists later phases as remaining. | Resume restarts from Phase 0 or skips to later phase. |
| PHASE-04 | Failure cleanup respects phase contract | Simulate Phase 3 failure with partial file manifest. | Cleanup removes only files created in failed run per manifest. | Cleanup removes files outside failed run manifest. |
