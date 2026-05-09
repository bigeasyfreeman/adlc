# Work-Item Reconciliation Contract

## Purpose

Define the product-neutral ADLC contract for reconciling already-created tracker work items against a Build Brief without mixing product backlog cleanup into generic emitter skills.

## Scope

This contract applies to JIRA, GitHub Issues, Linear, and any future work-item target supported by `docs/specs/emitter-contract.md`. Product-specific audits must live in the product repo, project tracker, or an approved project-specific runbook. Generic ADLC skills must not embed a customer's ticket IDs, phase names, or backlog cleanup instructions.

## Required Sequence

1. Run a dry-run emitter payload for the Build Brief.
2. Run a read-only estate audit of the target tracker.
3. Match existing work items by durable metadata before title:
   - ADLC idempotency key
   - Build Brief ID
   - task ID
   - stored external ref
4. Produce a reconciliation report for human review.
5. Mutate the tracker only after explicit approval and only through a configured local provider.

Dry-run and audit commands are evidence. They are not permission to mutate.

## Required Checks

The report must include:

- phase/project or milestone mismatches
- missing idempotency metadata
- missing ADLC execution sections
- unresolved dependency aliases
- unresolved decision blockers
- validation tasks that were folded into implementation work instead of emitted as first-class work items
- obsolete work items that should be closed only with explicit approval

## Mutation Guardrails

- Never reconcile by fuzzy title alone.
- Never move product tickets based on a generic ADLC framework brief.
- Never encode one product's tracker conventions in `skills/linear-ticket-creation`, `skills/jira-ticket-creation`, or `skills/github-issue-creation`.
- Stop before mutation when the readiness report is blocked.
- Preserve ticket history; update in place only when idempotency metadata proves identity.

## Output Shape

```json
{
  "target": "linear",
  "build_brief_id": "BRF-123",
  "mode": "read_only",
  "totals": {
    "checked": 42,
    "phase_project_mismatches": 3,
    "missing_idempotency": 1,
    "missing_adlc_sections": 4,
    "unresolved_aliases": 2,
    "decision_blockers": 1,
    "validation_split_mismatches": 0
  },
  "proposed_mutations": []
}
```

`proposed_mutations` must stay empty until the operator approves a follow-up mutating run.
