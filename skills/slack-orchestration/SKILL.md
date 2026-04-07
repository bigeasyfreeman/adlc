# Skill: Slack Workflow Orchestration

> Manages the end-to-end workflow from PRD to Build Brief to approval to coding kickoff. Posts summaries, routes Type 1 escalations, collects approvals, and tracks decision resolution. This is the glue that connects all ADLC agents and skills.

---

## Trigger

Multiple trigger points throughout the ADLC lifecycle:

| Trigger | Event | Action |
|---------|-------|--------|
| PRD Handoff | Product Agent completes PRD | Notify engineer, start Build Brief |
| Brief Completed | Build Brief Agent finishes | Post summary, request review |
| Type 1 Escalation | Unresolved Type 1 decision | Escalate to decision owner |
| Brief Approved | Engineer approves | Trigger downstream skills |
| Blocker Detected | Blocker in Open Questions | Notify blocker owner |
| Deploy Gate | Phase 1 ready for deploy | Request deploy approval |
| Incident | SLO breach post-deploy | Page on-call, post runbook |

## Input Contract

```json
{
  "event_type": "prd_handoff | brief_complete | type1_escalation | brief_approved | blocker | deploy_gate | incident",
  "payload": {
    "feature_name": "string",
    "owner": "string",
    "channel": "string (Slack channel ID or name)",
    "escalation_channel": "string (for Type 1 decisions)",
    "content": "string (varies by event type)",
    "decision": {
      "description": "string",
      "type": "Type 1",
      "owner": "string",
      "deadline": "ISO date",
      "options": ["string"],
      "context": "string (from Build Brief)"
    },
    "build_brief_url": "string (Confluence link)",
    "jira_epic_key": "string"
  }
}
```

## Output Contract

```json
{
  "message_ts": "string (Slack message timestamp for threading)",
  "channel": "string",
  "action_taken": "string",
  "awaiting_response_from": "string (user ID, if escalation)",
  "deadline": "ISO date (if escalation)",
  "follow_up_scheduled": "boolean"
}
```

## Behavior

### 1. PRD Handoff (Product Agent → Build Brief Agent)

When a PRD is finalized by the Product Agent:

```
📋 *New PRD Ready for Technical Design*
Feature: [Feature Name]
PRD: [link]
Owner: [Product Manager]
Target: [date]

@[assigned-engineer] — ready for Build Brief. Run the ADLC Build Brief Agent against this PRD.

React ✅ to acknowledge, 🔄 if you need to reassign.
```

### 2. Brief Completed

When the Build Brief Agent finishes:

```
📐 *Build Brief Complete: [Feature Name]*
Owner: @[engineer]
Phase 1 Target: [date]
Tickets: [N] across Backend/Frontend/Infra/Observability

*Key Decisions:*
• [Type 1 decision 1 — status]
• [Type 1 decision 2 — status]

*Top Risk:* [biggest risk from Section 4]
*SLO:* [availability target] availability, [latency] p99

📄 Full Brief: [Confluence link]
🎫 Epic: [JIRA link]

@[reviewer] — please review. React ✅ to approve, ❌ to request changes.
```

### 3. Type 1 Escalation

When a Type 1 decision is unresolved after brief completion:

```
🚨 *Type 1 Decision — Escalation Required*
Feature: [Feature Name]
Decision: [description]

*Context:* [1-2 sentences from the Build Brief explaining why this matters]

*Options:*
1️⃣ [Option A] — [tradeoff]
2️⃣ [Option B] — [tradeoff]

*Impact of delay:* [what blocks if this isn't decided]
*Deadline:* [date]

@[decision-owner] — this blocks the first slice. Please decide by [deadline].
```

**Escalation ladder:**
- Day 0: Post in feature channel, tag decision owner
- Day 1: DM the decision owner
- Day 2: Post in escalation channel, tag decision owner's manager
- Day 3: Post in leadership channel, mark as blocking

### 4. Brief Approved → Skill Trigger

When the engineer reacts ✅ to the brief summary:

```
✅ *Build Brief Approved: [Feature Name]*
Triggering downstream workflows:

• 📄 Confluence pages — creating...
• 🎫 JIRA tickets — creating [N] tickets in [project]...
• 🧪 QA test data — generating fixtures and scenarios...
• 🔧 CI/CD pipelines — generating/updating workflows...
• 📖 Runbook — creating incident runbook shell...

Will post links when complete.
```

Then post each skill's output as a thread reply:
```
📄 Confluence pages created: [links]
🎫 JIRA epic: [link] ([N] tickets created)
🧪 Test fixtures written to [path]
🔧 Pipeline updated: [workflow file]
📖 Runbook created: [Confluence link]
```

