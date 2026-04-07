# Skill: Codegen Context Assembly

> Assembles all ADLC artifacts into optimized, per-task coding agent inputs that maximize one-shot production code success. This is the bridge between planning and execution — it takes the research deliverable, scaffolding, pre-written tests, schema definitions, and task tickets and compresses them into the exact context a coding agent needs to produce production-ready code on the first pass.
>
> **THIS SKILL IS A MANDATORY GATE, NOT AN OPTIONAL STEP.** Every task that reaches a coding agent MUST pass through context assembly first. Tasks without assembled context are not agent-ready and will produce stubs instead of working code. The assembled context IS the ticket — not a separate artifact.

---

## Why This Exists

The ADLC system produces excellent artifacts:
- **Codebase Research** tells the agent what service to build in, what to reuse, what to extend, what patterns to follow
- **Architecture Scaffolding** produces port interfaces, adapter stubs, and directory structure
- **QA Test Data** produces deterministic test scenarios from G/W/T acceptance criteria
- **JIRA Tickets** have self-contained task descriptions with pattern references

But a coding agent can't read 5 separate artifacts and synthesize them the way a human can. It needs a **single, assembled context per task** that contains everything in the right order, at the right level of detail, with explicit instructions — not references to other documents.

This skill is the difference between "here's a well-documented task" and "here's everything you need to write production code in one pass."

---

## Trigger

Activated after ALL of these are complete:
1. Build Brief approved
2. Architecture Scaffolding generated (stubs exist in repo)
3. QA tests generated (tests exist and are runnable)
4. JIRA tickets created

**This skill is a MANDATORY GATE.** It runs BEFORE the coding agent starts. Its output IS the coding agent's input. No task may be dispatched to a coding agent without passing through context assembly first. Dispatching a raw ticket without assembled context is the #1 cause of stub-only code that doesn't wire together.

**Enforcement:** If a task reaches a coding agent without an assembled context, the task is rejected and returned to the context assembly queue. The Eval Council Executioner persona verifies this at every checkpoint.

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
    "dependencies": ["task IDs"],
    "parallel": true
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

**What gets inlined:**
- Reference implementation code (full file or relevant section)
- Pre-written test file contents (every test, every assertion)
- Test fixtures and seed data
- Schema definitions (models, migrations)
- Scaffolded stubs (port interfaces, adapter shells)
- Relevant type definitions and interfaces

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
- **ANTI-SLOP:** Do NOT leave TODO, FIXME, placeholder, or stub implementations. Every function must have a real implementation. Every import must resolve. Every service must be wired to its consumers. If you write a function signature, you write the body. No exceptions.
- **COMPLETENESS:** Implement the FULL requirement described in this task. Do not partially implement and leave notes for "later." Do not skip edge cases. Do not omit error handling. Do not create interfaces without implementations. If the task says "handle failure X," you handle failure X — you do not add a comment saying "TODO: handle failure X."
- **REUSABILITY:** If you create a utility, interface, or pattern that could serve multiple callers, design it that way. One-off code that only serves this task is tech debt.
- **IMMUTABILITY:** Do not change the task's acceptance criteria, scope, or requirements. If you think a requirement is wrong, flag it — do not silently skip it. Every G/W/T criterion must have a passing test when you're done.
- **BPE ENFORCEMENT:** If the task spec classifies a function as INTELLIGENCE (requires understanding — classification, evaluation, routing, judgment, decomposition, risk assessment), you MUST implement it with an LLM call path. Writing `if "feature" in text.lower()` instead of calling the LLM is a BPE violation. The pattern: static fallback (Layer 1, always runs) + LLM judgment (Layer 2, runs when llm_call_fn provided). The LLM path is the PRIMARY implementation. The static path is the FALLBACK. If you only write the static path, the implementation is incomplete — same as leaving a TODO.

---

## 1. Problem Context (Why This Task Exists)
[1-3 sentences. What is broken, missing, or needed — and WHY. Not what to code, but what problem the code solves. The coding agent must understand the problem before it writes the solution.

Example — BAD: "Build a ShareRepo adapter following the ClickHouseCreditRepo pattern."
Example — GOOD: "Users can't share deliverables because there's no persistence layer for share invitations. The invite modal (Screen 3) creates share records but nothing saves them. The test at test_share_deliverable_persists_invitation is currently failing because ShareRepo doesn't exist yet."]

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

## 5. Schema
The database schema for this task:

```prisma
[Paste the relevant portion of schema.prisma — including the models this task touches and any new models from schema_intelligence]
```

If a migration is needed, create it:
```bash
npx prisma migrate dev --name [migration_name_following_convention]
```
Follow the migration convention in `prisma/migrations/` — most recent migration is `[name]` for reference.

## 6. Integration Wiring (CRITICAL — This Is What Makes It Actually Work)

This section shows how the component you're building connects to the rest of the system. Without this, you'll build an isolated component that doesn't plug into anything.

