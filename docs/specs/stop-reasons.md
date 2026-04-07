# Stop Reasons Taxonomy

## Canonical Reasons
- `completed`
- `budget_exhausted`
- `council_blocked`
- `engineer_rejected`
- `type1_unresolved`
- `crash_recovered`
- `skill_failed_unrecoverable`
- `timeout`

## Definitions and Actions
| Stop Reason | Trigger | User/Operator Next Action |
|---|---|---|
| completed | Pipeline reached terminal success | Archive artifacts and close session |
| budget_exhausted | Pre-turn check blocked call | Increase budget or resume with compaction |
| council_blocked | Eval Council returned BLOCKED | Revise brief and rerun council |
| engineer_rejected | Human gate rejected package | Apply requested changes and restart from checkpoint |
| type1_unresolved | Critical decision unresolved | Escalate for explicit approval |
| crash_recovered | Resume happened after crash | Validate state integrity and continue |
| skill_failed_unrecoverable | Skill failed without safe retry path | Manual remediation; rerun from prior checkpoint |
| timeout | Execution exceeded hard timeout | Retry with narrower scope or increased timeout |

## Terminal Event Contract
Terminal `pipeline.completed` and `pipeline.failed` events must include `stop_reason` and actionable `recommendation`.
