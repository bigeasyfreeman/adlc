---
name: brief-clarity-judge
description: Resolve ambiguous triage outcomes in the middle confidence band.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 700
    expected_calls_per_run: 1
---

# Brief Clarity Judge

Use this judge when `0.6 <= task_classification_confidence < 0.8`, when `epistemic_ledger` contains architecture-affecting UNKNOWN entries, or when `bin/adlc clarity-gate` emits pending questions.

## Purpose

The confidence band is advisory. This judge decides whether the brief is clear enough to continue or should escalate for human clarification.

## Inputs

```json
{
  "request": "string",
  "signal_features": {
    "language_hints": ["py"],
    "intent_keywords": ["fix", "bug"],
    "linked_refs": ["PR-123"],
    "reproducer_present": true
  },
  "task_classification": "bugfix",
  "task_classification_confidence": 0.72,
  "classification_evidence": ["..."],
  "epistemic_ledger": {},
  "pending_questions": [],
  "contamination": {},
  "missing": ["..."]
}
```

## Output

```json
{
  "verdict": "proceed | escalate",
  "rationale": "string",
  "pending_questions": [
    {
      "ledger_entry_id": "L-1",
      "question": "string",
      "why_it_matters": "string",
      "what_changes": "string",
      "conservative_default": "string"
    }
  ]
}
```

## Rules

- Judge clarity, not implementation detail.
- Prefer `proceed` when the task has a concrete objective, bounded scope, and a plausible verifier path.
- Return `escalate` when the task is internally contradictory, underspecified, or missing the information needed to classify safely.
- Return `escalate` when an `ask-user` ledger entry lacks a recorded human answer or when pending questions would change architecture, compatibility, or task boundaries.
- Do not convert an `ask-user` unknown into an assumption; only a human answer or signed accepted risk resolves it.
- Do not rewrite or invent the evidence inventory. Consume the deterministic feature summary as given.