**How your code gets called (upstream):**
```
[Paste the exact code that will call your new code. Example:]
[The route handler in api.py calls deliverable_service.share_deliverable()]
[Show the actual calling code so the agent knows the interface contract]
```

**How your code calls others (downstream):**
```
[Paste the exact code your component needs to call. Example:]
[share_email_service calls mailtrap.send() — here's the Mailtrap client pattern:]
[Show the actual client/service being called so the agent wires to it correctly]
```

**Registration / Dependency Injection:**
```
[Show exactly where and how this component gets registered. Example:]
[In api.py, the router is mounted: app.include_router(deliverables_router, prefix="/deliverables")]
[In the service constructor, inject dependencies: def __init__(self, db: AsyncSession, mailtrap: MailtrapClient)]
```

**Import chain (complete):**
```
[List every import needed for this component to work, copied from similar components:]
from services.models.share_invitations import ShareInvitations
from services.deliverable_service import DeliverableService
from utils.auth_utils import get_current_user_id_from_jwt
[etc. — real imports, not guesses]
```

**Smoke test (proves wiring works):**
After implementation, this single test proves the full chain is wired:
```
[A test that calls the API endpoint → hits the service → writes to the database → returns a response]
[This is NOT a unit test. It's a wiring test. If any link in the chain is broken, this fails.]
```

## 7. What NOT to Do (Duplication Guardrails + Anti-Slop)
[From duplication_risks — specific things the agent must NOT build because they already exist]

- Do NOT build custom access checking. Use `checkAccess()` from `src/server/middleware/permissions.ts`. Extend it with the `share` grant type.
- Do NOT build a custom retry loop for email sending. Use `withRetry()` from `src/lib/resilience.ts`.
- Do NOT create a new validation utility. Use the existing zod schemas in `src/lib/validation/`.
- Do NOT add a new error class. Extend `DomainError` from `src/domain/errors/base.ts`.

**ANTI-SLOP RULES (enforced by Eval Council):**
- Do NOT write `pass`, `TODO`, `FIXME`, `NotImplementedError`, `raise NotImplementedError`, `...` (ellipsis) as function bodies. Every function has a real implementation.
- Do NOT write placeholder return values (`return None`, `return {}`, `return []`) unless that's the actual correct behavior.
- Do NOT create a service class without wiring it into the route/handler that calls it.
- Do NOT create a model without the corresponding migration.
- Do NOT create an endpoint without registering it in the router.
- Do NOT import a module without using it.
- If you create a function that calls another service, verify the other service actually exists and the method signature matches.

## 8. Failure Modes & Error Handling
[Every I/O operation, network call, and state mutation in this task MUST have explicit failure handling.]

| Operation | What Can Fail | How to Handle | Log Event |
|-----------|--------------|---------------|-----------|
| [e.g., httpx.post to gateway] | Network timeout, 5xx, connection refused | Retry with backoff (use existing _RETRY_BACKOFF pattern), log error, return False | `component.send_failed` |
| [e.g., state_store.upsert_job] | SQLite write error, disk full | Log error with job_id, propagate exception (caller handles) | `component.store_error` |
| [e.g., llm_call for verdict] | LLM timeout, malformed response | Fallback to static heuristic (GAP-006 pattern), log warning | `component.llm_fallback` |

**Rules:**
- No bare `except: pass` — every caught exception must log
- No `except Exception` without structured logging of the error
- Every function that can fail must document what happens on failure in its docstring or inline comment
- Callers must know whether this function raises or returns an error sentinel

## 8.5 Observability Requirements
[Part of definition of done — not optional, not post-launch.]

**Structured log events this component MUST emit:**
```python
_LOG.info("component.started", job_id=job_id, [key_context_fields])
_LOG.info("component.completed", job_id=job_id, duration_ms=elapsed, result=result)
_LOG.warning("component.fallback", job_id=job_id, reason="[why fallback triggered]")
_LOG.error("component.error", job_id=job_id, error=str(exc), [context_fields])
```

**Error handling contract:**
- Exceptions caught at THIS level: [list]
- Exceptions propagated to caller: [list]
- Error codes/messages returned: [list]

**Metrics (if applicable):**
- [counter/histogram/gauge name and what it measures]

## 8.7 Contract Changes
[Document ANY changes to interfaces consumed by other components.]

**API changes:** [new endpoints, modified request/response schemas, deprecations]
**MCP tool changes:** [new tools, modified inputSchema, changed behavior]
**Data model changes:** [new/modified Pydantic models, new SQLite tables/columns, required migrations]
**Config changes:** [new config keys, new env vars, default values]

If none: "No contract changes — internal implementation only."

## 9. Scale Considerations
[From scalability analysis — things the agent must get right for production]

- Email sending MUST be async. Enqueue to BullMQ at `packages/worker/`. Do NOT send in the request handler.
- User list queries MUST use cursor pagination. Follow the pattern in `src/server/routes/widgetRoutes.ts:paginated()`.
- [Any other scale-critical implementation details]

## 10. Verification (4-Level)

