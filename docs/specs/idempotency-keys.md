# Idempotency Keys Spec

## Purpose
Prevent duplicate side effects when ADLC phases or skills retry after timeout, crash, or partial completion.

## Key Format
```text
{brief_id}:{skill_name}:{task_id}:{operation}
```

`run_id` is not part of the idempotency key. A resume must reuse the same work-item keys even when `resume_count` or `attempt` changes. Store `run_id`, `session_id`, and `brief_id` beside the side-effect record for correlation.

## Skill-Specific Keys
- JIRA Ticket Creation: `{brief_id}:jira:{task_id}`
- GitHub Issue Creation: `{brief_id}:github:{task_id}`
- Linear Ticket Creation: `{brief_id}:linear:{task_id}`
- Confluence Decomposition: `{brief_id}:confluence:{section_id}`
- Notion Decomposition: `{brief_id}:notion:{section_id}`
- Architecture Scaffolding: `{brief_id}:scaffold:{component_name}`
- Grafana Observability: `{brief_id}:grafana:{dashboard_name}`
- CI/CD Pipeline: `{brief_id}:cicd:{pipeline_name}`
- Slack Orchestration: `{brief_id}:slack:{event_type}:{target}`
- Git operations: `{brief_id}:git:{operation}:{ref}`
- Work-item emitter stable external ID: `{brief_id}:{target}:{task_id}:upsert`
- Work-item status sync: `{brief_id}:{target}:{task_id}:upsert:sync:{update_id}`

For work-item synchronization, the `:upsert` key identifies the tracker item and prevents duplicate ticket creation. The `:sync:{update_id}` key identifies a specific status/evidence append so repeated provider calls can dedupe the same update without preventing later run updates from appending to the same ticket.

## Required Behavior
1. Compute key before any external mutation.
2. Check durable store by `idempotency_key`.
3. If key exists and status is `completed` or `deduplicated`, return existing artifact metadata.
4. If key exists with `failed`, retry only if operation is marked retryable.
5. Record result in `workflow-state.side_effects[]` with `run_id`, `session_id`, and `brief_id`.

## Response Contract
```json
{
  "idempotency_key": "BRF-123:jira:TASK-7:create",
  "run_id": "ADLC-RUN-001",
  "session_id": "S-001",
  "brief_id": "BRF-123",
  "status": "deduplicated",
  "artifact_id": "ENG-781",
  "artifact_ref": "https://jira/.../ENG-781"
}
```
