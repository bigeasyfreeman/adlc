# Skill: JIRA Ticket Creation

> Creates structured JIRA tickets from Build Brief task breakdowns. Produces tickets with acceptance criteria, constraints, architecture pattern references, and linked failure modes that autonomous coding agents can execute against.

---

## Trigger

Activated after the engineer approves the Build Brief. Consumes Section 8 (Task Breakdown) and Section 7 (Phased Plan).

## Input Contract

```json
{
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

## Output Contract

```json
{
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
- Description: Build Brief Section 1 (What Changes) + link to Confluence parent page
- Labels: `adlc`, `[segment]`, `[phase]`
- Fix version: target release (if configured)

### 2. Create Tickets from Task Breakdown

For each task in Section 8, create a ticket:

**Title format:** `[Area] [Verb] [Specific Deliverable]`
- Good: `[BE] Add POST /api/v1/widgets endpoint with validation`
- Bad: `Set up the API`

**Description template:**
```
h2. Task
[Task description from brief — self-contained, no references to "the spec" or "as discussed"]

h2. Acceptance Criteria (Given/When/Then)
{panel:title=Done When}
* Given [precondition], When [action], Then [expected outcome]
* Given [precondition], When [action], Then [expected outcome]
* Given [precondition], When [action], Then [expected outcome]
{panel}

h2. Architecture Pattern
Follow: [pattern name] per [file path reference]
Reference implementation: [file path — the agent should study this file before coding]

h2. Constraints
* Must: [must do items]
* Must Not: [must not do items]
* Escalate If: [escalation triggers]

h2. Dependencies
* Depends on: [task IDs or "none — parallelizable"]
* Blocks: [task IDs or "none"]

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
* Build Brief: [Confluence link]
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
| On-Call Rotation | Section 6 | rotation name |
| Service Owner | Section 6 | team name |
| Architecture Pattern | Section 2 | pattern name |
| SLO Target | Section 6 | availability target |

## MCP Server Contract

### Tool: `create_tickets_from_brief`

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
    "required": ["build_brief", "project_key"]
  }
}
```

### Tool: `sync_tickets_with_brief`

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
      "epic_key": {
        "type": "string",
        "description": "Existing JIRA epic key"
      }
    },
    "required": ["build_brief", "epic_key"]
  }
}
```

## CLI Interface

```bash
# Preview tickets from build brief
adlc-jira create --brief ./build-brief.md --project ENG --dry-run

# Create tickets
adlc-jira create --brief ./build-brief.md --project ENG --sprint 42

# Sync updated brief to existing tickets
adlc-jira sync --brief ./build-brief.md --epic ENG-123
```

## Quality Gates

- [ ] Every task in Section 8 has a corresponding JIRA ticket
- [ ] All tickets have acceptance criteria (not empty)
- [ ] All tickets reference an architecture pattern from Section 2
- [ ] Phase 1 tickets are in the sprint
- [ ] Dependency links exist between blocking tasks
- [ ] No ticket exceeds 2h estimate (decomposed into sub-tasks)
- [ ] Failure mode cross-references are linked
- [ ] Epic links to Confluence parent page

## Framework Hardening Addendum

- **Contract versioning:** Ticket input/output contracts include `contract_version` and compatibility checks.
- **Schema validation:** Validate incoming task payloads against `docs/schemas/build-brief.schema.json` before creating any issue.
- **Idempotency:** Every issue create/update operation must include an idempotency key per `docs/specs/idempotency-keys.md`; retries must not create duplicates.
- **Structured errors:** Return field-level validation and upstream dependency failures in a typed error payload.