**Level 1: Unit tests pass**
```bash
[exact test command for this task's tests]
```
All [N] tests must pass. If any fail: read error, check against reference in Section 4, fix, re-run. Do not modify tests.

**Level 2: Integration wiring works**
```bash
[exact command to run the smoke test from Section 6]
```
This proves the full chain is connected: API → service → database → response. If this fails, your component is isolated — go back to Section 6 and wire it in.

**Level 3: No regressions**
```bash
[exact full test suite command]
```

**Level 4: Observability verification**
Verify every new/modified function has structured logging:
```bash
# Check that every new function has entry/exit/error logging
git diff --cached --name-only -- '*.py' | xargs grep -l "def " | while read f; do
  echo "=== $f ===" && grep -n "_LOG\.\(info\|error\|warning\)" "$f" | head -5
done
```
Every public function must have at least: started + completed OR error log events.

**Level 5: OWASP Security scan (HARD GUARDRAIL)**
Run ALL of these checks on every task. Not just security-tagged tasks — every task.
```bash
# A01: BROKEN ACCESS CONTROL — unauthenticated endpoints
git diff --cached | grep -E "def (get|post|put|delete|patch)_" | head -20
# For each new endpoint: verify auth decorator/middleware is applied

# A02: CRYPTOGRAPHIC FAILURES — plaintext secrets
git diff --cached | grep -E "os\.environ.*TOKEN|os\.getenv.*TOKEN|os\.environ.*KEY|os\.getenv.*KEY|os\.environ.*SECRET|os\.environ.*PASSWORD"
# Any match = FAIL. Must use credential vault.

# A03: INJECTION — command, SQL, path, prompt
git diff --cached | grep -E "subprocess\.(run|call|Popen|check_output).*shell=True"
git diff --cached | grep -E "(eval|exec)\("
git diff --cached | grep -E "f\".*SELECT|f\".*INSERT|f\".*UPDATE|f\".*DELETE"
# shell=True with external input = command injection
# f-string SQL = SQL injection (use parameterized queries)
# eval/exec = code injection

# A05: SECURITY MISCONFIGURATION — debug/verbose defaults
git diff --cached | grep -E "debug.*=.*True|verbose.*=.*True|DEBUG.*=.*1"
# Debug enabled by default = security misconfiguration

# A07: AUTH FAILURES — hardcoded credentials
git diff --cached | grep -E "password.*=.*\"|token.*=.*\"|api_key.*=.*\"|secret.*=.*\""
# Hardcoded credentials = critical finding

# A09: LOGGING FAILURES — secrets in logs
git diff --cached | grep -E "_LOG\.(info|error|warning|debug).*token|_LOG\.(info|error|warning|debug).*secret|_LOG\.(info|error|warning|debug).*password|_LOG\.(info|error|warning|debug).*key"
# Secrets in logs = SEC-001 class bug

# A10: SSRF — user-controlled URLs
git diff --cached | grep -E "httpx\.(get|post|put|delete)\(.*\burl\b"
# If URL comes from user input: verify allowlist enforcement
```
If ANY match: investigate before committing. These are not warnings — they are potential vulnerabilities that the OWASP threat model in the task spec should have mitigated. If the task spec doesn't address the finding, the task spec needs updating.

**Level 6: Anti-slop scan**
Before declaring done, search your changes for slop:
```bash
git diff --cached | grep -E "(TODO|FIXME|NotImplementedError|pass$|raise NotImplementedError|\.\.\.$)"
```
If any matches: fix them. No exceptions. Placeholders are not implementation.

**Level 6: Contract change verification**
If this task introduces contract changes:
```bash
# Verify new MCP tools are registered
grep -r "register_tool" src/mcp/ | grep "[new_tool_name]"
# Verify new config keys have defaults
grep -r "os.getenv\|config.get" src/ | grep "[new_key_name]"
# Verify new models have migrations
ls src/stores/migrations/ | grep "[new_table_name]"
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
- The scaffolded stubs (if they exist for this task)

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
2. Architecture Scaffolding (generates stubs)
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
        "description": "Paths to scaffolded stub files relevant to this task"
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
- [ ] Every assembled prompt includes the full reference implementation contents
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

## Framework Hardening Addendum

- **Contract versioning:** Inputs from Build Brief, repo map, scaffolding, and tests must include `contract_version` metadata.
- **Schema validation:** Validate assembled task payloads against `docs/schemas/build-brief.schema.json` task definitions and referenced schemas before prompt assembly.
- **Per-task token budget:** Enforce per-task budgets from `docs/specs/token-budgets.md` with pre-turn checks (`docs/specs/pre-turn-check.md`).
- **Compaction behavior:** When context approaches budget limits, apply transcript/context compaction from `docs/specs/transcript-compaction.md` while preserving acceptance criteria and wiring fields.
- **Stop reasons:** If assembly cannot proceed safely, emit structured stop reasons (`budget_exhausted`, `contract_mismatch`, `missing_dependency`).

