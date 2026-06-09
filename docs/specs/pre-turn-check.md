# Pre-Turn Budget Check Spec

## Purpose
Enforce budget checks before every LLM call to prevent runaway spend and incomplete outputs.

## Pre-Turn Algorithm
1. Estimate `input_tokens` from prompt payload.
2. Estimate `expected_output_tokens` by model + phase profile.
3. Compute `projected_total = tokens_used + input_tokens + expected_output_tokens`.
4. Compare projected usage to thresholds from `token-budget.schema.json`.

## Decision Rules
- `< warn_at`: proceed.
- `>= warn_at && < alert_at`: proceed and emit `budget.warning`.
- `>= alert_at && < hard_stop_at`: enter **wrap up mode**.
- `>= hard_stop_at`: block call and emit stop reason `budget_exhausted`.
- stale budget artifact: block autonomous maturity claims and emit stop reason `budget_stale`.

## Wrap Up Mode
When budget is above 80%:
- prioritize summarizing remaining work,
- skip optional deep dives,
- emit a structured pending-work report.

## Hard Stop Response
```json
{
  "reason": "budget_exhausted",
  "tokens_used": 812340,
  "budget": 800000,
  "phase": "phase_2_eval_council",
  "recommendation": "increase budget or resume with compacted context"
}
```

## Eval Council Circuit Breaker
- If iteration 1 consumes >50% of council budget, iteration 2 must use compressed brief input.
- If iteration 2 still fails and council budget headroom is below required estimate, block iteration 3.
- Council budget is isolated from codegen budget.

## Loop Contract Integration

When a Loop Contract includes `budget_guard`, the pre-turn check is executable through `bin/adlc loop-budget-check`. `loop-action-validate` can consume the same token budget before admitting an LLM action, and `loop-maturity-audit` records the resulting `budget_status`. Missing, stale, warning, alert, or exhausted budget evidence blocks `self_autonomous` but does not invalidate legacy `assisted_loop` contracts.
