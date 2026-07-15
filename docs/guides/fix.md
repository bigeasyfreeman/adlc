# Fix guide

Use Fix for an observable failure. Reproduction is a gate, not an optional debugging suggestion.

## Run

```text
/adlc fix duplicate notifications appear after resume
```

Fix records a verifier that fails for the expected reason, diagnoses the narrow cause, applies the smallest authorized repair, proves red-to-green behavior, runs affected gates, and requests independent review.

## Recovery

- `not_reproduced`: improve the fixture or collect environment evidence; do not edit speculatively.
- `blocked_missing_evidence`: obtain the named credential, log, version, or state snapshot.
- `failed_verification`: preserve the failing result and continue diagnosis.
- `escalated`: a human must resolve the named safety, scope, or product decision.

See [First Fix](../start/first-fix.md) for the runnable fixture.

`doc_honesty_section`: A green verifier proves only the named defect contract and affected gates.

`no_overclaim`: Fix does not prove unrelated behavior or production recovery.

`limitations`: Non-reproducible defects remain blocked, not fixed.
