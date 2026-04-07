# Cost Reporting Spec

## Purpose
Provide deterministic cost visibility for each ADLC run.

## Report Shape
```json
{
  "session_id": "S-001",
  "brief_id": "BRF-123",
  "currency": "USD",
  "total_tokens": 542001,
  "total_estimated_cost": 18.42,
  "tokens_by_phase": {},
  "tokens_by_skill": {},
  "estimated_cost_by_model": {},
  "top_expensive_operations": [
    {"operation": "eval-council iteration 2", "tokens": 102345, "cost": 3.91}
  ]
}
```

## Emission Points
- Append to Build Brief output package.
- Post summary to Slack orchestration channel.
- Persist under workflow/session state.

## Calculation Rules
- Use configured model price table at runtime.
- Include retries and deduplicated attempts.
- Round costs to 4 decimal places internally, 2 for display.
