---
name: fix-bug
description: "Orchestration skill for bug fixes and production issue repair. Investigate -> light brief -> targeted verification -> council -> PR."
---

# Fix Bug (Orchestration)

## Overview

Chains the fix loop for bug fixes and production issue repair. It is lighter than build-feature and uses a bug-specific verifier contract instead of universal test ceremony.

---

## When to Use

- A bug report or production error needs fixing
- A regression is confirmed in the test suite
- A failure has been reproduced and needs root-cause repair

---

## The Sequence

```text
Step 1: Investigate (systematic debugging)
Step 2: Light Brief (single task with verification_spec)
Step 3: Apply only the gates that the task class warrants
Step 4: LDD gate
Step 5: Bugfix verification discipline
Step 6: Definition of Done
Step 7: Light Council (3 personas, 1 round)
Step 8: PR with evidence
```

### Step 1: Investigate

Use `systematic-debugging` to:
- trace the failure to its origin
- check recent changes and git blame
- build a root-cause hypothesis
- identify the smallest fix scope

### Step 2: Light Brief

Create a single-task brief that includes:
- the bug description
- the observed failure
- the task classification: `bugfix`
- the `verification_spec`
- the regression expectation
- `product_vocabulary` with mappings and `banned_tokens[]`, or `none_declared`

Do not decompose into feature-style subwork unless the bug truly reveals a larger feature gap.
Write the canonical light brief outside the target repo using `bin/adlc process-artifact-path --target-repo <target-repo> --task <task-id> --artifact-type build-brief --filename build-brief.json --json`.

### Step 3: Apply Only Relevant Gates

Use the brief's applicability decision, not a universal checklist.
- Security review only if the fix changes attack surface, auth, or data handling
- Observability only if the fix changes runtime paths or user-visible behavior
- Compatibility only if the fix changes interfaces or data formats

### Step 4: LDD

Use `ldd-enforcement` before verification. Lint must pass before the bugfix verifier runs.

### Step 5: Bugfix Verification Discipline

Use the primary verifier from `verification_spec`.

Bugfix rules:
- start with the smallest deterministic reproducer
- confirm the reproducer fails for the right reason
- make the minimum code change that fixes the failure
- re-run the primary verifier until it passes
- add regression coverage if the fix changes behavior
- run any secondary verifiers from the spec

Do not force the bug through a generic RED/GREEN/REFACTOR script. The verifier itself is the contract.

### Step 6: Definition of Done

Use the DoD subset that applies to the task class and activated overlays.

### Step 7: Light Council

Use `eval-council` in light mode with three personas:
- Skeptic: root cause vs symptom
- Operator: safe to deploy, rollback plan
- Security Auditor: only when the fix touches security-relevant surfaces

### Step 8: PR

Include:
- reproduction steps
- root cause analysis
- verifier evidence
- regression guard evidence
- council verdict
- severity classification

Before publishing, run `bin/adlc pr-hygiene-scan` with the Build Brief. The PR diff and body must contain only the scoped code/docs change, not ADLC goal prompts, Build Brief drafts, local paths, council scratch artifacts, or removed target-repo gates. If the base branch is not the default branch, document the dependency explicitly.

Store verifier summaries, council output, and closeout notes in ADLC process artifact storage keyed by target repo and task. Reference those artifacts from the PR body; do not add them to the target repo commit.

---

## Escalation

If three fix attempts fail:
1. Capture what was tried
2. Record the verifiers used and why they were insufficient
3. Summarize root-cause hypotheses tested
4. Escalate with the smallest clear next step
