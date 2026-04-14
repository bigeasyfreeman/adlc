---
name: section-policy-judge
description: Override deterministic section suppression when manifest evidence shows the section should stay active.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 700
    expected_calls_per_run: 2
---

# Section Policy Judge

Run this after deterministic section-policy evaluation and only for sections currently suppressed or marked not applicable.

## Inputs

- task classification
- change-surface flags
- claim provenance
- current `section_policy` entries
- candidate suppressed sections and their deterministic reasons

## Output

```json
{
  "overrides": [
    {
      "section_name": "5_security_review",
      "status": "active",
      "reason": "Docs task changes credential-handling guidance and needs explicit security review.",
      "evidence": ["claim provenance: auth guidance edit"],
      "overridden_by": "section_policy_judge"
    }
  ]
}
```

## Rules

- Override sparingly. Deterministic policy remains the default.
- Every override must cite manifest evidence, not generic caution.
- Do not suppress an already active section.
