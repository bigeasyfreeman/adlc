# First Fix loop

Use Fix when you have an observable defect and can name the affected target.

## Ask the agent

```text
/adlc fix the failing average calculation. Reproduce it first, make the smallest repair, run the affected tests, and stop with PR-ready evidence.
```

## Expected sequence

1. Capture the failure and authority boundary.
2. Run or create a verifier that fails for the expected reason.
3. Diagnose the narrow cause.
4. Make the smallest authorized repair.
5. Prove the verifier turns green and run affected gates.
6. Obtain independent review and package the evidence.

Expected terminal states are `pr_ready`, `not_reproduced`, `blocked_missing_evidence`, `failed_verification`, or `escalated`. A blocked state is an honest result; do not convert it into success.

## Replay the fixture

From the ADLC checkout:

```bash
bash tests/acceptance/run_readme_quickstart.sh
```

The script creates an isolated repository, installs the Codex-shaped ADLC bundle, routes a Fix request through `public-operation`, records a red verifier, exercises interruption/resume idempotency, applies a bounded repair, records green proof, and runs an independent deterministic completion audit.

## What you receive

- red and green verifier evidence;
- causal diagnosis and scoped diff;
- affected-suite result;
- persisted state and approval records when used;
- independent audit result;
- a clear terminal state.

`doc_honesty_section`: The fixture proves the deterministic public Fix contract on its temporary repository.

`no_overclaim`: It does not invoke Codex, prove a live provider, merge a PR, or establish production recovery.

`limitations`: Real defects can remain blocked when they cannot be reproduced or require unavailable credentials or environments.
