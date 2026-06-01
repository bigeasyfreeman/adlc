# Scalable AI Code Primitives

## Purpose

This contract defines the engineering primitives ADLC uses to make AI-generated code scale without lowering the production-quality bar.

The scope is code and environment consistency, not broad organization design. ADLC should help agents understand constructs, relationships, approved build paths, verifiers, and load-bearing invariants before they write code.

## Core Primitives

| Primitive | Role | Not Used For |
|---|---|---|
| Graph-backed construct map | Names the modules, interfaces, schemas, configs, persistence paths, tests, and dependency relationships relevant to the work | Replacing direct source verification |
| Intent contract | Captures behavior, why it matters, constraints, tradeoffs, non-goals, edge cases, and load-bearing assumptions before codegen | Step-by-step implementation control |
| Agent paved-road registry | Records approved repo-local patterns, reference implementations, and conventions agents should reuse | Freezing architecture or blocking justified new abstractions |
| Verifiability gate | Defines what proves the agent output is correct and when human judgment is required | Treating every task as automatable |
| Production invariant coverage | Captures identity, auth, tenancy, data integrity, ordering, retries, persistence, observability, and failsafe behavior where relevant | Generic production-readiness prose |

## Lifecycle Binding

| ADLC Stage | Required Behavior |
|---|---|
| `research` | Produce construct-map evidence, paved-road candidates, validation surfaces, and invariant gaps from Graphify plus direct source verification. |
| `plan` | Convert evidence into Build Brief constraints, task-level paved-road refs, verifiers, production invariant coverage, and compatibility/failsafe obligations. |
| `context_assembly` | Inline only task-relevant construct paths, paved-road references, intent constraints, verifiers, and invariants into coding prompts. |
| `code_review` | Block medium+ blast-radius changes when paved-road decisions, verifiability, or production invariants are missing or unsupported. |
| `pr_prep` | Preserve construct-map refs, paved-road refs, intent refs, invariant coverage, compatibility evidence, and unresolved gaps in emitted work items. |

## Graph-Backed Construct Map

A construct map should name only evidence-backed relationships that matter to the current work:

- modules, packages, services, CLIs, jobs, scripts, and generated artifacts
- public APIs, internal interfaces, schemas, events, queues, configs, and environment variables
- persistence paths, migrations, caches, and stateful resources
- imports, callers, producers, consumers, reverse dependencies, and compatibility-sensitive paths
- tests, fixtures, schemas, contract checks, smoke tests, and other validation surfaces
- existing implementations or conventions that should be reused or extended

Graphify output is a map. Claims that affect public API, data model, auth, storage, tenancy, migration, external integrations, or other Type 1 decisions still require direct verification against source, schemas, tests, docs, or command output.

## Intent Contract

Every agent-executable task should preserve enough structured intent for a cold-start agent to build without guessing:

- behavior that changes
- user or system reason for the change
- constraints and explicit non-goals
- tradeoffs or rejected alternatives when relevant
- edge cases and failure modes
- load-bearing assumptions
- verifier or human-judgment checkpoint

The intent contract should be concise. It should describe outcomes and constraints, not procedural coding steps.

## Agent Paved-Road Registry

A paved-road record is an evidence-backed build path:

```json
{
  "id": "string",
  "capability": "string",
  "status": "approved | preferred | deprecated | no_paved_road_found",
  "reference_impl": "path:line | path",
  "applies_when": ["string"],
  "do_not_reimplement": ["string"],
  "allowed_departure": "string",
  "evidence": ["path:line | command output | graph query"]
}
```

Agents should prefer paved roads. Leaving a paved road requires:

- direct evidence that the existing pattern cannot absorb the change safely
- the smallest new abstraction that solves the current problem
- a verifier or context artifact that protects the new contract
- a follow-up path for adding the new pattern to the registry if it becomes reusable

## Verifiability Gate

Before autonomous implementation, ADLC should classify verification:

| Classification | Meaning | Pipeline Result |
|---|---|---|
| deterministic | A test, schema, command, fixture, or contract check can prove the behavior | Agent can execute when other gates pass |
| bounded_judgment | Human judgment is needed but supported by concrete artifacts and checks | Agent may execute with explicit review checkpoint |
| unverifiable | No concrete verifier or review artifact exists | Return `revise` or emit a `decision_gate` |

Use the existing `verification_spec.must_be_deterministic` and verifier metadata first. Add richer schema only when the existing fields cannot preserve the needed evidence.

## Production Invariant Coverage

Production-quality claims must name concrete invariants instead of generic quality language. Relevant invariants include:

- identity and account binding
- authentication, authorization, and secret handling
- tenancy and data isolation
- money movement or financial state
- PII and sensitive data handling
- ordering, concurrency, idempotency, retries, and dedupe
- persistence, migrations, rollback, and downgrade
- dependency failure behavior and graceful degradation
- observability required to know whether the behavior works

If an invariant is relevant but not covered, the planner must either add prerequisite work, create a validation task, or record a blocker.

## Non-Goals

ADLC does not require:

- a full software-ecology map of teams, incentives, or culture
- Google-specific repository practices such as monorepo or trunk-based development
- token economics for every task
- broad productivity metrics
- heavyweight release governance for low-risk changes
- paved-road evidence for trivial docs, lint-only, or build-validation changes where no code path changes

## Removal Criteria

These primitives remain BLE/BPE compliant only if they can shrink over time:

- Remove explicit construct-map prompts when Graphify and source-aware models reliably infer and cite the same relationships.
- Remove paved-road discovery hints when models consistently reuse repo-local patterns without prompting.
- Keep verifiability and invariant gates while models remain jagged in production design choices.
- Remove duplicated fields when the Build Brief schema, context assembly, and work-item emitters can preserve the same evidence through a smaller contract.
