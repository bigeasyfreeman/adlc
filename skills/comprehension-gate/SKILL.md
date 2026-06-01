---
name: comprehension-gate
description: "Reviews code changes for understanding, blast radius, state, secrets, assumptions, and explainability. Produces a blocking comprehension artifact when implications are unclear."
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: core_plus_overlays
  consumes_manifest: true
  produces:
    - comprehension_artifact
---

# Comprehension Gate

## Purpose

The comprehension gate reviews a change for system understanding. It does not replace correctness review, security review, linting, or tests. It answers: did someone understand what this change does, what it affects, and what assumptions it makes before it ships?

## Standalone Mode

Ask:

"Paste the diff, PR description, or code change you want reviewed. Include as much as you have. Optional but strongly recommended: also paste any system context such as a module manifest, behavioral contracts, or dependency map."

If the user provides only a description, work with it and note where the actual diff would enable more specific analysis.

## ADLC Embedded Mode

Run during `code_review` after normal task correctness checks and before security review.

Inputs:
- diff or changed files
- Build Brief task and verification spec
- graph research evidence
- context-layer artifacts when available
- module manifest, behavioral contracts, and decision log references
- test and QA output

If blast radius cannot be assessed because context artifacts are missing, return `review_required` with the missing artifact named.

## Review Dimensions

### 1. Credential And Secret Exposure

- Are any values used as credentials, API keys, tokens, or secrets?
- Are they hardcoded, logged, stored, or passed in leaky ways?
- Read contextually. A variable named `config_value` is a credential if it authenticates a request.

### 2. Cross-Service Side Effects

- Does the change write to a shared database, cache, queue, filesystem, or external system?
- Could another service read what this change writes?
- Does it create a data flow that did not exist before?
- Could independently correct services combine into cross-tenant exposure?

### 3. Blast Radius

- If the change fails, what else breaks?
- What calls this code?
- What reads the data it produces?
- What assumes the state it modifies?
- Is the failure graceful or catastrophic?

### 4. State And Persistence

- Does the change create, modify, or delete persistent state?
- Is there a mismatch between apparent scope and actual production-state impact?
- Does it treat infrastructure or environment as ephemeral when it is persistent?

### 5. Token And Session Management

- Are tokens, sessions, temporary credentials, or agent-created access paths created or changed?
- Do they have TTLs?
- Who cleans them up if an automated process dies?

### 6. Implicit Assumptions

- What does the code assume about ordering, timing, concurrency, availability, tenancy, or data shape?
- Are those assumptions documented?
- Would behavior change under load, partial outage, retries, or slow dependencies?

### 7. Comprehension Check

- Could the shipper explain the change to a non-technical stakeholder?
- Could on-call understand it at 3 AM?
- Does understanding require context that is not captured anywhere?

## Output

Produce a Comprehension Artifact:

### Change Summary

2-3 sentences stating what the code actually does. If stated intent and behavior diverge, flag it.

### Findings Table

Table columns:

`Finding | Severity (Critical / Warning / Note) | Category | Details`

List every finding ordered by severity. Be concrete.

### Blast Radius Map

For medium+ blast radius changes, include a forward trace of what could be affected.

### Questions Before Merging

Numbered direct questions that need answers before shipping.

### Comprehension Verdict

- **CLEAR** - intent matches behavior; blast radius is bounded and understood.
- **REVIEW REQUIRED** - concrete questions need answers first.
- **HOLD** - system-level implications appear misunderstood; do not ship without senior review.

## Guardrails

- Analyze only provided or directly verified context.
- Distinguish confirmed findings from risks needing investigation.
- Never say "looks good" by default.
- Do not review style, naming, or normal test coverage.
- If the change appears AI-generated and lacks reasoning for non-obvious choices, note it as relevant context.

