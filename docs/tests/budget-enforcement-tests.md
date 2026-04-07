# Budget Enforcement Invariant Tests

## Harness Setup
- Use budget fixture from `docs/specs/token-budgets.md` and algorithm from `docs/specs/pre-turn-check.md`.
- Feed fixed token-estimate inputs to avoid nondeterminism.
- Validate emitted events and stop reasons in machine-readable summary.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| BUD-01 | Warning threshold behavior (50%) | Set projected usage to `warn_at <= projected_total < alert_at`; run pre-turn check. | Call proceeds and emits `budget.warning`. | Call blocks or warning event is missing. |
| BUD-02 | Wrap-up mode behavior (80%) | Set projected usage to `alert_at <= projected_total < hard_stop_at`. | Call proceeds in wrap-up mode and emits structured pending-work report marker. | Full-depth execution continues without wrap-up marker. |
| BUD-03 | Hard stop behavior (100%) | Set projected usage `>= hard_stop_at`; attempt model call. | Call is blocked with `reason=budget_exhausted` and required hard-stop payload fields. | Model call executes or response omits required fields. |
| BUD-04 | Eval Council circuit breaker | Iteration 1 consumes >50% council budget; iteration 2 fails with insufficient headroom for iteration 3. | Iteration 3 is blocked; council budget remains isolated from codegen budget. | Iteration 3 runs despite insufficient headroom or budget pools are mixed. |
