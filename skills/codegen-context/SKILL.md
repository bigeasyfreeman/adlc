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
    "id": "BE-001",
    "task_classification": "feature | bugfix | build_validation | lint_cleanup",
    "description": "string",
    "acceptance_criteria_gwt": [],
    "verification_spec": {
      "primary_verifier": {
        "type": "test | reproducer | command",
        "command": "string",
        "target": "string",
        "expected_pre_change": "fail",
        "expected_post_change": "pass"
      },
      "secondary_verifiers": [],
      "must_fail_before_change": true,
      "must_be_deterministic": true,
      "scope_note": "string"
    },
    "pattern_ref": "string",
    "reference_implementation": "string",
    "files_to_create": ["file paths"],
    "files_to_modify": ["file paths"],
    "dependency_ids": ["task IDs"],
    "parallel": true,
    "manual_test_plan": [{"step": "string", "action": "string", "expected": "string"}]
  },
  "build_brief": {
    "applicability_manifest": {},
    "existing_patterns": [{"pattern": "string", "file_path": "string", "reuse_instructions": "string"}],
    "compatibility_constraints": {
      "backwards_compat": "string",
      "forward_compat": "string",
      "degradation_strategy": "string"
    },
    "performance_budget": [{"operation": "string", "latency_target": "string", "constraint": "string"}]
  },
  "research_deliverable": {
    "service_placement": {},
    "integration_paths": {},
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

What gets inlined:
- Reference implementation code
- Current contents of every file listed in `files_to_modify`
- Pre-written tests or command-verifier output, depending on task class
- Fixtures and seed data when they exist
- Relevant schema definitions
- Scaffolded contracts and implementation guide
- The existing pattern table from the Build Brief
- Compatibility constraints and performance budget when active

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
[Paste only the constraints that are active for this task.]

## 8. Performance Budget
[Paste only the targets that are active for this task.]

## 9. Schema
[Paste only the relevant schema sections.]

## 10. What Not To Do
[Paste the negative constraints from duplication and verifier quality.]

## 11. Manual Test Plan
[Paste if present.]

## 12. Verification
Run the primary verifier first.
If it fails for the wrong reason, adjust the verifier.
If it fails for the right reason, make the smallest change that makes it pass.
Then run the secondary verifiers.
```

---

## How The Prompt Is Assembled

### Step 1: Extract task-relevant research

From the research deliverable, pull only what the task needs:
- integration path
- duplication risks
- scalability concerns
- schema changes

### Step 2: Extract active brief sections

Pull in only the brief sections that the applicability manifest marks active:
- existing patterns
- compatibility constraints when applicable
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
