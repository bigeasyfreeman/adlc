# Skill: Incident Runbook Generation

> Generates incident runbooks from Build Brief failure modes, SLOs, and incident ownership definitions. Produces actionable runbooks that on-call engineers can follow at 2am without context loading.

---

## Trigger

Activated when Phase 1 is ready for deploy. Consumes Section 4 (Risk), Section 5 (Security), Section 6 (SLOs & Incident Ownership), and Section 11 (Failure Mode Roll-Up).

## Input Contract

```json
{
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "incident_ownership": {
    "on_call_rotation": "string",
    "escalation_contact": "string",
    "service_name": "string",
    "team": "string"
  },
  "slo_targets": {
    "availability": "string",
    "latency_p99": "string",
    "error_rate": "string",
    "burn_response": "string"
  },
  "failure_modes": [
    {
      "id": "FM-001",
      "description": "string",
      "area": "string",
      "severity": "P0 | P1 | P2 | P3",
      "likelihood": "L | M | H",
      "prevention": "string",
      "mitigation": "string",
      "early_warning": "string",
      "owner": "string"
    }
  ],
  "rollback_mechanism": "feature_flag | revert | migration_rollback | config | none",
  "rollback_details": "string",
  "security_posture": {},
  "confluence_config": {
    "space_key": "string",
    "parent_page_id": "string (runbook page from Confluence Skill)"
  }
}
```

## Output Contract

```json
{
  "runbook_page": {
    "page_id": "string",
    "url": "string",
    "title": "string"
  },
  "alert_configs": [
    {
      "name": "string",
      "condition": "string",
      "severity": "P0 | P1 | P2 | P3",
      "notification_channel": "string",
      "runbook_link": "string"
    }
  ],
  "summary": "string"
}
```

## Behavior

### 1. Generate Runbook Structure

Every runbook follows this structure (optimized for 2am reading):

```markdown
# Runbook: [Feature Name]

**Service:** [service name]
**Team:** [team]
**On-Call:** [rotation name]
**Escalation:** [contact name] → [manager] → [director]
**Last Updated:** [date]
**Build Brief:** [Confluence link]

---

## Quick Reference

| Symptom | Likely Cause | Action | Severity |
|---------|-------------|--------|----------|
| [symptom 1] | [FM-001] | [first action] | P0 |
| [symptom 2] | [FM-002] | [first action] | P1 |

---

## Rollback Procedure

**Mechanism:** [feature_flag | revert | migration_rollback | config]

### Steps (execute in order)
1. [Step 1 — with exact command or UI path]
2. [Step 2]
3. [Step 3]
4. Verify: [how to confirm rollback worked]

### If rollback fails
1. [Fallback action]
2. Escalate to [escalation contact] immediately
3. [Emergency measure]

---

## Failure Modes

### FM-001: [Description]

**Severity:** [P0-P3]
**Likelihood:** [L/M/H]

**How to detect:**
- Alert: [alert name and condition]
- Dashboard: [dashboard link]
- Manual check: [command or query]

**How to diagnose:**
1. Check [specific log / metric / dashboard]
2. Look for [specific pattern or error message]
3. Query: `[specific diagnostic command]`

**How to fix:**
1. [Immediate mitigation step]
2. [Root cause fix]
3. [Verification step]

**How to prevent recurrence:**
- [Prevention measure from brief]

---

[Repeat for each failure mode]

---

## SLO Dashboard Links

| SLO | Target | Dashboard | Alert |
|-----|--------|-----------|-------|
| Availability | [target] | [link] | [alert name] |
| Latency (p99) | [target] | [link] | [alert name] |
| Error Rate | [target] | [link] | [alert name] |

---

## Escalation Path

| Level | Who | When | How |
|-------|-----|------|-----|
| L1 | On-call engineer | Immediately | PagerDuty / OpsGenie |
| L2 | [Escalation contact] | If not resolved in 30 min | Slack DM + phone |
| L3 | [Engineering manager] | If not resolved in 1 hour | Phone call |
| L4 | [Director / VP] | If P0 and customer impact > 1 hour | Phone call + incident bridge |

---

## Contacts

| Role | Name | Slack | Phone |
|------|------|-------|-------|
| Feature Owner | [name] | @[handle] | [number] |
| On-Call | [rotation] | @[rotation-handle] | PagerDuty |
| Escalation | [name] | @[handle] | [number] |
```

### 2. Generate Per-Failure-Mode Sections

For each failure mode from the roll-up (Section 11):
- Translate "early warning" into a specific alert condition
- Translate "mitigation" into executable steps (commands, not descriptions)
- Translate "prevention" into post-incident action items
- Cross-reference the JIRA ticket that addresses this failure mode

