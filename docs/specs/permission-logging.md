# Permission Logging Spec

## Purpose
Record every allow/deny decision as auditable structured data.

## Log Entry Contract
```json
{
  "tool": "jira-ticket-creation",
  "action": "create_issue",
  "tier": "requires_approval",
  "decision": "approved",
  "decided_by": "human",
  "timestamp": "2026-04-06T20:00:00Z",
  "rationale": "Brief approved; phase_10 mutation allowed"
}
```

## Required Capture Points
- before tool invocation decision
- after policy override
- on denial (include concrete reason)
- on escalation approval/rejection

## Reporting
Session summary must include:
- total approvals/denials
- repeated denial patterns
- unresolved escalation requests