### 5. Blocker Notification

When an open question is marked as Blocker:

```
🔴 *Blocker: [Feature Name]*
Question: [description]
Owner: @[owner]
Impact: Blocks Phase 1 start

@[owner] — please resolve or escalate by [deadline].
```

### 6. Deploy Gate

When Phase 1 tasks are all marked done:

```
🚀 *Deploy Gate: [Feature Name] Phase 1*
All [N] Phase 1 tickets complete.

*Pre-deploy checklist:*
☐ Code reviewed and merged
☐ Tests passing in CI
☐ Runbook reviewed
☐ On-call rotation confirmed: [rotation name]
☐ SLO dashboards configured

@[owner] — react ✅ to approve deploy, ❌ to hold.
```

### 7. Incident Response

When SLO breach detected post-deploy:

```
🔥 *SLO Breach: [Feature Name]*
Metric: [which SLO]
Current: [current value]
Target: [target value]
Duration: [how long]

📖 Runbook: [link]
🎫 Related tickets: [links to failure mode tickets]
📟 On-call: @[on-call-engineer]

@[on-call-engineer] — runbook linked above. Escalation path: [escalation contact].
```

## MCP Server Contract

### Tool: `post_workflow_message`

```json
{
  "name": "post_workflow_message",
  "description": "Post an ADLC workflow message to Slack",
  "inputSchema": {
    "type": "object",
    "properties": {
      "event_type": {
        "type": "string",
        "enum": ["prd_handoff", "brief_complete", "type1_escalation", "brief_approved", "blocker", "deploy_gate", "incident"]
      },
      "channel": {
        "type": "string",
        "description": "Slack channel name or ID"
      },
      "payload": {
        "type": "object",
        "description": "Event-specific payload"
      }
    },
    "required": ["event_type", "channel", "payload"]
  }
}
```

### Tool: `check_decision_status`

```json
{
  "name": "check_decision_status",
  "description": "Check if a Type 1 decision has been resolved via Slack reaction or thread reply",
  "inputSchema": {
    "type": "object",
    "properties": {
      "message_ts": {
        "type": "string",
        "description": "Slack message timestamp of the escalation"
      },
      "channel": {
        "type": "string",
        "description": "Slack channel"
      }
    },
    "required": ["message_ts", "channel"]
  }
}
```

### Tool: `escalate_decision`

```json
{
  "name": "escalate_decision",
  "description": "Escalate an unresolved Type 1 decision to the next level",
  "inputSchema": {
    "type": "object",
    "properties": {
      "decision_description": "string",
      "current_owner": "string",
      "escalation_channel": "string",
      "escalation_level": {
        "type": "integer",
        "description": "1 = DM, 2 = manager, 3 = leadership"
      }
    },
    "required": ["decision_description", "current_owner", "escalation_channel"]
  }
}
```

## CLI Interface

```bash
# Post brief completion summary
adlc-slack notify --event brief_complete --brief ./build-brief.md --channel #eng-feature

# Escalate a Type 1 decision
adlc-slack escalate --decision "Schema change for multi-tenancy" --owner @jane --channel #eng-leads

# Check decision status
adlc-slack status --message-ts 1234567890.123456 --channel #eng-feature

# Trigger skill chain after approval
adlc-slack trigger-skills --brief ./build-brief.md --channel #eng-feature
```

## Escalation Timing

| Level | Trigger | Action |
|-------|---------|--------|
| L0 | Decision posted | Tag owner in feature channel |
| L1 | +24h no response | DM the owner directly |
| L2 | +48h no response | Post in escalation channel, tag owner's manager |
| L3 | +72h no response | Post in leadership channel, mark feature as blocked |

Each escalation includes the original context, options, and impact of delay. No context is lost between levels.

## Quality Gates

- [ ] Every Build Brief completion posts a summary to Slack
- [ ] Every unresolved Type 1 decision has an escalation message
- [ ] Approval reaction triggers all downstream skills
- [ ] Escalation ladder fires on schedule (24h, 48h, 72h)
- [ ] Deploy gate blocks on unchecked items
- [ ] Incident response tags on-call and links runbook

## Framework Hardening Addendum

- **Contract versioning:** Event payload contracts must include `contract_version` with semver compatibility checks.
- **Schema validation:** Validate event payloads against declared schema before posting or escalating.
- **Idempotency:** Escalation and notification sends must dedupe by event idempotency key to prevent duplicate alerts.
- **Structured events:** Include workflow state identifiers (`session_id`, `brief_id`, `phase`, `stop_reason`) in every orchestration message payload.

