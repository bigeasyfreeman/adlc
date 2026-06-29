# Ponytail ADLC Integration Review

Source reviewed: <https://github.com/DietrichGebert/ponytail>

Ponytail should enter ADLC as a mandatory minimality contract, not just as an
optional agent plugin. The upstream plugin is valuable as runtime context, but a
plugin alone cannot guarantee that decomposition, tickets, scoped work, and
reviews carry the constraint forward. ADLC should make Ponytail a schema-backed
forcing function.

## What Ponytail Adds

Ponytail is a pre-code decision ladder:

1. Skip work that does not need to exist.
2. Reuse what already exists in the codebase.
3. Use the standard library.
4. Use native platform features.
5. Use already-installed dependencies.
6. Prefer a one-line solution when correct.
7. Only then write the minimum code that works.

It explicitly does not permit cutting comprehension, trust-boundary validation,
data-loss handling, security, accessibility, hardware calibration, or requested
requirements. Non-trivial logic should leave one small runnable check behind.

## Integration Principle

Make Ponytail a required ADLC field and gate, not a vibe.

Every implementation or validation task should answer:

- Which Ponytail rung applies?
- What did we verify already exists?
- What are we explicitly not building?
- Did we avoid new dependencies and speculative abstractions?
- What is the smallest required check?
- If we took an intentional shortcut, what is the `ponytail:` ceiling and
  upgrade trigger?

If those answers are missing, `emit-work-items --require-ready` should block.

## Recommended ADLC Surfaces

### Build Brief Schema

Add `minimality_contract` to Build Brief tasks, required for
`implementation_task` and `validation_task`, with a compact not-applicable form
only for docs-only or decision-only work.

Suggested shape:

```json
{
  "mode": "full",
  "rung": "reuse_existing",
  "decision": "reuse scripts/adlc_runtime/cli.py validators instead of adding a new runtime",
  "reuse_evidence": ["graphify query ...", "scripts/adlc_runtime/cli.py"],
  "skipped": ["new orchestrator", "new dependency", "new abstraction"],
  "new_dependencies": [],
  "new_abstractions": [],
  "minimum_check": "bash tests/test_adlc_cli.sh",
  "safety_preserved": ["validation", "security", "data_loss", "accessibility"],
  "shortcut_comments": []
}
```

Use enums for `rung`: `skip`, `reuse_existing`, `stdlib`, `native_platform`,
`installed_dependency`, `one_liner`, `minimum_code`, `not_applicable`.

### Planner And Decomposition

The planner should be unable to emit implementation tickets without a
`minimality_contract`. Ticket wording should include a "Ponytail Contract"
section with the selected rung, local reuse refs, skipped work, dependency
policy, and minimum check.

This makes Ponytail visible before the coding agent starts, instead of relying
on a post-hoc reviewer to notice overbuild.

### Readiness Gate

`compute_readiness_report` should block:

- missing `minimality_contract`
- `new_dependencies` without explicit Type 1 approval
- `new_abstractions` without a second implementation or explicit approval
- empty `reuse_evidence` when rung is not `skip` or `not_applicable`
- missing `minimum_check` for non-trivial logic
- safety fields omitted for trust-boundary, data-loss, security, accessibility,
  money, or hardware paths

### CLI And MCP

Add a deterministic CLI/MCP surface:

- `ponytail-admit --build-brief ...`
- `ponytail-review --diff ...` or `--changed-path ...`
- `ponytail-debt --workspace ...`

`ponytail-admit` validates task contracts before work-item emission.
`ponytail-review` reports over-engineering in the current diff.
`ponytail-debt` harvests `ponytail:` comments so deliberate shortcuts do not rot.

The upstream Ponytail MCP can provide instruction text, but ADLC should still
own its local schema and readiness gate. Host context injection is not a
control plane.

### Codegen Context And Runtime

`codegen-context` should inline each task's Ponytail Contract. The coding agent
should see:

- current Ponytail mode, default `full`
- selected rung
- what to reuse
- what not to build
- dependency and abstraction constraints
- required minimum check
- safety exceptions that cannot be simplified away

For `bin/adlc run-phase code`, ADLC should prepend a Ponytail prelude to the
runtime prompt or retrieve it from the Ponytail MCP/plugin when installed. The
fallback should be local, because the policy must hold even without plugin
availability.

### Review And Eval Council

Add Ponytail checks to code review and Eval Council:

- Did the diff add a dependency where stdlib/native/local code was enough?
- Did it introduce a one-implementation abstraction?
- Did it duplicate an existing helper?
- Did it build skipped scope?
- Did it leave the smallest required check?
- Did it preserve validation, data-loss handling, security, and accessibility?

Ponytail review should be a complexity pass, not a substitute for correctness
or security review.

### Definition Of Done

Add a DoD overlay:

- `minimality_contract` present or explicitly not applicable
- selected rung honored in implementation
- no unapproved new dependency
- no unapproved speculative abstraction
- skipped scope still skipped
- minimum check run and recorded
- `ponytail:` shortcuts carry ceiling and upgrade trigger

## Proposed Implementation Slices

1. Add Ponytail policy doc and source metadata.
2. Add Build Brief `minimality_contract` schema plus fixtures.
3. Add `ponytail-admit` CLI/MCP validator and readiness integration.
4. Update planner, codegen-context, coder, code-reviewer, Eval Council, and DoD.
5. Update ticket emitters to include the Ponytail Contract.
6. Add runtime prompt prelude or Ponytail MCP/plugin fallback.
7. Add canaries and full `bin/adlc ci --json` proof.
8. Run `graphify update .`.

## Non-Goals

- Do not import Ponytail as a replacement orchestrator.
- Do not let Ponytail remove safety, validation, security, or accessibility.
- Do not rely only on agent memory or plugin context.
- Do not make "shorter diff" override task correctness.

## Bottom Line

Ponytail belongs in ADLC as a mandatory minimality admission contract carried
from decomposition to ticket text to coding context to review. The coding agent
should receive Ponytail instructions, but the real guarantee comes from ADLC
schema fields, readiness blocking, emitted ticket content, and post-diff gates.
