---
name: specificity-judge
description: Score whether each task is specific enough for autonomous execution.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 900
    expected_calls_per_run: 4
---

# Specificity Judge

Run this at Eval Council Gate 0 after schema validation succeeds.

## Inputs

For each task provide:

- acceptance criteria list
- `reference_impl`
- `files_to_modify`
- verifier target from `verification_spec.primary_verifier`

## Output

```json
{
  "task_id": "TASK-001",
  "score": 0.74,
  "rationale": "The task names files and a verifier, but the acceptance criteria still leave error handling implicit.",
  "failing_signals": ["missing_negative_case", "ambiguous_user_path"]
}
```

## Thresholds

- `score >= 0.8` -> pass
- `0.6 <= score < 0.8` -> warn
- `score < 0.6` -> revise with `low_specificity`

## Rules

- Specificity means a cold-start coding agent can execute without guessing.
- Penalize missing file scope, vague acceptance criteria, absent reference paths, and verifier targets that do not pin the intended behavior.
- Do not count checklist items mechanically. Judge whether the task is executable.
- If `fast_judge` is unavailable for the active runtime, emit `stuck` with reason `specificity_judge_unavailable`.
