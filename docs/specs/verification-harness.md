# Verification Harness Spec

## Goal
Validate ADLC infrastructure invariants with deterministic checks (not prompt quality judgment).

## Invariant Categories
- Permission enforcement
- Gate enforcement
- Budget enforcement
- Idempotency and recovery
- Scope immutability
- Phase boundary enforcement

## Test Harness Requirements
1. Mock LLM responses with fixed fixtures.
2. Mock skill endpoints with deterministic success/failure modes.
3. Validate schema boundaries before and after every step.
4. Produce machine-readable pass/fail summary.

## Execution Triggers
- Any change under `agents/`, `skills/`, or `docs/schemas/`.
- Any contract version bump.
- Any runtime change to tool registry or permission policy.

## Output Contract
```json
{
  "run_id": "VH-2026-04-06-01",
  "passed": 42,
  "failed": 0,
  "categories": {"idempotency": "pass", "budget": "pass"},
  "blocking": false
}
```
