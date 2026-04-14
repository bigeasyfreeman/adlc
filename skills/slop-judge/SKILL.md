---
name: slop-judge
description: Judge whether prose that cleared regex still contains generic filler, passive evasion, or tautology.
contract_version: 1.0.0
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

## Inputs

```json
{
  "mode": "general | outreach",
  "regex_screen": "pass",
  "content": "string",
  "audience": "internal | external"
}
```

## Output

```json
{
  "verdict": "pass | revise",
  "rationale": "string",
  "signals": ["generic_filler", "passive_evasion", "tautology"]
}
```

## Rules

- `pass` means the prose is concrete enough after the deterministic filter.
- `revise` means the prose still sounds padded, evasive, or self-referential even though regex did not catch it.
- Limit signals to observed issues. Do not invent brand guidance that is not in the source skill.
