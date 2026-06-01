# Skill: Codegen Context Assembly

> Assembles a single per-task coding prompt from the brief, research, scaffolding, and verifier metadata. The prompt should match the task class, not force universal test ceremony.

---

## Why This Exists

The coding agent needs one prompt, not a pile of documents. But that prompt should be driven by `task_classification` and `verification_spec`, because different tasks need different verifiers:
- feature tasks need behavioral tests
- bugfix tasks need a reproducer or regression guard
- build-validation tasks need the exact failing command
- lint-cleanup tasks need the exact failing lint or fmt command

The assembled context is the contract. It should not imply that every task starts with pre-written tests.

---

## Trigger

Activated after the Build Brief is approved and the task has a verifier contract available.

1. Build Brief approved
2. Relevant scaffolding exists, if the task needs scaffolding
3. QA artifacts exist when the task class warrants them
4. Task tickets exist

This skill runs before the coding agent starts. Its output is the coding agent's input.

---

## Input

```json
{
  "task": {
    "task_id": "BE-001",
    "artifact_type": "implementation_task | validation_task",
    "task_classification": "feature | bugfix | build_validation | lint_cleanup",
    "objective": "string",
    "decision_contract": {},
    "acceptance_criteria": [],
    "tech_debt_boundaries": {},
    "compatibility_contract": {},
    "construct_map_refs": ["graph:construct:service-or-module"],
    "paved_road_refs": ["skill:paved-road-registry#reference-id"],
    "intent_contract_refs": ["brief:intent:task-id"],
    "production_invariant_coverage": [
      {
        "invariant": "identity | auth | tenancy | data_integrity | persistence | ordering | idempotency | retries | sensitive_data | migration | downgrade | observability | dependency_failure | other",
        "status": "covered | not_applicable | gap | requires_human_judgment",
        "evidence": ["string"]
      }
    ],
    "evidence_responsibilities": [],
    "definition_of_done": [],
    "verification_spec": {
      "primary_verifier": {
        "type": "test | reproducer | command",
        "command": "string",
        "target": "string",
        "expected_pre_change": "fail",
        "expected_post_change": "pass",
        "target_files": ["file paths"],
        "expected_failure_mode": "string"
      },
      "secondary_verifiers": [],
      "must_fail_before_change": true,
      "must_be_deterministic": true,
      "scope_note": "string"
    },
    "pattern_ref": "string",
    "reference_impl": "string",
    "files_to_create": ["file paths"],
    "files_to_modify": ["file paths"],
    "dependencies": ["task IDs"],
    "parallel": true,
    "manual_test_plan": [{"step": "string", "action": "string", "expected": "string"}]
  },
  "build_brief": {
    "applicability_manifest": {},
    "existing_patterns": [{"pattern": "string", "file_path": "string", "reuse_instructions": "string"}],
    "enterprise_readiness_contract": {},
    "compatibility_constraints": {
      "backwards_compat": "string",
      "forward_compat": "string",
      "degradation_strategy": "string"
    },
    "graph_research_evidence": {},
    "construct_map": {},
    "paved_road_evidence": {},
    "intent_contract": {},
    "production_invariant_coverage": [],
    "context_layer_requirements": [],
    "performance_budget": [{"operation": "string", "latency_target": "string", "constraint": "string"}]
  },
  "research_deliverable": {
    "service_placement": {},
    "integration_paths": {},
    "construct_map": {},
    "paved_road_evidence": {},
    "load_bearing_invariants": [],
    "duplication_risks": {},
    "scalability": {},
    "schema_intelligence": {}
  },
  "scaffolding": {
    "generated_files": ["file paths"],
    "implementation_guide": "string"
  },
  "verification_artifacts": {
    "test_file": "string",
    "fixture_file": "string",
    "test_count": "number",
    "command_checks": [],
    "all_currently_failing": true
  },
  "repo_map": {
    "architecture": {},
    "conventions": {},
    "tech_stack": {}
  },
  "context_artifacts": {
    "module_manifest": "markdown string | null",
    "behavioral_contracts": "markdown string | null",
    "decision_log": "markdown string | null"
  }
}
```

---

## The Zero-Read Principle

The coding agent should never need to read a file to understand what to do. Every piece of context it needs is inlined directly into the prompt.

Hard rule:
- Every file listed in `files_to_modify` must have its current content inlined
- Every file in `reference_impl` must have its code inlined
- Every behavioral test artifact, fixture, and command verifier relevant to the task must be inlined
- Every implementation task must include its decision contract, tech debt boundaries, compatibility contract, evidence responsibilities, and Definition of Done. If the task is blocked by an unresolved Type 1 decision, do not assemble a coding prompt; return `stuck` with reason `unresolved_decision_blocks_implementation`.
- Every code-changing implementation task must include its construct-map refs, paved-road refs or explicit `no_paved_road_found`, intent contract refs, and production invariant coverage. If these are missing for a medium+ blast-radius code path, return `stuck` with reason `missing_scalable_code_primitives`.

