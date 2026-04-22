# Skill: JIRA Ticket Creation

> Creates structured JIRA tickets from Build Brief task breakdowns. Produces tickets with acceptance criteria, constraints, architecture pattern references, and linked failure modes that autonomous coding agents can execute against.

---

## Trigger

Activated after the engineer approves the Build Brief. Consumes the schema-validated Build Brief, especially task breakdown, phased plan, and each task's applicability/verifier contract.

## Emitter Contract Alignment

This skill is a work-item emitter and must conform to [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md). Suppressed sections do not become filler ticket content. Every mutation requires `contract_version`, idempotency handling, and permission logging.

## Local MCP Model

ADLC does not ship a JIRA client. This skill targets a locally installed MCP provider that can search, create, update, and relate JIRA artifacts. Repo configuration resolves the provider name and binds the logical capabilities from the shared emitter contract to the provider's actual tool names.

## Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "jira_config": {
    "project_key": "string",
    "epic_name": "string (created if not exists)",
    "sprint_id": "string (optional, for Phase 1 tasks)",
    "board_id": "string",
    "issue_type_mapping": {
      "backend": "Story | Task",
      "frontend": "Story | Task",
      "infra": "Task",
      "observability": "Task"
    }
  },
  "mcp_provider": {
    "server_name": "string",
    "capability_bindings": {
      "search_by_metadata": "string",
      "upsert_parent_artifact": "string",
      "upsert_artifact": "string",
      "apply_artifact_metadata": "string",
      "link_dependencies": "string (optional)"
    }
  },
  "task_breakdown": {
    "backend": [],
    "frontend": [],
    "infra": [],
    "observability": []
  },
  "phased_plan": {
    "phase_1": [],
    "phase_2": [],
    "phase_3": []
  },
  "architecture_patterns": {},
  "failure_modes": []
}
```

Every emitted ticket must preserve the task's `task_classification`, `verification_spec`, `reference_impl`, explicit reuse instructions, and any active overlay expectations from the brief's `applicability_manifest`. If the brief includes prerequisite debt-paydown work or deferred-cleanup notes, those must remain visible in the emitted ticket. Suppressed sections do not become filler ticket content. Unsupported claims and non-sequitur guardrail lines do not become ticket scope.

## Mixed Acceptance Criteria Shapes

Task acceptance criteria may arrive as strings or structured objects.

Extraction rules:
- If an item is an object, read its `.then` field for the visible acceptance-criteria text.
- If an item is a string, use the string directly.
- Preserve any upstream `id` and `measurable_post_condition` when present; do not flatten structured items into prose that loses them.

## Output Contract

```json
{
  "contract_version": "1.0.0",
  "epic": {
    "key": "PROJ-123",
    "url": "string",
    "title": "string"
  },
  "tickets": [
    {
      "key": "PROJ-124",
      "url": "string",
      "title": "string",
      "type": "Story | Task | Sub-task",
      "area": "backend | frontend | infra | observability",
      "phase": 1,
      "assignee": "string (if provided)",
      "story_points": "number",
      "linked_failure_modes": ["FM-001"],
      "idempotency_key": "BRF-123:jira:TASK-7:create",
      "sprint_id": "string (if Phase 1)"
    }
  ],
  "dependency_links": [
    {
      "from": "PROJ-124",
      "to": "PROJ-125",
      "type": "blocks | is_blocked_by | relates_to"
    }
  ],
  "summary": "string"
}
```

## Behavior

### 1. Create Epic

Create an epic for the feature:
- Title: `[Feature Name] - [Target First Slice Date]`
- Description: Build Brief Section 1 (What Changes) + link to the configured documentation parent page
- Labels: `adlc`, `[segment]`, `[phase]`
- Fix version: target release (if configured)

### 2. Create Tickets from Task Breakdown

For each task in the Build Brief task breakdown, create a ticket:

**Title format:** `[Area] [Verb] [Specific Deliverable]`
- Good: `[BE] Add POST /api/v1/widgets endpoint with validation`
- Bad: `Set up the API`

Emitter rules:
- Keep the first sentence concrete and behavior-first.
- Preserve positive invariants from the brief before negative bans.
- Do not emit defensive comparison lines unless they are grounded by the brief's contamination or prior-failure evidence.

**Description template:**
```
h2. Task
[Task description from brief — self-contained, no references to "the spec" or "as discussed". Lead with the user/system behavior that changes, then the architecture details.]

