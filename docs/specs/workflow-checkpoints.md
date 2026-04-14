# Workflow Checkpoints Spec

## Purpose
Define resumable checkpoints for each ADLC phase and recovery behavior after partial failure.

## Checkpoint Contract
Every phase completion writes:
- `phase`
- `step`
- `status`
- `checkpoint` (phase payload)
- `side_effects[]`
- `updated_at`

## Phase Checkpoints
| Phase | Capture | Resume Requires | Cleanup on Failure |
|---|---|---|---|
| 0 Research | repo map version, key findings | repo map cache handle | clear invalid cache entry |
| 0a Grafana | baseline queries + dashboard refs | workspace/org IDs | remove partial dashboard with same key |
| 1 Brief Prefill | extracted PRD fields | schema-valid PRD payload | reset incomplete extraction fields |
| 2 Eval Council | iteration, persona findings, verdict | prior brief hash + iteration counter | mark iteration failed and preserve findings |
| 3 Scaffolding | target files + generated paths | file manifest + hash | remove only files created in failed run |
| 4 Failing Tests | test plan + expected failures | task ticket IDs | clear temp fixtures |
| 5 Codegen Context | prompt bundles per task | repo map + task IDs + budget snapshot | invalidate incomplete bundles |
| 6 Parallel Codegen | task worker states | task queue state | rerun only incomplete tasks |
| 7 Security Review | domain assessments | generated diffs + task IDs | mark unresolved findings |
| 8 Task Breakdown | finalized task ticket set | brief hash + scope freeze | regenerate only invalid tasks |
| 9 Codegen Execution | merged patches + validations | branch ref + task completion map | revert failed partial patch |
| 10 Artifact Publishing Prep | external artifact refs | idempotency keys | dedupe via emitter-specific key lookups |
| 11 CI/CD + QA Prep | pipeline and QA configs | config IDs + commit SHA | remove invalid generated configs |
| 12 Deploy Gate | gate verdict + evidence links | latest council verdict | keep gate closed on failure |
| 13 Monitoring Feedback | post-deploy metrics snapshot | deployment ID + dashboard refs | mark monitoring run incomplete |

## `resumeWorkflow(briefId)` Contract
**Input:** `briefId` (required), optional `targetPhase`.
**Output:** `{ status, resumed_from_phase, resumed_step, remaining_phases[], recovery_report }`.

Behavior:
1. Load latest checkpoint for `briefId`.
2. Validate schema and idempotency status of side effects.
3. Resume from last `status=executing|failed` step.
4. Emit recovery report:
   ```json
   {"total": 18, "completed": 12, "failed": 2, "remaining": 4, "failures": []}
   ```
5. If checkpoint is corrupted, stop with `stop_reason=skill_failed_unrecoverable`.