What gets inlined:
- Reference implementation code
- Current contents of every file listed in `files_to_modify`
- Pre-written tests or command-verifier output, depending on task class
- Fixtures and seed data when they exist
- Relevant schema definitions
- Scaffolded contracts and implementation guide
- The existing pattern table from the Build Brief
- Task-relevant construct relationships, validation surfaces, and blast-radius notes
- Paved-road reference implementations, allowed departures, and `do_not_reimplement` rules
- Intent constraints, explicit non-goals, load-bearing assumptions, and human-judgment checkpoints
- Production invariant coverage for the task, including any gaps or review-required items
- Compatibility constraints and performance budget when active
- Graph research evidence relevant to compatibility, reuse, and blast radius
- Module manifests, behavioral contracts, and decision-log warnings when the task touches those modules

What does not get inlined:
- Unrelated files
- Entire dependency manifests
- Full migration history

---

## Verification Integration

The assembled prompt must carry the verifier contract explicitly.

```markdown
## Verification Spec
- Task class: `[task_classification]`
- Primary verifier: `[type + command/test/reproducer]`
- Expected pre-change result: fail
- Expected post-change result: pass
- Target files: `[verification_spec.primary_verifier.target_files]`
- Expected failure mode: `[verification_spec.primary_verifier.expected_failure_mode]`
- Secondary verifiers: `[optional list]`
- Scope note: `[why this verifier is sufficient]`

## Verifier Quality
- Task-class match
- Falsifiable before the change
- Closest signal to the defect
- Deterministic and low-noise
- Minimal sufficient coverage
```

Task-class behavior:
- `feature`: inline the tests that define success
- `bugfix`: inline the reproducer or regression guard
- `build_validation`: inline the failing command and expected failure shape
- `lint_cleanup`: inline the failing lint or fmt command and expected failure shape

No task should be forced into fabricated behavioral tests when the verifier is a command.

## Normalize Acceptance Criteria

Before emitting assembled context, normalize every task's acceptance criteria into structured Given/When/Then objects.

Normalization rules:
- If an item is already structured with `id`, `given`, `when`, and `then`, preserve it as-is.
- If an item is a string, emit:
  - `id`: `AC-{task_id}-{n}`
  - `given`: `""`
  - `when`: the shortest objective-derived action statement for the task
  - `then`: the original string text unchanged
  - `measurable_post_condition`: `""`
- Preserve item order so downstream AC-to-test mappings stay deterministic across retries.
- Preserve any existing `measurable_post_condition`; do not collapse it into prose or drop it from the assembled prompt.

Downstream agents should consume only the normalized structured form. This keeps legacy string-only briefs runnable without weakening newer structured briefs.

---

## Output: The Coding Agent Prompt

For each task, this skill produces a single markdown document that is the coding agent's system prompt.

```markdown
# Task: [ID] [Description]

## Your Mission
Make the primary verifier in `[verification_spec]` pass by implementing the smallest correct change.
Do not modify verification artifacts unless the task class explicitly requires it.

## Rules
- Follow the patterns in this document exactly.
- Reuse existing code. Do not duplicate what already exists.
- If a pattern is unclear, use the inlined reference content. Do not guess.
- Run the primary verifier after every meaningful change.
- Stop when the primary verifier passes, then run any secondary verifiers.

## 1. What You're Building
[Short functional description stripped of irrelevant jargon.]

## 2. Verification Spec
- Task class: `[task_classification]`
- Primary verifier: `[type, command, or reproducer]`
- Secondary verifiers: `[optional list]`
- Scope note: `[why the verifier is sufficient]`
- Verifier quality: `[why this is deterministic and task-class aligned]`

## 3. Verification Artifacts
### Feature or bugfix task
```text
[Paste the actual test file or reproducer content]
```

### Build-validation or lint-cleanup task
```text
[Paste the exact failing command, expected failure shape, and any captured output needed to rerun it]
```

## 4. Files to Modify or Create
These are the exact files this task touches.

## 5. Reference Implementations
[Paste the actual reference code and only the patterns needed for this task.]

## 6. Existing Patterns
[Paste only the relevant pattern table entries from the Build Brief.]

## 7. Compatibility Constraints
[Paste the task `compatibility_contract`, active enterprise readiness compatibility constraints, and any rollout or migration expectations.]

## 8. Scalable AI Code Primitives
### Construct Map
[Paste only construct_map_refs relevant to this task: affected constructs, relationships, validation surfaces, and direct evidence.]

### Paved Road
[Paste paved_road_refs, reference_impl content, do_not_reimplement rules, allowed_departure, and any explicit no_paved_road_found rationale.]

### Intent Contract
[Paste behavior, why, constraints, non-goals, edge cases, load-bearing assumptions, and review checkpoints.]

### Production Invariants
[Paste production_invariant_coverage entries, status, evidence, and required verifier or human-judgment checkpoint.]

## 9. Tech Debt Boundaries
[Paste prerequisite debt, deferred debt, and safe-deferral rationale. Do not ask the coding agent to implement unrelated catalog items.]

## 10. Comprehension Context
[Paste relevant module manifest entries, behavioral contracts, decision-log warnings, graph research evidence, and unresolved context gaps.]

## 11. Evidence and Definition of Done
[Paste evidence responsibilities and binary Definition of Done checks.]

## 12. Performance Budget
[Paste only the targets that are active for this task.]

## 13. Schema
[Paste only the relevant schema sections.]

## 14. What Not To Do
[Paste the negative constraints from duplication and verifier quality.]

## 15. Manual Test Plan
[Paste if present.]

## 16. Verification
Run the primary verifier first.
If it fails for the wrong reason, adjust the verifier.
If it fails for the right reason, make the smallest change that makes it pass.
Then run the secondary verifiers.
```

