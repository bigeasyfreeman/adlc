# Graph Research And Comprehension Contract

## Purpose

This contract defines how ADLC uses graph-backed research, task memory, and comprehension artifacts without turning the lifecycle into prompt ceremony.

Graphify is the codebase and corpus map. Beads is the dependency-aware work graph. Context-layer artifacts are the durable human-readable comprehension record. The comprehension gate blocks changes whose system implications are not understood. Scalable AI code primitives extend this contract with construct maps, paved-road references, implementation-interface candidates, verifiability evidence, production invariant coverage, and productionization gates.

## Tool Roles

| Tool or Skill | Role | Not Used For |
|---------------|------|--------------|
| `graph-research` / Graphify | Repo topology, construct relationships, dependency paths, compatibility research, reuse discovery, validation surfaces, graph freshness, dark-code hotspots | Work-item source of truth |
| Beads (`bd`) | Ready-work selection, dependency blockers, issue relationships, durable task memory | Architecture proof or code behavior evidence |
| `paved-road-registry` | Approved repo-local build paths, reference implementations, convention gaps, and evidence for leaving a pattern | Generic best-practice enforcement |
| `dark-code-audit` | Structural and velocity dark-code risk assessment | Generic bug review |
| `context-layers` | Module manifest, behavioral contracts, decision log | Redesigning the system |
| `comprehension-gate` | Post-change understanding, blast radius, state, secrets, assumptions, explainability | Style review, linting, normal test coverage |

## Lifecycle Binding

| ADLC Stage | Required Behavior |
|------------|-------------------|
| `research` | Read or build Graphify before broad search. Record graph freshness, graph queries, construct maps, direct verification, compatibility evidence, validation surfaces, paved-road candidates, implementation-interface candidates, blocked production claims, Beads task-memory context, and dark-code hotspots. |
| `plan` | Convert graph, construct-map, paved-road, implementation-interface, and compatibility evidence into Build Brief constraints. Add context-layer artifact requirements for modules, interfaces, state, ownership, production invariants, productionization gates, and dark-code hotspots. |
| `context_assembly` | Inline only task-relevant graph evidence, construct relationships, paved-road refs, implementation-interface contracts, compatibility constraints, productionization gates, production invariants, and context artifacts into each coding prompt. |
| `code_review` | Run comprehension-gate after correctness review. Return `revise` for `HOLD`, unanswered `REVIEW REQUIRED`, missing paved-road evidence, missing implementation-interface semantics, unverifiable delegation, overclaimed production-ready states, unsupported production-quality claims, or missing medium+ blast-radius context. |
| `pr_prep` | Include graph freshness, construct-map refs, paved-road refs, implementation-interface contracts, productionization gates, context artifact paths, comprehension verdict, unresolved dark-code risk, and Beads follow-up IDs if present. |

## Graph Research Evidence

Every repo-backed ADLC run should produce:

```json
{
  "graph_status": "fresh | stale_refreshed_ast_only | stale_not_refreshed | unavailable",
  "graph_report": "graphify-out/GRAPH_REPORT.md | null",
  "graph_commit": "string | null",
  "head_commit": "string | null",
  "queries_run": [],
  "direct_verification": [],
  "construct_map": {
    "constructs": [],
    "relationships": [],
    "validation_surfaces": [],
    "blast_radius": []
  },
  "implementation_interface_candidates": [],
  "blocked_production_claims": [],
  "paved_road_refs": [],
  "accuracy_gaps": []
}
```

Graph-derived claims are not enough for Type 1 decisions. Public API, data model, auth, storage, tenancy, migration, and external integration claims need direct verification against source, schema, tests, docs, or command output.

Construct-map evidence should name the affected module, service, schema, config, persistence path, API, event, or test surface. Do not collapse construct relationships into vague "repo touched" claims.

## Paved-Road Evidence

Paved-road evidence is required when a change adds or modifies code, schema, runtime behavior, tests, or deployment conventions.

Each paved-road finding must name:
- the capability or construct being built
- the approved or preferred repo-local pattern
- the reference implementation path
- the verifier or contract that protects the pattern
- whether the task follows the pattern, leaves it with evidence, or has `no_paved_road_found`

For trivial docs, lint-only, and build-validation work, paved-road evidence may be marked `not_applicable` with a concrete reason.

## Compatibility Evidence

Compatibility evidence is required when the change surface includes an interface, integration, rollout, data format, storage, auth, runtime path, or public user operation.

Each compatibility finding must name:
- the consumer, stored artifact, config, endpoint, schema, workflow, or module affected
- the current contract
- the proposed change
- the direct evidence
- the verifier or context artifact that protects the contract

Backward compatibility protects current users and artifacts. Forward compatibility protects named future phases only. Do not create speculative abstraction for unnamed future work.

## Implementation Interface And Productionization Evidence

Graph-backed research should identify implementation-interface candidates before planning creates tasks:

- existing modules, schemas, CLIs, emitters, providers, or workflows that should be reused
- what those surfaces consume and emit today
- minimum fields or semantic constraints that downstream tasks must preserve
- integration points and validation gates
- blocked production claims where no evidence, rollback path, observability, security/privacy posture, or no-overclaim boundary exists

Graph evidence remains a starting point. Critical interface and productionization claims must be directly verified before the planner turns them into `implementation_interface_contract` or `productionization_gate` fields.

## Context-Layer Artifact Requirements

Create or update context artifacts when a change:
- adds or materially changes a module, service, public interface, schema, event, queue, persistence path, retry behavior, or ownership boundary
- touches a graph-identified dark-code hotspot
- creates behavior that a new on-call engineer could not explain from code and tests alone

Artifacts:
- `MODULE_MANIFEST.md` or `CONTEXT.md`
- behavioral contracts near the interface definitions
- `DECISIONS.md`, ADR, or existing decision log

Unknown rationale is recorded as unknown. Do not invent historical intent.

## Comprehension Gate Outcomes

| Verdict | Pipeline Result |
|---------|-----------------|
| `CLEAR` | May proceed when normal review, security, and QA gates pass |
| `REVIEW REQUIRED` | Return `revise` unless every listed question is answered with cited evidence |
| `HOLD` | Return `revise`; senior engineer review required before continuing |

Passing tests never override an unclear comprehension verdict.

## Beads Integration

ADLC ships a read-only `bin/adlc beads-status` preflight so a harness can detect
whether the optional Beads layer is usable before relying on it. It reports
`available`, `not_configured`, or `unavailable`, never runs `bd init`, `bd setup`,
or any write command, and exits cleanly when `bd` and `.beads/` are absent.

If Beads is configured:
- use `bd prime` at session start
- use `bd ready --json` for ready-work selection
- use `bd show <id> --json` before executing a task
- use dependency links for blocked, related, parent-child, duplicate, and superseding work
- use `bd remember` for durable process insights that should survive compaction

If Beads is not configured, ADLC continues with existing work-item emitters. Do not require Beads for repos that already use GitHub, Linear, Jira, or another work tracker.

## Removal Criteria

These gates are BLE/BPE compliant only if they can shrink over time.

- Keep Graphify while it materially reduces repo rereads or catches cross-file compatibility paths.
- Keep Beads while multi-agent handoff or dependency management benefits from durable task memory.
- Keep context-layer generation where code and tests do not encode structural, semantic, or philosophical context.
- Keep the comprehension gate for medium+ blast-radius changes even as models improve; remove only redundant interview ceremony when models can infer and update artifacts reliably.
