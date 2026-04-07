# Token Budgets Spec

## Default Budget Allocation
| Area | Budget |
|---|---:|
| Codebase Research | 100,000 |
| Build Brief conversation (all phases) | 200,000 |
| Eval Council per iteration | 100,000 |
| Eval Council total | 300,000 |
| Codegen Context per task | 50,000 |
| Coding Agent per task | 80,000 |
| Security skills per task | 30,000 |
| **Total session default** | **1,000,000** |

## Rules
1. Session starts with configured budget or default 1M.
2. Track tokens by phase and by skill invocation.
3. Enforce pre-turn check for every model call.
4. Emit warnings at 50%, alerts at 80%, stop at 100%.

## Override Mechanism
Per-brief override payload:
```json
{
  "brief_id": "BRF-123",
  "budget_override": {
    "session_total": 1400000,
    "phase_limits": {"phase_2_eval_council": 400000},
    "task_limits": {"TASK-7": 120000}
  },
  "approved_by": "engineering_manager"
}
```

## Output Requirement
Final report must include `tokens_by_phase`, `tokens_by_skill`, and estimated cost by model.
