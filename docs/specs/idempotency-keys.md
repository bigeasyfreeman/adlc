# Idempotency Keys Spec

## Purpose
Prevent duplicate side effects when ADLC phases or skills retry after timeout, crash, or partial completion.

## Key Format
```text
{brief_id}:{skill_name}:{task_id}:{operation}
```

## Skill-Specific Keys
- JIRA Ticket Creation: `{brief_id}:jira:{task_id}`
- Confluence Decomposition: `{brief_id}:confluence:{section_id}`
- Architecture Scaffolding: `{brief_id}:scaffold:{component_name}`
- Grafana Observability: `{brief_id}:grafana:{dashboard_name}`
- CI/CD Pipeline: `{brief_id}:cicd:{pipeline_name}`
- Slack Orchestration: `{brief_id}:slack:{event_type}:{target}`
- Git operations: `{brief_id}:git:{operation}:{ref}`

## Required Behavior
1. Compute key before any external mutation.
2. Check durable store by `idempotency_key`.
3. If key exists and status is `completed` or `deduplicated`, return existing artifact metadata.
4. If key exists with `failed`, retry only if operation is marked retryable.
5. Record result in `workflow-state.side_effects[]`.

## Response Contract
```json
{
  "idempotency_key": "BRF-123:jira:TASK-7:create",
  "status": "deduplicated",
  "artifact_id": "ENG-781",
  "artifact_ref": "https://jira/.../ENG-781"
}
```
