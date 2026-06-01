---
name: graph-research
description: "Uses Graphify as ADLC's graph-backed research layer and Beads as an optional dependency-aware task memory layer. Produces evidence for compatibility, reuse, accuracy, dark-code hotspots, and long-horizon handoff."
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: core
  consumes_manifest: true
  produces:
    - graph_research_evidence
    - construct_map
    - compatibility_evidence
    - paved_road_refs
    - task_memory_context
---

# Graph Research

## Purpose

ADLC research must be grounded in a persistent map of the codebase, not a fresh grep pass every time. This skill makes Graphify the default repo-understanding substrate and treats Beads as the optional work graph for task state, dependency holds, and durable agent memory.

Use Graphify for:
- codebase topology, construct relationships, and cross-file relationships
- forward- and backward-compatibility research
- reuse discovery and duplicate-pattern avoidance
- blast-radius and dependency-path analysis
- validation-surface discovery across tests, schemas, fixtures, and contract checks
- identifying dark-code hotspots where behavior emerges across modules

Use Beads for:
- dependency-aware decomposition and ready-work selection
- agent handoff memory across long-running ADLC sessions
- task relationships such as blocks, relates_to, duplicates, and supersedes
- durable notes that should survive context compaction

Do not use Beads as an architecture oracle. Do not use Graphify as the work-item source of truth. They solve different problems.

## Trigger

Run during `research` before raw repository search whenever a repo path is available.

Run again during `code_review` or `pr_prep` when the change touches any of:
- public API, data format, storage, auth, or service boundaries
- shared utilities or reusable framework code
- migration, rollout, downgrade, or compatibility-sensitive behavior
- agent-generated code where comprehension evidence is missing

## Preconditions

If `graphify-out/wiki/index.md` exists, navigate that first.

If `graphify-out/GRAPH_REPORT.md` exists:
1. Read it before broad source reads.
2. Compare its `Built from commit` value against `git rev-parse HEAD`.
3. If stale, run `graphify update .` and record that the refresh is AST-only unless semantic extraction is also run.

If `graphify-out/` does not exist:
1. Run `graphify update .` for an AST-only graph when Graphify is installed.
2. If Graphify cannot run, record `graph_status = unavailable` and fall back to normal research with an explicit gap.

If `.beads/` exists or `bd` is available:
1. Run `bd prime` for workflow context.
2. Run `bd ready --json` when choosing execution slices.
3. Use `bd show <id> --json` before treating an issue description as authoritative.
4. Record task-memory evidence separately from repo evidence.

## Required Graphify Queries

Ask graph questions before raw grep when the graph is available:

```bash
graphify query "What modules and interfaces are most relevant to this PRD or change?"
graphify query "What constructs, config, schemas, persistence paths, and tests are related to this PRD or change?"
graphify query "What existing implementation should be reused or extended for this request?"
graphify query "What backward compatibility or forward compatibility paths could this change affect?"
graphify query "What validation surfaces prove behavior for the constructs this change touches?"
graphify query "What cross-module paths create dark-code risk for this request?"
graphify path "<changed module>" "<dependent module>"
graphify explain "<core concept or module>"
```

Use the specific module, service, schema, or public interface names from the PRD or diff. Do not ask vague graph questions and present the answer as evidence.

## Compatibility Research Rules

For every interface, schema, storage, or integration change, produce an explicit compatibility finding:

- **Backward compatibility:** current consumers, stored data, config, CLI flags, API clients, and old artifacts that must keep working.
- **Forward compatibility:** known future phases, extension points, version fields, capability negotiation, and places where premature lock-in would be expensive.
- **Downgrade and rollback:** what happens if the new code is rolled back after data or external state was written.
- **Reuse:** existing modules, helpers, schemas, fixtures, or workflows to extend instead of reimplement.
- **Accuracy:** where the graph is authoritative, where it is AST-only, and what was directly verified in source.

Graph evidence is a starting point, not proof by itself. Confirm critical compatibility claims against source files, schemas, tests, or docs before the Build Brief turns them into tasks.

## Construct Map Rules

For every code-backed ADLC run, produce a construct map scoped to the requested work:

- **Constructs:** modules, services, packages, CLIs, schemas, configs, environment variables, APIs, internal interfaces, events, queues, persistence paths, tests, and generated artifacts.
- **Relationships:** imports, callers, consumers, producers, reverse dependencies, stored artifacts, and compatibility-sensitive paths.
- **Validation surfaces:** tests, fixtures, schemas, contract checks, smoke tests, backtests, or commands that can verify the affected behavior.
- **Accuracy gaps:** graph-only claims that were not directly verified.

Do not present "the repo" as the construct. Name the actual code constructs and relationships an agent must preserve.

## Output

```json
{
  "graph_research_evidence": {
    "graph_status": "fresh | stale_refreshed_ast_only | stale_not_refreshed | unavailable",
    "graph_report": "graphify-out/GRAPH_REPORT.md | null",
    "wiki_index": "graphify-out/wiki/index.md | null",
    "head_commit": "string | null",
    "graph_commit": "string | null",
    "queries_run": [
      {
        "query": "string",
        "result_summary": "string",
        "source": "graphify query | graphify path | graphify explain"
      }
    ],
    "direct_verification": [
      {
        "claim": "string",
        "evidence": "path:line | command output | doc quote",
        "confidence": "high | medium | low"
      }
    ]
  },
  "construct_map": {
    "constructs": [
      {
        "name": "string",
        "kind": "module | service | api | schema | config | env | persistence | event | queue | test | cli | generated_artifact | other",
        "evidence": "graph query + path:line | command output",
        "confidence": "high | medium | low"
      }
    ],
    "relationships": [
      {
        "from": "string",
        "to": "string",
        "relationship": "imports | calls | consumes | produces | stores | validates | configures | depends_on | other",
        "evidence": "graph query + direct verification"
      }
    ],
    "validation_surfaces": [],
    "blast_radius": [],
    "accuracy_gaps": []
  },
  "compatibility_evidence": {
    "backward_compatibility": [],
    "forward_compatibility": [],
    "rollback_or_downgrade": [],
    "reuse_paths": [],
    "paved_road_refs": [],
    "accuracy_gaps": []
  },
  "task_memory_context": {
    "beads_status": "available | not_configured | unavailable",
    "ready_items": [],
    "blocking_dependencies": [],
    "persistent_memories": []
  },
  "dark_code_hotspots": [
    {
      "component": "string",
      "risk": "string",
      "evidence": "graph query + direct verification",
      "needs_context_artifact": true
    }
  ]
}
```

## Quality Gates

- Every compatibility claim must name a consumer, artifact, interface, or data path.
- Every reuse recommendation must cite the existing implementation by path.
- Every construct-map entry must name the construct kind and evidence.
- Every graph-derived claim must say whether it was directly verified.
- Beads findings must not replace code or graph evidence.
- If the graph is unavailable, the output must say which research confidence was reduced.
