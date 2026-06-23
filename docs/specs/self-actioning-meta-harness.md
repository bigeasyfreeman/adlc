# Self-Actioning Meta-Harness

The self-actioning meta-harness makes ADLC consumable by an LLM or external harness as a bounded control plane without skipping the framework's admission, queue, verifier, memory, and human-approval gates.

The shipped scope is `meta-harness-plan`: a deterministic planner that reads repo, ticket, or signal candidates, ranks them by value, risk, verifiability, repeatability, and urgency, chooses a packaged loop template, emits queue and tracker-sync seed artifacts, and stops before mutation.

## Boundary

`meta-harness-plan` does not:

- dispatch agents
- claim queue tasks
- create worktrees
- create or update external tickets
- merge code
- deploy code
- make architecture decisions

Those actions remain behind the existing commands: `loop-template-install`, `sync-work-item`, `queue-claim`, `worktree-prepare`, `run-phase`, `queue-complete`, `queue-escalate`, `architecture-memory`, and `action-admit`.

## Inputs

The planner can read any combination of:

- `--signals <path>`: JSON object or array containing `signals`, `candidates`, `items`, or `tasks`.
- `--build-brief <path>`: schema-valid Build Brief task tickets.
- `--queue <path>`: schema-valid ADLC Work Queue candidates that are queued, released, or blocked.
- `--catalog <path>`: packaged loop catalog, defaulting to `docs/loop-library/catalog.json`.

Signals can include `title`, `summary`, `labels`, `expected_paths`, `verifier_refs`, `value_score`, `risk_score`, `verifiability_score`, `repeatability_score`, `urgency_score`, `template_id`, `suggested_template_id`, or `work_item_external_id`.

## Output

The command emits and validates a `meta-harness-plan-report`:

```bash
bin/adlc meta-harness-plan \
  --signals .adlc/signals.json \
  --build-brief .adlc/build_brief.json \
  --max-candidates 3 \
  --json
```

The report contains:

- ranked candidate decisions
- selected loop template ids
- blockers that require human review
- generated Work Queue seed payload
- generated Work Item Sync payloads
- planned ADLC commands for install, sync, claim, worktree preparation, verifier execution, and human review
- explicit boundary claims and human approval points

## Admission Rules

A candidate can be admitted to queue only when:

- an automated verifier is present
- risk is below the high-risk threshold
- expected return clears the score floor

Missing verifier evidence, high-risk domains, architecture-sensitive work, merge/deploy decisions, auth, payments, secrets, production mutation, or irreversible side effects force `needs_human`.

## Harness Contract

A consuming harness should:

1. Run `meta-harness-plan`.
2. Inspect `selected[]`, `planned_actions[]`, and `generated_artifacts.validation[]`.
3. Write generated artifacts into `.adlc/meta_harness/` if acceptable.
4. Run the planned ADLC commands in order.
5. Require `action-admit` and human approval before any mutation.
6. Stop at human review before merge, deploy, architecture decisions, or irreversible side effects.

The meta-harness therefore gives ADLC task selection and execution planning, while preserving the earlier control-plane constraints.
