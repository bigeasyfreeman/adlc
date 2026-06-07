---
name: paved-road-registry
description: "Discovers and records repo-local approved build paths so agents reuse proven patterns instead of inventing parallel architectures."
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: core
  consumes_manifest: true
  produces:
    - paved_road_candidates
    - paved_road_refs
    - paved_road_gaps
---

# Paved Road Registry

## Purpose

AI-generated code scales when agents build with the repo's proven patterns. This skill discovers those patterns, names where they apply, and records when no paved road exists.

Use this skill to keep monoliths and large codebases consistent as agent throughput increases. It complements `reuse-analysis`: reuse analysis finds concrete things not to reimplement; paved-road registry captures the broader build contract agents should follow.

## Inputs

- PRD or task description
- Graphify evidence and construct-map output when available
- Repo map or codebase research deliverable
- Existing architecture docs, ADRs, manifests, schemas, fixtures, tests, and reference implementations

## Discovery Process

1. Read Graphify evidence before broad raw-source search when available.
2. Identify the capability being built: API, CLI, schema, auth, storage, UI, background job, deployment, test, or integration.
3. Find existing examples and conventions for that capability.
4. Verify candidates against source files, schemas, tests, docs, or command output.
5. Record whether each candidate is `approved`, `preferred`, `deprecated`, or `no_paved_road_found`.
6. Record when a new abstraction is justified and what would make it a future paved road.
7. When an active surface needs `implementation_interface_contract`, map the paved road into the contract's reuse, integration points, invariants, and validation gates.

## Registry Record

```json
{
  "id": "string",
  "capability": "string",
  "status": "approved | preferred | deprecated | no_paved_road_found",
  "reference_impl": "path:line | path | null",
  "applies_when": ["string"],
  "do_not_reimplement": ["string"],
  "required_invariants": ["string"],
  "verifiers": ["path | command | schema | fixture"],
  "allowed_departure": "string",
  "evidence": ["path:line | command output | graph query"]
}
```

## Output Contract

```json
{
  "paved_road_candidates": [
    {
      "id": "string",
      "capability": "string",
      "status": "approved | preferred | deprecated | no_paved_road_found",
      "reference_impl": "string | null",
      "applies_when": [],
      "do_not_reimplement": [],
      "required_invariants": [],
      "verifiers": [],
      "allowed_departure": "string",
      "evidence": []
    }
  ],
  "paved_road_gaps": [
    {
      "capability": "string",
      "gap": "string",
      "risk": "string",
      "evidence": []
    }
  ],
  "recommended_task_refs": [
    {
      "task_id": "string",
      "paved_road_refs": [],
      "implementation_interface_contract": {},
      "departure_requires_review": true
    }
  ]
}
```

## Guardrails

- Do not invent a paved road from preference or generic best practice.
- Do not block justified new abstractions when existing patterns cannot safely absorb the change.
- Do not recommend broad rewrites. Prefer the smallest extension of an existing pattern.
- Mark weak evidence as a gap or open question, not a rule.
- For docs, lint-only, and build-validation work, report `not_applicable` when no code path or build pattern changes.

## Quality Gates

- Every paved-road candidate cites at least one evidence source.
- Every `no_paved_road_found` result explains the search path and closest convention.
- Every recommended departure names the invariant or verifier that protects the new path.
- Every implementation-interface recommendation names the existing paved-road surface, the integration point it protects, and the validation gate that proves it.
- Deprecated patterns must include the replacement path or state that replacement is unknown.

## Removal Criteria

Remove this discovery skill when models consistently infer repo-local build paths and reuse them without explicit guidance. Keep a smaller verification gate that detects duplicated or inconsistent patterns.
