---
name: ship-content
description: "Orchestration skill for Magnus content delivery. Brief → Council → Draft → Slop Gate → Council(light) → Publish. End-to-end content creation and publishing."
---

# Ship Content (Orchestration — Magnus)

## Overview

Chains the ADLC Build Loop adapted for content operations. From content signal to published piece.

## When to Use

- Magnus needs to produce and publish content
- Content brief is ready for execution
- End-to-end content creation pipeline

## The Sequence

```
Step 1: Content Brief (structured from signal)
Step 2: Eval Council (HEAVY — content-adapted)
Step 3: Draft (content-forge with voice profile)
Step 4: Stop Slop (content mode, 35/50 gate)  ←── revision loop
Step 5: Platform Adapt (each version slop-gated)
Step 6: Eval Council (LIGHT — 2 personas, 1 round)
Step 7: Publish (Postiz CLI)
Step 8: Audit + Engagement Tracking
```

### Step 1: Content Brief
- **External Magnus dependency:** `content-brief` (Magnus domain PRD)
- Structure signal into: topic, angle, ICP target, platform, voice constraints, format, anti-slop rules
- Reject ambiguous briefs (no clear ICP, no clear angle)

### Step 2: Eval Council — Full
- **Skill:** `eval-council` (HEAVY — 6 content-adapted personas)
- Architect: Content strategy alignment
- Skeptic: Brand damage risk
- Operator: Platform publishability
- Executioner: Can the agent produce this?
- Security Auditor: PII/reputation risk
- First Principles: Does this serve the ICP?

### Step 3: Draft
- **External Magnus dependency:** `content-forge`
- Voice profile loaded (`eric-voice-profile.md`)
- Draft against brief constraints
- STRIDE brand risk awareness during drafting

### Step 4: Stop Slop Gate
- **Skill:** `stop-slop` (content mode)
- 5-dimension scoring: Directness, Rhythm, Trust, Authenticity, Density
- Threshold: 35/50 (38/50 for outreach)
- If fail: revise with specific feedback on which dimensions failed
- Max 3 revision attempts, then escalate

### Step 5: Platform Adapt
- **External Magnus dependency:** `content-adapt`
- Generate platform-native versions (LinkedIn, X, email, etc.)
- EACH version individually slop-gated (35/50)
- Platform constraints enforced (character limits, format rules)

### Step 6: Eval Council — Light
- **Skill:** `eval-council` (LIGHT — 2 personas, 1 round)
- Skeptic: Any brand risk in final versions?
- Operator: Ready to publish across all target platforms?

### Step 7: Publish
- **External Magnus dependency:** `content-publish`
- Publish via Postiz CLI
- Capture: platform, URL, timestamp, content_id

### Step 8: Audit + Tracking
- Pipeline audit log: full trace from brief to publish
- Engagement tracking initiated (link to pipeline_run_id)
- Feedback capture: when Eric edits, diff is recorded for voice profile refinement
