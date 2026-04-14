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

Use this judge only when `0.6 <= task_classification_confidence < 0.8`.

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
  "contamination": {},
  "missing": ["..."]
}
```

## Output

```json
{
  "verdict": "proceed | escalate",
  "rationale": "string"
}
```

## Rules

- Judge clarity, not implementation detail.
- Prefer `proceed` when the task has a concrete objective, bounded scope, and a plausible verifier path.
- Return `escalate` when the task is internally contradictory, underspecified, or missing the information needed to classify safely.
- Do not rewrite or invent the evidence inventory. Consume the deterministic feature summary as given.
