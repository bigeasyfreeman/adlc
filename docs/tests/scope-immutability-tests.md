# Scope Immutability Invariant Tests

## Harness Setup
- Use fixed PRD fixture `PRD-FIX-001` and fixed brief `BRF-123`.
- Mock all skills and LLM calls with deterministic fixtures per `docs/specs/verification-harness.md`.
- Record machine-readable result entries per test.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| SIM-01 | Scope freeze holds after Phase 8 | Complete `phase_8_task_breakdown` with task set hash `H1`; run `phase_9_codegen_execution` and `phase_10_jira_confluence_prep`. | `scope_hash` remains `H1`; no added/removed tasks in downstream checkpoints. | Any downstream checkpoint mutates task set without an approved Type 1 decision. |
| SIM-02 | Unapproved scope expansion is blocked | Inject new task `TASK-99` during `phase_9_codegen_execution` without Type 1 approval metadata. | Pipeline stops before mutation with `stop_reason=type1_unresolved`; checkpoint keeps original scope. | `TASK-99` appears in checkpoint or external artifacts. |
| SIM-03 | Approved Type 1 scope change is explicit and auditable | Re-run SIM-02 with Type 1 approval fixture (`decision_type=type1`, approver present). | Scope change is accepted and checkpoint includes approval reference + updated scope hash. | Scope changes without approval reference or hash transition evidence. |