---

## How The Prompt Is Assembled

### Step 1: Extract task-relevant research

From the research deliverable, pull only what the task needs:
- construct-map entries for affected modules, interfaces, schemas, configs, state, tests, and reverse dependencies
- paved-road candidates or the explicit `no_paved_road_found` gap
- load-bearing invariant notes and validation surfaces
- integration path
- duplication risks
- scalability concerns
- evidence-backed production readiness probe findings assigned to this task
- schema changes

### Step 2: Extract active brief sections

Pull in only the brief sections that the applicability manifest marks active:
- existing patterns
- compatibility constraints when applicable
- graph research evidence for compatibility, reuse, and blast radius
- construct map, paved-road evidence, intent contract, and production invariant coverage when the task changes code, schema, runtime behavior, persistence, API contracts, or deployment conventions
- context-layer artifacts and decision-log warnings when applicable
- performance budget when applicable

### Step 3: Inline the right verification artifacts

- For `feature` and `bugfix`, inline tests or reproducible failure artifacts
- For `build_validation` and `lint_cleanup`, inline commands and expected failure shape
- Do not invent a test suite if the task class does not justify one

### Step 4: Convert references to line-specific instructions

Every instruction must name:
- the exact file
- the exact location
- the exact pattern to follow
- the exact interface or verifier to use

### Step 5: Add negative constraints

State explicitly what must not be duplicated, hidden, or invented.

For production readiness findings, include only the specific `PROD-*` entries that the Build Brief assigned to the task. Do not ask the coding agent to implement unrelated catalog items such as queues, CDNs, replicas, load tests, or runbooks unless the finding has repo evidence, priority, and a verification path.

For paved-road findings, include only repo-local reference implementations and explicit allowed departures. Do not ask the coding agent to invent a parallel framework, schema style, emitter format, or build convention unless the Build Brief names `no_paved_road_found` and records why existing patterns cannot absorb the work.

### Step 6: Add the verification loop

The prompt ends with the primary verifier and any secondary verifiers. The coding agent's terminal state is that the verifier contract has been satisfied.

---

## Parallel Execution

Tasks flagged as `parallel: true` with no dependencies get separate assembled prompts and can be dispatched independently.

---

## MCP Server Contract

### Tool: `assemble_codegen_context`

```json
{
  "name": "assemble_codegen_context",
  "description": "Assemble all ADLC artifacts into an optimized coding agent prompt for a specific task",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": { "type": "string" },
      "build_brief": { "type": "string" },
      "research_deliverable": { "type": "string" },
      "repo_path": { "type": "string" }
    },
    "required": ["task_id", "build_brief", "research_deliverable", "repo_path"]
  }
}
```

### Tool: `assemble_all_tasks`

```json
{
  "name": "assemble_all_tasks",
  "description": "Assemble codegen contexts for all tasks in the Build Brief, with parallel execution grouping",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": { "type": "string" },
      "research_deliverable": { "type": "string" },
      "repo_path": { "type": "string" },
      "output_directory": { "type": "string" }
    },
    "required": ["build_brief", "research_deliverable", "repo_path"]
  }
}
```

### Tool: `verify_task_completion`

```json
{
  "name": "verify_task_completion",
  "description": "Verify a coding agent's output against the task verifier contract",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": { "type": "string" },
      "repo_path": { "type": "string" },
      "verification_spec": { "type": "object" },
      "duplication_guardrails": {
        "type": "array",
        "items": { "type": "string" }
      }
    },
    "required": ["task_id", "repo_path", "verification_spec"]
  }
}
```
