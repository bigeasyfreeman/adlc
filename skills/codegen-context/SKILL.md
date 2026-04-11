# Skill: Codegen Context Assembly

> Assembles all ADLC artifacts into optimized, per-task coding agent inputs that maximize one-shot production code success. This is the bridge between planning and execution — it takes the research deliverable, scaffolding, pre-written tests, schema definitions, and task tickets and compresses them into the exact context a coding agent needs to produce production-ready code on the first pass.

---

## Why This Exists

The ADLC system produces excellent artifacts:
- **Codebase Research** tells the agent what service to build in, what to reuse, what to extend, what patterns to follow
- **Architecture Scaffolding** produces port interfaces, implementation guides, and directory structure
- **QA Test Data** produces deterministic test scenarios from G/W/T acceptance criteria
- **JIRA Tickets** have self-contained task descriptions with pattern references

But a coding agent can't read 5 separate artifacts and synthesize them the way a human can. It needs a **single, assembled context per task** that contains everything in the right order, at the right level of detail, with explicit instructions — not references to other documents.

This skill is the difference between "here's a well-documented task" and "here's everything you need to write production code in one pass."

---

## Trigger

Activated after ALL of these are complete:
1. Build Brief approved
2. Architecture Scaffolding generated (contracts/guides exist for the task)
3. QA tests generated (tests exist and are runnable)
4. JIRA tickets created

This skill runs BEFORE the coding agent starts. Its output IS the coding agent's input.

---

## Input

```json
{
  "task": {
    "id": "BE-001",
    "description": "string (from JIRA ticket)",
    "acceptance_criteria_gwt": [],
    "pattern_ref": "string",
    "reference_implementation": "string (file path)",
    "files_to_create": ["file paths"],
    "files_to_modify": ["file paths"],
    "dependency_ids": ["task IDs"],
    "parallel": true,
    "manual_test_plan": [{"step": "string", "action": "string", "expected": "string"}]
  },
  "build_brief": {
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
  "pre_written_tests": {
    "test_file": "string (file path)",
    "fixture_file": "string (file path)",
    "test_count": "number",
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

## The Zero-Read Principle (Inspired by Superpowers Subagent-Driven Development)

The coding agent should NEVER need to read a file to understand what to do. Every piece of context it needs is **inlined directly into the prompt**. This is the single biggest factor in one-shot success.

**Why:** A coding agent that sees "follow the pattern in `src/services/deliverable_service.py`" will either:
- Read the file (costs a tool call, breaks flow, may read the wrong section)
- Guess (gets it wrong)

Instead, paste the relevant code directly. The agent sees the actual code, not a pointer.

**Hard rule:** Every file listed in `files_to_modify` must have its current content inlined. Every file in `reference_impl` must have its code inlined. The coding agent reads ZERO files — everything is in the prompt.

**What gets inlined:**
- Reference implementation code (full file contents from every reference_impl path)
- Current contents of every file listed in files_to_modify (so the agent sees what it's changing)
- Pre-written test file contents (every test, every assertion)
- Test fixtures and seed data
- Schema definitions (models, migrations)
- Scaffolded stubs (port interfaces, adapter shells)
- Relevant type definitions and interfaces
- Existing pattern table from the Build Brief (so the agent knows established conventions)
- Compatibility constraints from Section 10 of the Build Brief
- Performance budget from Section 8 of the Build Brief

**What does NOT get inlined (too large, too noisy):**
- Entire package.json / pyproject.toml (just the relevant deps)
- Full migration history (just the latest relevant migration)
- Unrelated test files

The controller assembles the context. The coding agent executes against it. Clean separation.

---

## TDD Enforcement Integration

Every codegen context prompt includes a mandatory TDD section. The coding agent follows RED-GREEN-REFACTOR per acceptance criterion. See `skills/tdd-enforcement/SKILL.md` for the full protocol.

**Two modes:**
- **Pre-written tests exist** (QA skill ran first): Agent runs existing test → verifies FAIL → implements until PASS
- **No pre-written tests**: Agent writes test from G/W/T in the task → verifies FAIL → implements until PASS

The codegen context detects which mode applies and generates the appropriate TDD instructions per cycle.

---

## Output: The Coding Agent Prompt

For each task, this skill produces a single markdown document that IS the coding agent's system prompt / context. The coding agent receives ONLY this document — it should not need to read any file to understand what to build.

```markdown
# Task: [ID] [Description]

## Your Mission
Make all [N] tests in `[test_file_path]` pass by implementing `[specific deliverable]`.
Do not modify the tests. Do not skip tests. All tests must pass.

## Rules
- Follow the patterns in this document exactly. Do not invent new patterns.
- Reuse existing code. Do not duplicate what already exists.
- If you are unsure about a pattern, read the reference file cited below — do not guess.
- Run the tests after every meaningful change. Stop when all pass.

