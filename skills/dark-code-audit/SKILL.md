---
name: dark-code-audit
description: "Assesses structural and velocity dark-code risk from architecture, AI tool usage, ownership, and deployment practices. Produces a direct risk assessment without inventing missing facts."
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: overlay
  consumes_manifest: true
  trigger_fields:
    - service_boundary_change
    - external_integration
    - persistent_storage
    - runtime_path_change
    - auth_change
  produces:
    - dark_code_risk_assessment
---

# Dark Code Audit

## Purpose

Dark code is code or runtime behavior that no human understood at any point in its lifecycle. ADLC uses this audit when a request has systemic risk: multi-service behavior, non-engineer workflow creation, high AI-generated code volume, ownership gaps, or production data paths that cannot be explained.

This is not a bug hunt. It is a comprehension risk assessment.

## Standalone Interview Mode

When the user asks for a dark-code audit directly, gather context one group at a time. Wait for an answer before moving to the next group.

### Group 1 - System Architecture

Ask:

"Describe your system architecture. You can paste a repo structure, a list of services/modules, or describe it in plain language. I need to understand: what are the major components, how do they communicate, and where does data flow between them?"

### Group 2 - AI Tool Usage

Ask:

"How does your team use AI coding tools? Specifically:
- Which tools?
- What percentage of new code is AI-generated?
- Are there mandates or targets for AI tool usage?
- Do AI agents have autonomous access such as CI/CD, production, data pipelines, or runtime tool selection?"

### Group 3 - Team And Ownership

Ask:

"How is ownership structured?
- How many engineers, and what's the seniority distribution?
- Has headcount changed significantly in the past 12 months?
- Is there a clear mapping of team to service?
- Are there services or workflows that no specific team owns?"

### Group 4 - Development And Deployment

Ask:

"Walk me through how code gets to production:
- What does review look like for AI-generated code vs. human-written code?
- What automated checks exist?
- Can non-engineers connect tools, create workflows, or wire agents to production data?
- Have there been incidents or near-misses in the past 6 months where the root cause was hard to trace?"

## ADLC Embedded Mode

When this skill runs inside ADLC, do not stop the pipeline for a full interview unless a required fact is missing and the risk is elevated. Use these inputs first:

- PRD
- repo map
- graph research evidence
- Build Brief change surface
- owner/on-call data from docs if available
- prior incident/runbook references if provided

If team or AI-usage data is missing, mark it as `insufficient data to assess`. Do not invent it.

## Analysis Dimensions

### Structural Dark Code

Look for emergent behavior nobody designed:
- agent-assembled runtime paths
- cross-service data flows without explicit schemas
- non-engineer workflows touching production data
- tool chains where behavior emerges from agent choices
- services that interact in ways no team explicitly wired together

### Velocity Dark Code

Look for authored code nobody understood:
- high AI-generation ratio without proportional review depth
- reduced senior engineering capacity relative to code volume
- AI-generated code that passes checks but was never held in anyone's head
- fast-shipping teams with no spec or design-doc requirement
- services modified frequently by AI with no comprehension artifacts

### Compounding Factors

- ownership gaps
- lost institutional knowledge
- observability mistaken for comprehension
- regulatory exposure from unexplainable data processing

## Output

Produce a Dark Code Risk Assessment:

1. **Executive Summary** - 3-4 sentences with overall risk level: Critical, High, Moderate, or Low.
2. **Dark Code Hotspot Map** - table with Component/Area, Dark Code Type, Severity, Owner, Key Risk Description.
3. **Highest-Risk Scenarios** - top 3 concrete failure scenarios, diagnosis difficulty, blast radius, and whether the behavior could be explained to a regulator or customer.
4. **Ownership Gaps** - unowned behaviors, workflows, or data flows, who likely created them if known, and why they fell through the ownership model.
5. **Comprehension Debt Scorecard** - spec coverage, context coverage, review depth, and explainability.
6. **Prioritized Action Plan** - ordered actions with hotspot addressed, expected effort, and one-time vs ongoing practice.

## Guardrails

- Only assess based on provided or directly verified information.
- If data is limited, say `insufficient data to assess`.
- Distinguish confirmed facts from risks that need investigation.
- Be direct. Critical means critical.
- Do not recommend "add more monitoring" or "add a supervisory layer" as a primary fix. Recommend comprehension infrastructure: specs, context layers, comprehension gates, ownership assignments, and explicit contracts.