h2. Acceptance Criteria (Given/When/Then)
{panel:title=Done When}
* Given [precondition], When [action], Then [expected outcome]
* Given [precondition], When [action], Then [expected outcome]
* Given [precondition], When [action], Then [expected outcome]
{panel}

h2. Architecture Pattern
Follow: [pattern name] per [file path reference]
Reference implementation: [file path — the agent should study this file before coding]

h2. Reuse / Existing Patterns
* Reuse: [existing service/helper/pattern to extend]
* Do Not Reimplement: [existing helper/service/pattern that must not be duplicated]

h2. Constraints
* Must: [must do items]
* Must Not: [must not do items]
* Escalate If: [escalation triggers]
* Task Classification: [feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security]

h2. Tech Debt / Cleanup Boundaries
* Prerequisite debt: [blocking debt to pay down first, or "none"]
* Deferred debt: [allowed deferral with owner, or "none"]
* Why deferral is safe: [brief justification when deferred debt exists]

h2. Dependencies
* Depends on: [task IDs or "none — parallelizable"]
* Blocks: [task IDs or "none"]

h2. Verification Contract
* Primary verifier: [test | command | reproducer] — [target]
* Expected before change: fail
* Expected after change: pass
* Verifier phrasing: [feature = intended behavior; bugfix/build/lint = direct reproducer or command]
* Overlay checks: [security/observability/performance only when active]

h2. Agent Instructions
[Self-contained context — everything a coding agent needs to implement this task without searching]
* Files to modify: [explicit file paths]
* Files to create: [explicit file paths]
* Pattern to follow: [pattern name + reference file]
* Test file to update: [test file path]

h2. Failure Modes
|| ID || Failure || Likelihood || Prevention ||
| [FM-ID] | [description] | [L/M/H] | [prevention measure] |

h2. Estimated Hours
[X]h -- decompose into sub-tasks if > 2h