---

## 1. What You're Building
[1-3 sentences. Functional description from the task, stripped of all technical jargon.]

## 2. Tests You Must Pass
These tests already exist at `[test_file_path]`. They are currently failing. Your job is to make them pass.

```
[Paste the actual test file contents — every test, every assertion]
```

Test fixtures are at `[fixture_file_path]`:
```
[Paste fixture contents]
```

## 3. Files to Modify or Create

| File | Action | What to Do |
|------|--------|-----------|
| `[path]` | MODIFY | [Specific: "Add method `shareDeliverable()` after line 78. Follow the same try/catch pattern as `createDeliverable()` on line 45."] |
| `[path]` | CREATE | [Specific: "Implement the `ShareRepo` port interface defined in `src/domain/repos/ShareRepo.ts`. Follow `ClickHouseCreditRepo.ts` as your template — same constructor pattern, same error handling, same async wrapping."] |
| `[path]` | MODIFY | [Specific: "Add route `POST /api/v1/deliverables/:id/share` to the router. Follow the pattern at line 23 of this file for request validation with zod."] |
| `[path]` | MODIFY | [Specific: "Register `ShareRepo` in the container. Follow the binding pattern on line 12."] |

## 4. Reference Implementations (READ THESE FIRST)
Before writing any code, read these files. They are the patterns you must follow.

