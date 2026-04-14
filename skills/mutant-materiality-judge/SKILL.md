---
name: mutant-materiality-judge
description: Classify surviving mutants as trivial or material after deterministic mutation measurement.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: deep_judge
  cost_guard:
    max_tokens_per_call: 1400
    expected_calls_per_run: 3
---

# Mutant Materiality Judge

Run this only when mutation tooling reports surviving mutants.

## Inputs

- surviving-mutant diffs batched by file or behavior
- target acceptance criteria
- changed-file context
- measured coverage and kill-rate summary

## Output

```json
{
  "batch": [
    {
      "mutant_id": "M-12",
      "classification": "material",
      "rationale": "The mutant changes duplicate-invoice behavior without any test failing."
    }
  ]
}
```

## Rules

- `material` means the mutant could hide a real regression or missing assertion.
- `trivial` means the survivor is noise: equivalent behavior, logging-only drift, or unreachable semantics that the verifier contract intentionally ignores.
- Any material survivor forces the overall test-strength verdict to `weak`, regardless of aggregate kill rate.
- Judge batches, not the entire run at once, to stay within the cost guard.
