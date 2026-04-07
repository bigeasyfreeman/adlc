# Session Persistence Spec

## Purpose
Ensure ADLC runs survive crash/restart without losing state or duplicating side effects.

## Persistence Triggers
Persist session state after:
- every engineer/user message
- every skill invocation (start + finish)
- every permission decision
- every phase transition
- every Eval Council verdict

## Stored State
- conversation history
- token usage totals
- permission decision log
- workflow state reference
- runtime configuration (model, budgets, skill config)

## `resumeSession(sessionId)` Contract
**Input:** `sessionId`
**Output:**
```json
{
  "session_id": "S-001",
  "status": "active",
  "restored_phase": "phase_6_parallel_codegen",
  "restored_permissions": 23,
  "restored_token_usage": 412340
}
```

## Backend Requirements
- durable writes (fsync/transactional)
- atomic update per checkpoint
- corruption detection via checksum/version field
