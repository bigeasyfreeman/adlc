---
name: learning-capture
description: "Conditionally captures verified reusable ADLC learnings into docs/solutions after successful closeout."
contract_version: 1.0.0
side_effect_profile: mutating
activation:
  mode: conditional_closeout
  consumes_manifest: true
  trigger_nodes:
    - pr_prep
    - learning_capture
  produces:
    - learning_candidates
    - learning_entry
---

# Learning Capture

## Purpose

Capture only reusable, verified learnings that make future ADLC runs cheaper or safer. This is a closeout path, not a planning replacement and not a default documentation chore.

## Trigger

Run after `pr_prep` when the PR package includes `learning_candidates`.

Skip when:

- the work was mechanical, lint-only, or one-off
- tests did not pass
- the candidate lacks source evidence or verifier evidence
- the content may include secrets, private tokens, credentials, or unsupported environment claims
- the candidate duplicates an existing `docs/solutions` entry without adding new evidence

## Process

1. Read only the candidate, the cited source evidence, and the nearest relevant existing `docs/solutions` entries.
2. Choose `create`, `update`, or `skip`.
3. Write one compact markdown entry using `docs/solutions/_template.md`.
4. Include `source_evidence`, `verifier`, `redaction_review`, and `stale_conditions`.
5. Run `python3 scripts/validate_learning_entry.py <entry>`.
6. Emit `pass` only when validation passes; emit `skipped` when there is no reusable verified learning.

## Output

```json
{
  "label": "pass | skipped | fail",
  "learning_capture": {
    "action": "create | update | skip",
    "path": "docs/solutions/slug.md | null",
    "reason": "string",
    "verifier": "python3 scripts/validate_learning_entry.py docs/solutions/slug.md",
    "redaction_status": "passed | needs_review"
  }
}
```

## Rules

- Do not capture secrets or raw local credentials.
- Do not capture unsupported architecture claims.
- Do not paste entire session transcripts.
- Do not create broad refresh work; emit stale conditions for `learning-refresh`.
- A learning entry is prior art, not proof. Future agents must still verify current behavior.
