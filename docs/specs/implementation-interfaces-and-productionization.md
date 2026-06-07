# Implementation Interfaces And Productionization Gates

## Purpose

ADLC uses implementation-interface contracts and productionization gates to turn compound engineering intent into code-ready, production-claim-safe work.

These layers are part of the Build Brief lifecycle. They do not create a separate productionization framework, compliance program, or release workflow. They make existing ADLC stages more precise by naming what a task reuses, consumes, emits, guarantees, validates, and may claim.

## Definitions

| Term | Meaning | Not Used For |
|---|---|---|
| Implementation Interface | A task-scoped contract for the existing repo surface to extend, the data or state it consumes, what it emits, minimum fields, invariants, and integration points | Creating a parallel abstraction when an existing pattern can be extended |
| Productionization Gate | A task-scoped claim/evidence gate that names the production claim, coverage state, validation evidence, operational posture, security/privacy posture, reliability failure modes, and no-overclaim boundaries | Broad compliance readiness or ceremonial runbooks for trivial work |
| Coverage State | The allowed claim level: `unsupported`, `evidence_only`, `monitor_only`, `not_yet_ga`, `governed`, or `production_ready` | Treating partial evidence as production ready |
| No-Overclaim | Explicit statements that bound what the task does not prove, ship, support, or make production ready | Hiding unsupported claims in ticket prose |
| Validation Evidence | Deterministic tests, schemas, commands, smoke checks, runbooks, dashboards, audit evidence, or human approval records that prove the stated claim | Vague assertions such as "tested manually" without proof |

## Build Brief Binding

Build Briefs may include:

- top-level `sections.16_implementation_interfaces`
- top-level `sections.17_productionization_gates`
- task-level `implementation_interface_contract`
- task-level `productionization_gate`
- enterprise-readiness rollups through `implementation_interface_refs` and `productionization_gate_refs`

These fields are optional for backward compatibility. Existing briefs that do not make production claims continue to validate and emit normally.

## Implementation Interface Contract

An implementation-interface contract captures the smallest reusable surface a coding agent must preserve:

```json
{
  "id": "iface:example",
  "capability": "string",
  "reuse": ["existing helper, schema, CLI, workflow, or module to extend"],
  "consumes": ["input, state, config, artifact, event, or dependency"],
  "emits": ["output, state update, artifact, event, or evidence"],
  "minimum_fields": [
    { "name": "field_name", "kind": "string", "constraint": "non-empty and stable" }
  ],
  "invariants": ["idempotency, compatibility, ownership, or data-integrity rule"],
  "integration_points": ["path, command, schema, provider, or runtime boundary"],
  "validation_gates": ["test, schema, command, smoke check, or review gate"],
  "failure_semantics": ["how invalid input, missing dependency, or rollback behaves"],
  "privacy_redaction": "what must not be stored or emitted",
  "evidence_refs": ["path:line, command output, graph query, or ticket evidence"]
}
```

The planner should prefer an implementation interface when a task touches a repo boundary, schema, emitter payload, workflow state, CLI contract, external provider edge, or reusable framework surface.

## Productionization Gate

A productionization gate binds a production claim to proof:

```json
{
  "id": "prod:example",
  "claim": "This behavior is safe to treat as production ready.",
  "coverage_state": "production_ready",
  "operational_readiness": {
    "owner": "team or role",
    "rollback_path": "how to back out",
    "runbook_refs": ["docs/runbooks/example.md"],
    "dashboard_refs": ["dashboard or query"],
    "alerting_refs": ["alert or monitor"]
  },
  "security_privacy": {
    "redaction_posture": "what sensitive data is excluded or redacted",
    "audit_evidence": ["evidence ref"]
  },
  "reliability_failure_modes": ["known failure mode and mitigation"],
  "validation_evidence": ["test, schema, smoke check, or command evidence"],
  "no_overclaim": ["what this task does not prove or support"]
}
```

Readiness checks are strict only for `coverage_state: production_ready`. A production-ready claim without an implementation-interface contract, validation evidence, no-overclaim bounds, reliability failure modes, rollback/owner/runbook or observability posture, and security/privacy redaction posture is blocked as `overclaimed_production_ready`.

Lower coverage states preserve evidence without blocking normal work:

| Coverage State | Meaning |
|---|---|
| `unsupported` | The claim is explicitly not supported |
| `evidence_only` | Evidence exists, but no production support claim is made |
| `monitor_only` | Shipped behavior may be observed, but not relied on as GA |
| `not_yet_ga` | The implementation exists behind a gate, preview, or non-GA path |
| `governed` | Human, policy, or rollout approval controls the claim |
| `production_ready` | ADLC may claim production readiness only when required evidence is present |

## Lifecycle Binding

| ADLC Stage | Required Behavior |
|---|---|
| `research` | Find implementation-interface candidates, reuse paths, integration points, validation surfaces, and blocked production claims. |
| `plan` | Resolve candidates into task-level `implementation_interface_contract` and `productionization_gate` fields when the change surface warrants them. |
| `context_assembly` | Inline only task-relevant contracts so coding agents know what they consume, emit, validate, and may not overclaim. |
| `plan_review` / `eval-council` | Return `REVISION_REQUIRED` for `missing_implementation_interface_contract`, `missing_productionization_gate`, or `overclaimed_production_ready` when active surfaces warrant them. |
| `code_review` | Verify the diff preserves interface semantics and does not expand production claims beyond evidence. |
| `pr_prep` | Preserve the contracts in emitted work items and closeout evidence. |

## Removal Criteria

Keep these fields only while they reduce rereads, integration drift, or unsupported production claims. Remove or collapse them if the Build Brief, codegen context, and emitter contracts can preserve the same evidence through a smaller structure.
