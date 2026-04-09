---
name: fix-bug
description: "Orchestration skill for the Fix Loop. Investigate → Brief(light) → LDD → TDD → Council(light) → PR. Use for bug fixes and production issue repair."
---

# Fix Bug (Orchestration)

## Overview

Chains the Fix Loop for bug fixes and production issue repair. Lighter than build-feature — single task, light brief, light council.

## When to Use

- Bug report or production error needs fixing
- Fix Loop detected and confirmed an error
- Regression identified in test suite

## The Sequence

```
Step 1: Investigate (systematic debugging)
Step 2: Light Brief (single task)
Step 3: STRIDE on the fix
Step 4: LDD gate
Step 5: TDD (RED: reproduce → GREEN: fix → REFACTOR)
Step 6: Definition of Done
Step 7: Light Council (3 personas, 1 round)
Step 8: PR with evidence
```

### Step 1: Investigate
- **Skill:** `systematic-debugging`
- Trace call chain from error to origin
- Check git blame and recent changes
- Build root cause hypothesis
- Identify minimal fix scope

### Step 2: Light Brief
- Single task (no full decomposition)
- G/W/T acceptance criteria focused on: bug is fixed, regression test exists, no new issues introduced
- STRIDE on the fix (does fixing this introduce new security concerns?)
- Observability: does the fix add logging for this failure mode?

### Step 3: Security Review
- **Skill:** `security-review` (STRIDE mode)
- Quick STRIDE on the fix itself
- Security fixes auto-elevate to Critical risk tier

### Step 4: LDD
- **Skill:** `ldd-enforcement`
- Lint the fix. Must pass before tests.

### Step 5: TDD
- **Skill:** `tdd-enforcement`
- **RED:** Write test that reproduces the bug (must fail without fix)
- **GREEN:** Write minimal fix to pass the test
- **REFACTOR:** Clean up
- Run full test suite for regressions

### Step 6: Definition of Done
- **Skill:** `definition-of-done`
- Subset of full DoD relevant to fixes

### Step 7: Light Council
- **Skill:** `eval-council` (LIGHT — 3 personas, 1 round)
- **Skeptic:** Root cause vs symptom?
- **Operator:** Safe to deploy? Rollback plan?
- **Security Auditor:** New security issues?

### Step 8: PR
- Reproduction steps
- Root cause analysis
- Fix explanation
- Test evidence (reproduction test + full suite)
- Council verdict
- Severity classification

## Escalation

If 3 fix attempts fail:
1. Create detailed issue with everything learned
2. Include: root cause hypotheses tested, what didn't work, suggested next steps
3. Tag with severity
4. Assign to human