**Primary reference** (most similar to what you're building):
```
[Paste the FULL contents of the reference implementation file — not a path, the actual code]
```
File: `[path]` — This is how [similar feature] was built. Follow the same structure.

**Secondary references** (specific patterns to reuse):
- Error handling: See lines [X-Y] in `[path]` — use the same `DomainError` subclass pattern
- Validation: See `[path]` — use the same zod schema + `parseOrThrow` pattern
- Database queries: See lines [X-Y] in `[path]` — use the same Prisma query pattern with `include`

## 5. Existing Patterns
These are the established patterns in this codebase. Follow them exactly. Do not invent new patterns.

| Pattern | File Path | Reuse Instructions |
|---------|-----------|-------------------|
| [pattern name] | `[path]` | [how to reuse or extend] |
| [pattern name] | `[path]` | [how to reuse or extend] |

[Inlined from the Build Brief pattern table — every pattern the coding agent may encounter or must follow for this task.]

## 6. Files to Create / Files to Modify
These are the EXACT files this task touches. Do not create or modify files outside this list.

**Files to Create:**
| File Path | Purpose | Template/Pattern to Follow |
|-----------|---------|---------------------------|
| `[path]` | [purpose] | Follow `[reference_impl path]` |

**Files to Modify:**
| File Path | What to Change | Location |
|-----------|---------------|----------|
| `[path]` | [specific change] | [line number or method anchor] |

[From the task's files_to_create and files_to_modify fields — NOT the generic file_targets.]

## 7. Reference Implementations
Before writing any code, study these implementations. Their FULL CODE is inlined below — do not read any files, everything you need is here.

**Primary reference** (most similar to what you're building):
```
[ACTUAL CODE from the primary reference_impl path — the FULL file contents, not a pointer]
```
File: `[path]` — This is how [similar feature] was built. Follow the same structure.

**Secondary references** (specific patterns to reuse):
```
[ACTUAL CODE from each secondary reference_impl — inlined, not referenced]
```
File: `[path]` — Reuse this pattern for [specific aspect].

[Every file listed in reference_impl has its code pasted here. The coding agent reads ZERO files.]

## 8. Compatibility Constraints
[From Section 10 of the Build Brief]

**Backwards Compatibility:**
[What existing behavior must NOT change. What breaks if compatibility is violated. Migration path for any breaking change.]

**Forward Compatibility:**
[What future changes this design must accommodate. Extension points that must remain open.]

**Degradation Strategy:**
[For each external dependency: what happens when it's unavailable. Fallback behavior. Timeout/retry policy.]

## 9. Performance Budget
[From Section 8 of the Build Brief]

| Operation | Latency Target | Constraint |
|-----------|---------------|------------|
| [operation] | p95 < [X]ms | [any additional constraint] |
| [operation] | p95 < [X]ms | [any additional constraint] |

Do not introduce blocking operations, unbounded queries, or N+1 patterns that would violate these targets.

## 10. Schema
The database schema for this task:

```prisma
[Paste the relevant portion of schema.prisma — including the models this task touches and any new models from schema_intelligence]
```

If a migration is needed, create it:
```bash
npx prisma migrate dev --name [migration_name_following_convention]
```
Follow the migration convention in `prisma/migrations/` — most recent migration is `[name]` for reference.

## 11. What NOT to Do (Duplication Guardrails)
[From duplication_risks — specific things the agent must NOT build because they already exist]

- Do NOT build custom access checking. Use `checkAccess()` from `src/server/middleware/permissions.ts`. Extend it with the `share` grant type.
- Do NOT build a custom retry loop for email sending. Use `withRetry()` from `src/lib/resilience.ts`.
- Do NOT create a new validation utility. Use the existing zod schemas in `src/lib/validation/`.
- Do NOT add a new error class. Extend `DomainError` from `src/domain/errors/base.ts`.

## 12. Scale Considerations
[From scalability analysis — things the agent must get right for production]

- Email sending MUST be async. Enqueue to BullMQ at `packages/worker/`. Do NOT send in the request handler.
- User list queries MUST use cursor pagination. Follow the pattern in `src/server/routes/widgetRoutes.ts:paginated()`.
- [Any other scale-critical implementation details]

## 13. Manual Test Plan
[From the task's manual_test_plan field, if present. Omit this section if the task has no manual_test_plan.]

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | [manual action] | [expected outcome] |
| 2 | [manual action] | [expected outcome] |

These are human-verified checks that complement the automated tests. They cover UX flows, visual correctness, or integration behaviors that cannot be asserted programmatically.

## 14. Verification
After implementation, run:
```bash
[exact test command for this task's tests]
```

All [N] tests must pass. If any fail:
1. Read the error message
2. Check your implementation against the reference in Section 4
3. Fix and re-run
4. Do not modify the tests

When all tests pass, run the full suite to ensure no regressions:
```bash
[exact full test suite command]
```
```

---

## How the Prompt Is Assembled

### Step 1: Extract task-relevant research

From the research deliverable, pull ONLY what this specific task needs:
- Integration path for this task's capability (reuse / extend / new)
- Duplication risks that apply to this task
- Scalability concerns that apply to this task
- Schema changes this task needs

Discard everything else. The coding agent's context window is finite — only include what affects this task.

### Step 1b: Extract new brief sections

From the Build Brief, pull the following into their dedicated prompt sections:
- **Existing Patterns** (pattern table) — becomes Section 5 of the prompt so the agent knows established conventions before it writes any code
- **files_to_create / files_to_modify** from the task — becomes Section 6, the explicit scope boundary
- **reference_impl paths** from the task — becomes Section 7, with ACTUAL CODE inlined (not just the path)
- **Compatibility Constraints** from Brief Section 10 — becomes Section 8, so the agent knows what must not break
- **Performance Budget** from Brief Section 8 — becomes Section 9, so the agent knows latency targets
- **manual_test_plan** from the task (if present) — becomes Section 13, so the agent understands manual verification expectations

### Step 2: Inline file contents (don't reference, paste)

A coding agent that sees "follow the pattern in `src/server/adapters/ClickHouseCreditRepo.ts`" will either:
- Read the file (costs a tool call, breaks flow)
- Guess (gets it wrong)

Instead, **paste the file contents directly into the prompt.** The coding agent sees the actual code, not a pointer to it. This is the single biggest factor in one-shot success.

Inline these files:
- The reference implementation (primary pattern to follow)
- The pre-written test file (what must pass)
- The test fixtures (seed data)
- The relevant schema section
- The scaffolded contracts and implementation guide (if they exist for this task)

### Step 3: Convert references to line-specific instructions

Bad: "Add a share method to AgentService following the existing pattern"
Good: "Add method `shareDeliverable()` to `src/services/agent/AgentService.ts` after line 78. Follow the same try/catch pattern as `createDeliverable()` on line 45. Use the `ShareRepo` port (already scaffolded at `src/domain/repos/ShareRepo.ts`) for persistence."

Every instruction must name:
- The exact file
- The exact location (line number or "after method X")
- The exact pattern to follow (with line reference in the reference file)
- The exact interface/type to implement

### Step 4: Add negative constraints (what NOT to do)

From duplication risks, generate explicit "do NOT" instructions. Coding agents are eager to build things. Without explicit negative constraints, they will:
- Create a new utility when one exists
- Build custom error handling when a pattern exists
- Write synchronous code when async is required
- Create a new permission system when one can be extended

### Step 5: Add the verification loop

The prompt ends with the test command. The coding agent's terminal state is "all tests pass." This creates a natural verification loop:
1. Write code
2. Run tests
3. If tests fail, read error, fix, go to 2
4. If tests pass, run full suite for regressions
5. Done

---

## Test-First Assembly (TDD for Agents)

The QA skill MUST run BEFORE this skill. The tests must exist and be failing before the coding agent starts. This inverts the typical flow:

```
Traditional: Write code → Write tests → Fix code
ADLC:        Write tests (from G/W/T) → Assemble context → Agent writes code until tests pass
```

This means the QA skill execution order changes:

```
1. Build Brief approved
2. Architecture Scaffolding (generates contracts/guides)
3. Schema migration (if new models needed)
4. QA Test Generation (generates FAILING tests from G/W/T)
5. Codegen Context Assembly (assembles per-task prompts)
6. Coding Agent executes (goal: make tests pass)
7. Verification: all tests pass + no regressions
```

Tests being pre-written and failing is not a bug — it's the specification. The coding agent's entire job is to make them pass.

---

## Parallel Execution

Tasks flagged as `parallel: true` with no dependencies get separate assembled prompts and can be dispatched to separate coding agents simultaneously.

```
Assembled Prompts:
├── BE-001-prompt.md → Coding Agent 1
├── BE-002-prompt.md → Coding Agent 2 (parallel with BE-001)
├── BE-003-prompt.md → Coding Agent 2 (after BE-001, depends on it)
├── FE-001-prompt.md → Coding Agent 3 (parallel with all BE tasks)
└── INF-001-prompt.md → Coding Agent 4 (parallel)
```

Each agent operates independently with its own assembled context. No agent needs to know what the others are doing — the task dependencies ensure ordering.

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
      "task_id": {
        "type": "string",
        "description": "Task ID (e.g., BE-001)"
      },
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown"
      },
      "research_deliverable": {
        "type": "string",
        "description": "Full research deliverable JSON"
      },
      "repo_path": {
        "type": "string",
        "description": "Path to the repository"
      },
      "test_file_path": {
        "type": "string",
        "description": "Path to the pre-written test file for this task"
      },
      "scaffold_files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Paths to scaffolded contract/guide files relevant to this task"
      }
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
      "build_brief": {
        "type": "string"
      },
      "research_deliverable": {
        "type": "string"
      },
      "repo_path": {
        "type": "string"
      },
      "output_directory": {
        "type": "string",
        "description": "Where to write the assembled prompt files"
      }
    },
    "required": ["build_brief", "research_deliverable", "repo_path"]
  }
}
```

### Tool: `verify_task_completion`

```json
{
  "name": "verify_task_completion",
  "description": "Verify a coding agent's output: run task tests, check for regressions, validate against duplication guardrails",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string"
      },
      "repo_path": {
        "type": "string"
      },
      "test_file_path": {
        "type": "string"
      },
      "duplication_guardrails": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of things the code must NOT duplicate"
      }
    },
    "required": ["task_id", "repo_path", "test_file_path"]
  }
}
```

---

## CLI Interface

```bash
# Assemble context for a single task
adlc-codegen assemble --task BE-001 --brief ./build-brief.md --research ./research.json --repo ./my-repo

# Assemble all tasks with parallel grouping
adlc-codegen assemble-all --brief ./build-brief.md --research ./research.json --repo ./my-repo --output ./codegen-prompts/

# Execute a task (assemble + dispatch to coding agent + verify)
adlc-codegen execute --task BE-001 --brief ./build-brief.md --research ./research.json --repo ./my-repo --agent claude-code

# Execute all tasks respecting dependency order and parallelism
adlc-codegen execute-all --brief ./build-brief.md --research ./research.json --repo ./my-repo --agent claude-code --parallel 3

# Verify task completion
adlc-codegen verify --task BE-001 --repo ./my-repo --tests ./tests/be-001.test.ts
```

---

## Quality Gates

- [ ] Every task has an assembled prompt with ALL sections filled (no "see reference" without inlined content)
- [ ] Every assembled prompt includes the full test file contents (not a path reference)
- [ ] Every assembled prompt includes the full reference implementation contents (ACTUAL CODE, not paths)
- [ ] Every file in `files_to_modify` has its current content inlined in the prompt
- [ ] Every file in `reference_impl` has its full code inlined in the prompt
- [ ] Existing patterns table is present with file paths and reuse instructions
- [ ] Files to Create / Files to Modify section uses task-specific lists (not generic file_targets)
- [ ] Compatibility constraints section is populated from Brief Section 10
- [ ] Performance budget section includes numeric latency targets per operation
- [ ] Manual test plan section is present when the task has a manual_test_plan field
- [ ] Every "modify" instruction includes a line number or method name anchor
- [ ] Every "create" instruction includes the pattern file to follow with its contents inlined
- [ ] Duplication guardrails list specific existing files, not generic advice
- [ ] Scalability constraints are implementation-specific, not theoretical
- [ ] Schema section includes the exact Prisma model(s) and migration command
- [ ] Verification section includes the exact test command
- [ ] Parallel tasks have no shared file modifications (would cause merge conflicts)
- [ ] Pre-written tests exist and are failing before assembly
- [ ] After coding agent execution, all task tests pass
- [ ] After coding agent execution, full test suite passes (no regressions)
