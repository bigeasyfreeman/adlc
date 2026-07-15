# Resume guide

Resume continues persisted work without intentionally replaying completed effects.

## Inspect first

```bash
bin/adlc status --workspace /path/to/repo --json
```

`status` is read-only. It reports the current phase, terminal or blocked state, approvals, evidence, completed effects, and next action.

## Resume

```bash
bin/adlc resume --workspace /path/to/repo --json
bin/adlc resume --workspace /path/to/repo \
  --approve intent_validation \
  --reason "Resume the bounded task." \
  --json
```

Approval is scoped to the named gate. Completed side effects retain idempotency keys; the orchestrator must refuse or escalate a proposed duplicate rather than hiding it.

Stop when state is corrupt, the target commit changed incompatibly, an approval is missing, or the next effect exceeds the original authority boundary.

`doc_honesty_section`: Persisted state and idempotency evidence enable replay checks.

`no_overclaim`: Resume does not guarantee an external provider or service honors idempotency.

`limitations`: Recovery from state outside ADLC requires independent external evidence.
