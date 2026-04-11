---
name: build-feature
description: "Orchestration skill: chains the full ADLC Build Loop. PRD → Brief → Council → Scaffold → Codegen → LDD → TDD → Council → PR. Use when implementing a new feature end-to-end."
---

# Build Feature (Orchestration)

## Overview

This orchestration skill chains core ADLC skills into the complete Build Loop sequence. It teaches the agent WHEN to use each skill and HOW they connect.

## When to Use

- User wants to implement a new feature end-to-end
- A structured PRD or issue needs to become shipped code
- Any work that goes through the full ADLC pipeline

## The Sequence

```
Step 1: PRD (fork — interactive)
Step 2: Build Brief
Step 3: Eval Council (HEAVY)  ←── revision loop (max 3)
Step 4: Scaffold (if needed)
Step 5: Codegen Context Assembly
Step 6: Per-task execution (parallel where independent):
  6a: LDD gate
  6b: TDD (RED → GREEN → REFACTOR)
  6c: Implementation
Step 7: Definition of Done verification
Step 8: Eval Council (HEAVY — post-execution)  ←── revision loop (max 3)
Step 9: Stop Slop on PR description
Step 10: Create PR
```

### Step 1: PRD Agent
- **Skill:** `prd-generation`
- **Mode:** Interactive (fork — user participates)
- **Input:** Raw feature request, issue, or idea
- **Output:** Structured PRD with: problem statement, success metrics, out of scope, constraints/antipatterns, dependencies, personas
- **Gate:** PRD must have no ambiguous language. All sections populated.

### Step 2: Build Brief
- **Skill:** `build-brief` (ADLC Build Brief Agent)
- **Input:** Structured PRD + codebase context
- **Output:** Technical design with per-task: acceptance criteria (G/W/T), STRIDE threat model, observability contract, reuse analysis, antipatterns, Definition of Done
- **Includes:** `security-review` (STRIDE mode), `observability-contract`, `reuse-analysis`

### Step 3: Eval Council — Post-Brief
- **Skill:** `eval-council` (HEAVY — 6 personas, 3 rounds)
- **Personas:** Architect, Skeptic, Operator, Executioner, Security Auditor, First Principles
- **Pre-check:** Static checks must pass before council tokens are spent
- **Verdicts:** APPROVED → Step 4. REVISION REQUIRED → back to Step 2 (max 3 loops). BLOCKED → escalate.

### Step 4: Architecture Scaffolding
- **Skill:** `architecture-pattern` (only when new modules/interfaces needed)
- **Output:** Port interfaces, implementation targets, domain types, wiring/registration, directory structure, implementation guide

### Step 5: Codegen Context Assembly
- **Skill:** `codegen-context`
- **Output:** Per-task self-contained prompt with: mission, G/W/T, tests, files (inlined), reference implementations, reusable functions, schema, "What NOT to Do", security contract, observability contract, lint config, scale considerations, integration wiring, anti-slop rules, verification commands, DoD checklist
- **Parallel dispatch:** Independent tasks get separate prompts for simultaneous execution

### Step 6: Execution (per task)
- **6a — LDD:** `ldd-enforcement` — lint gate. Must pass before TDD.
- **6b — TDD:** `tdd-enforcement` — RED (failing test from G/W/T) → GREEN (minimal code to pass) → REFACTOR. Iron law: no code without failing test first.
- **6c — Implementation:** Agent builds per codegen context. Includes security tests (from STRIDE) and observability tests (from contract).

### Step 7: Definition of Done
- **Skill:** `definition-of-done`
- **All 22 checks must pass.** Failed checks block pipeline.

### Step 8: Eval Council — Post-Execution
- **Skill:** `eval-council` (HEAVY — reviewing implementation against brief)
- **Focus:** Did the implementation match the design? Are STRIDE mitigations present? Is observability complete?
- **Verdicts:** APPROVED → Step 9. REVISION REQUIRED → back to Step 6 (max 3 loops).

### Step 9: Stop Slop
- **Skill:** `stop-slop` (content mode on PR description)
- **Threshold:** 35/50

### Step 10: Create PR
- **Output:** PR with: summary, STRIDE summary, observability additions, DoD checklist, council verdict, test results, risk tier
- **Merge policy:** Routine=auto-merge, Elevated=human review, Critical=human sign-off

## Failure Handling

| Failure | Response |
|---------|---------|
| PRD ambiguous after 5 turns | Escalate to human |
| Brief fails council 3 times | Escalate with council feedback |
| Execution fails DoD | Revision loop (max 3), then escalate |
| Post-execution council rejects 3 times | Escalate with full context |
