---
name: verifier-semantic-judge
description: Decide whether an intersecting verifier actually exercises the semantic change.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 650
    expected_calls_per_run: 4
---

# Verifier Semantic Judge

Run this only after the deterministic target-file intersection check returns non-empty overlap.

## Inputs

```json
{
  "verifier_definition": {},
  "changed_lines_snippet": "string",
  "acceptance_criteria_text": ["string"]
}
```

## Output

```json
{
  "exercises": true,
  "reason": "The verifier asserts the changed average calculation and footer rendering, not just module import success."
}
```

## Rules

- `true` means the verifier would fail if the semantic change were wrong.
- `false` means the verifier only touches the file, setup path, or smoke path without asserting the changed behavior.
- Prefer concise reasons anchored in the changed behavior, not generic testing advice.