h2. Links
* Build Brief: [Confluence or Notion link]
* PRD: [link]
```

### 3. Map Tasks to Phases and Parallel Groups

- Phase 1 tasks: add to current sprint (if sprint_id provided), label `phase-1`
- Phase 2 tasks: label `phase-2`, add to backlog
- Phase 3 tasks: label `phase-3`, add to backlog

**Parallel execution groups:** Tasks flagged as `Parallel: Yes` with no dependencies between them are grouped and labeled `parallel-group-N`. This signals to coding agent orchestration that these tasks can be assigned to multiple agents simultaneously.

- Label independent tasks: `parallelizable`
- Create a JIRA board filter for parallel groups
- Add a comment to each parallelizable task: "This task has no dependencies and can be assigned to an independent coding agent."

### 4. Create Dependency Links

Analyze task descriptions and phase ordering to create JIRA links:
- Infra tasks that must complete before backend tasks: `blocks` relationship
- Backend tasks that must complete before frontend tasks: `blocks` relationship  
- Observability tasks that depend on backend endpoints: `is_blocked_by`
- Cross-cutting tasks: `relates_to`

### 5. Create Sub-tasks for Large Tasks

If estimated hours > 2h, decompose into sub-tasks:
- Each sub-task ≤ 2h
- Sub-tasks inherit the parent's acceptance criteria subset
- Sub-tasks inherit the parent's architecture pattern reference

### 6. Attach Failure Mode Cross-Reference

For each failure mode in the roll-up (Section 11):
- Find the task(s) that would prevent or detect it
- Add the failure mode ID to those tickets
- Create a linked "Risk" issue type if the failure mode is P0 or P1

### 7. Set Custom Fields (if configured)

| Field | Source | Value |
|-------|--------|-------|
| Decision Type | Phase 2 decisions | Type 1 / Type 2 |
| On-Call Rotation | Active observability/operations section | rotation name |
| Service Owner | Active observability/operations section | team name |
| Architecture Pattern | Section 2 | pattern name |
| SLO Target | Active observability/performance section | availability target |

## Mixed Acceptance Criteria Quality Gates

- [ ] Mixed acceptance-criteria handlers read `.then` from objects and raw text from strings
- [ ] Any acceptance-criteria `id` present upstream is preserved in the emitted ticket
- [ ] Any `measurable_post_condition` present upstream is preserved in the emitted ticket or linked metadata
- [ ] Verification contract fields survive decomposition without being weakened
- [ ] Reference implementations and explicit reuse instructions survive decomposition without being weakened
- [ ] Blocking or deferred tech-debt notes survive decomposition with sequencing context intact

## Required Local MCP Capabilities

ADLC expects a locally installed MCP provider. Provider tool names may differ; repo configuration maps them to the logical capability set. The payloads below are normalized examples, not a requirement that the provider expose these exact tool names.

### Logical operation: create work items from brief

```json
{
  "name": "create_tickets_from_brief",
  "description": "Create JIRA epic and tickets from Build Brief task breakdown",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown or Section 8 + Section 7"
      },
      "contract_version": {
        "type": "string",
        "description": "Expected contract version range, e.g. 1.x"
      },
      "project_key": {
        "type": "string",
        "description": "JIRA project key"
      },
      "sprint_id": {
        "type": "string",
        "description": "Sprint ID for Phase 1 tasks (optional)"
      },
      "dry_run": {
        "type": "boolean",
        "default": true,
        "description": "If true, show tickets without creating"
      }
    },
    "required": ["contract_version", "build_brief", "project_key"]
  }
}
```

### Logical operation: update work items from brief

```json
{
  "name": "sync_tickets_with_brief",
  "description": "Update existing JIRA tickets when the Build Brief changes",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Updated Build Brief markdown"
      },
      "contract_version": {
        "type": "string",
        "description": "Expected contract version range, e.g. 1.x"
      },
      "epic_key": {
        "type": "string",
        "description": "Existing JIRA epic key"
      }
    },
    "required": ["contract_version", "build_brief", "epic_key"]
  }
}
```

## Provider Resolution Example

```json
{
  "server_name": "jira-local-mcp",
  "capability_bindings": {
    "search_by_metadata": "issues.searchByMetadata",
    "upsert_parent_artifact": "issues.upsertEpic",
    "upsert_artifact": "issues.upsertIssue",
    "apply_artifact_metadata": "issues.applyBoardSprintAndLabels",
    "link_dependencies": "issues.linkDependency"
  }
}
```

## Quality Gates

- [ ] Every task in Section 8 has a corresponding JIRA ticket
- [ ] All tickets have acceptance criteria (not empty)
- [ ] All tickets reference an architecture pattern from Section 2
- [ ] Phase 1 tickets are in the sprint
- [ ] Dependency links exist between blocking tasks
- [ ] No ticket exceeds 2h estimate (decomposed into sub-tasks)
- [ ] Failure mode cross-references are linked
- [ ] Tickets preserve reference implementations, reuse rules, and debt-boundary notes from the brief
- [ ] Configured local MCP provider exposes the required logical capability bindings.
- [ ] Epic links to the configured documentation parent page

## Framework Hardening Addendum

- **Contract versioning:** Ticket input/output contracts include `contract_version` and compatibility checks.
- **Schema validation:** Validate incoming task payloads against `docs/schemas/build-brief.schema.json` before creating any issue.
- **Provider resolution:** Fail fast if the configured local MCP provider is missing required logical capabilities.
- **Idempotency:** Every issue create/update operation must include an idempotency key per `docs/specs/idempotency-keys.md`; retries must not create duplicates.
- **Permission logging:** Emit structured approval and denial records for every create, update, or close mutation.
- **Structured errors:** Return field-level validation, provider capability gaps, and upstream dependency failures in a typed error payload.
