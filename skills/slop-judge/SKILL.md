---
name: slop-judge
description: Score generated prose or product output that cleared deterministic checks against a rubric threshold.
contract_version: 2.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 750
    expected_calls_per_run: 3
---

# Slop Judge

Use this only after stop-slop regex and pattern checks do not hard-fail.

The judge exists to close the output-side quality loop. It is not a prompt
rewriter. It scores the produced output against a concrete rubric and returns a
numeric result that a gate can compare to a threshold.

## Inputs

```json
{
  "mode": "general | outreach | product_output | agent_output",
  "regex_screen": "pass",
  "content": "string",
  "audience": "internal | external",
  "rubric": [
    "Concrete criterion such as specificity, actionability, schema validity, policy fit, or non-hallucination"
  ],
  "threshold": 0.7,
  "baseline_score": 0.82,
  "regression_tolerance": 0.03
}
```

## Output

```json
{
  "verdict": "pass | revise",
  "score": 0.0,
  "threshold": 0.7,
  "criterion_scores": [
    {
      "criterion": "string",
      "score": 0.0,
      "reason": "string"
    }
  ],
  "regression_delta": 0.0,
  "rationale": "string",
  "signals": ["generic_filler", "passive_evasion", "tautology"],
  "new_eval_case_candidate": {
    "source": "council_rejection | human_edit | runtime_failure | production_sample | other",
    "input": "optional string",
    "bad_output": "string",
    "expected_quality": "string",
    "metric": "rubric_score",
    "threshold": 0.7
  }
}
```

## Rules

- `pass` means `score >= threshold` and any baseline regression is within `regression_tolerance`.
- `revise` means the output scored below threshold, regressed beyond tolerance, or remains padded, evasive, generic, structurally invalid, or self-referential even though deterministic checks did not catch it.
- Score each rubric criterion from 0 to 1. The top-level `score` is the average unless the input names a stricter metric.
- If the output fails because the benchmark is missing, return `revise` with `signals: ["missing_benchmark"]`.
- When revising, include `new_eval_case_candidate` so `feedback-loop` can promote the failure into the saved suite after approval.
- Limit signals to observed issues. Do not invent brand guidance that is not in the source skill.