**Critical rule:** Every step must be executable. Not "check the logs" but "Run `kubectl logs -l app=widget-service --tail=100 | grep ERROR`". Not "restart the service" but "Run `kubectl rollout restart deployment/widget-service -n production`".

If the skill cannot determine the exact command, it generates a TODO with the pattern:
```
TODO(@[owner]): Replace with exact command for [action]
```

### 3. Generate Alert Configurations

From SLO targets and failure modes, generate alert definitions:

```yaml
# alert_configs/feature-name-alerts.yml
alerts:
  - name: "widget-service-availability"
    condition: "error_rate > 0.001 for 5m"  # 99.9% availability
    severity: P1
    notification:
      channel: "#eng-alerts"
      pagerduty: "widget-service-rotation"
    runbook: "[confluence_link]#fm-001"

  - name: "widget-service-latency"
    condition: "p99_latency > 500ms for 5m"
    severity: P2
    notification:
      channel: "#eng-alerts"
    runbook: "[confluence_link]#fm-002"
```

### 4. Populate Confluence Runbook Page

Update the runbook page shell created by the Confluence Decomposition Skill with the full runbook content. Add:
- Confluence status macros for severity levels
- Expand macros for diagnostic commands
- Warning macros for P0 procedures
- Links to dashboards, JIRA tickets, and related pages

### 5. Create JIT On-Call Briefing

Generate a condensed "onboarding brief" for engineers rotating onto on-call who are unfamiliar with this feature:

```markdown
## On-Call Briefing: [Feature Name]

**What it does:** [1 sentence from Section 1]
**What can go wrong:** [top 3 failure modes, 1 sentence each]
**How to tell if it is broken:** [dashboard link + key metric]
**How to fix it fast:** [rollback steps, 3 lines max]
**Who to call if stuck:** [escalation contact]
**Full runbook:** [link]
```

## MCP Server Contract

### Tool: `generate_runbook`

```json
{
  "name": "generate_runbook",
  "description": "Generate incident runbook from Build Brief failure modes and SLOs",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown or relevant sections (4, 5, 6, 11)"
      },
      "confluence_page_id": {
        "type": "string",
        "description": "Confluence runbook page ID to populate"
      },
      "output_format": {
        "type": "string",
        "enum": ["confluence", "markdown", "both"],
        "default": "both"
      }
    },
    "required": ["build_brief"]
  }
}
```

### Tool: `generate_alert_configs`

```json
{
  "name": "generate_alert_configs",
  "description": "Generate alert configurations from SLO targets and failure modes",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Section 6 (SLOs) + Section 11 (Failure Modes) as markdown"
      },
      "alert_format": {
        "type": "string",
        "enum": ["prometheus", "datadog", "pagerduty", "opsgenie", "generic_yaml"],
        "default": "generic_yaml"
      },
      "output_path": {
        "type": "string",
        "description": "Where to write alert config files"
      }
    },
    "required": ["build_brief"]
  }
}
```

### Tool: `generate_oncall_briefing`

```json
{
  "name": "generate_oncall_briefing",
  "description": "Generate condensed on-call briefing for engineers unfamiliar with this feature",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown"
      },
      "format": {
        "type": "string",
        "enum": ["slack_message", "confluence_page", "markdown"],
        "default": "confluence_page"
      }
    },
    "required": ["build_brief"]
  }
}
```

## CLI Interface

```bash
# Generate runbook from build brief
adlc-runbook generate --brief ./build-brief.md --output ./runbook.md

# Generate and publish to Confluence
adlc-runbook publish --brief ./build-brief.md --page 12345

# Generate alert configs
adlc-runbook alerts --brief ./build-brief.md --format datadog --output ./alerts/

# Generate on-call briefing
adlc-runbook briefing --brief ./build-brief.md --format slack_message
```

## Quality Gates

- [ ] Every failure mode from Section 11 has a runbook section
- [ ] Every runbook step is executable (command, not description)
- [ ] Rollback procedure has exact steps and verification
- [ ] SLO targets have corresponding alert configurations
- [ ] Escalation path has named contacts at every level
- [ ] On-call briefing exists and is linked from the runbook
- [ ] TODOs for unknown commands are tagged with owner
- [ ] Confluence runbook page is populated (not just shell)

## Framework Hardening Addendum

- **Contract versioning:** Runbook generation input/output contracts include `contract_version`.
- **Schema validation:** Validate failure-mode and SLO ownership inputs against Build Brief contract requirements before generation.
- **Idempotency:** Runbook publish operations must dedupe by runbook key/version to avoid duplicate documents.
- **Stop reasons:** Emit structured terminal reasons for missing ownership data, invalid rollback contract, or publishing failures.

