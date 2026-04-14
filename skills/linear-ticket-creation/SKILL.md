# Skill: Linear Ticket Creation

> Creates structured Linear issues from Build Brief task breakdowns. Produces cycle-aware tickets that preserve verifier contracts, dependencies, and execution context for coding agents.

---

## Trigger

Activated after the engineer approves the Build Brief. Consumes the schema-validated Build Brief, especially task breakdown, phased plan, and each task's applicability and verifier contract.

## Emitter Contract Alignment

This skill is a work-item emitter and must conform to [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md). Suppressed sections do not become filler ticket content. Every mutation requires `contract_version`, idempotency handling, and permission logging.

## Local MCP Model

ADLC does not ship a Linear client. This skill targets a locally installed MCP provider that can search, create, update, and relate Linear issues. Repo configuration resolves the provider name and binds the logical capabilities from the shared emitter contract to the provider's actual tool names.

## Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "linear_config": {
    "team_key": "string",
    "project_name": "string (created if missing)",
    "cycle_id": "string (optional)",
    "workflow_state_id": "string (optional)",
    "default_assignee": "string (optional)",
    "label_prefixes": {
      "area": "area:",
      "phase": "phase:"
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
  "applicability_manifest": {},
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

Every emitted issue must preserve the task's `task_classification`, `verification_spec`, `dependency_ids`, and any active overlay expectations from the brief's `applicability_manifest`.

## Output Contract

```json
{
  "contract_version": "1.0.0",
  "project": {
    "id": "string",
    "url": "string",
    "name": "string"
  },
  "issues": [
    {
      "id": "string",
      "identifier": "ENG-124",
      "url": "string",
      "title": "string",
      "area": "backend | frontend | infra | observability",
      "phase": 1,
      "assignee": "string (if provided)",
      "labels": ["area:backend", "phase:1", "parallelizable"],
      "linked_failure_modes": ["FM-001"],
      "idempotency_key": "BRF-123:linear:TASK-7:create"
    }
  ],
  "dependency_links": [
    {
      "from": "ENG-124",
      "to": "ENG-125",
      "type": "blocks | blocked_by | relates_to"
    }
  ],
  "summary": "string"
}
```

## Behavior

### 1. Resolve Project Context

- Use an existing Linear project when provided.
- Create the project when configured to do so and it does not exist.
- Attach phase-1 items to the active cycle when `cycle_id` is present.

### 2. Create Issues from Task Breakdown

For each task in the Build Brief task breakdown, create one Linear issue.

**Title format:** `[Area] [Verb] [Specific Deliverable]`

**Description template:**
```md
## Task
[Self-contained task description]

## Acceptance Criteria (Given/When/Then)
- Given ...
- When ...
- Then ...

## Architecture Pattern
- Follow: [pattern name]
- Reference implementation: [file path]

## Constraints
- Must:
- Must not:
- Escalate if:
- Task Classification: [feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security]

## Dependencies
- Depends on:
- Blocks:

## Verification Contract
- Primary verifier: [test | command | reproducer] — [target]
- Expected before change: fail
- Expected after change: pass
- Overlay checks: [only when active]

## Agent Instructions
- Files to modify:
- Files to create:
- Pattern to follow:
- Test file to update:

## Failure Modes
- [FM-ID] [description]

ADLC Idempotency Key: BRF-123:linear:TASK-7:create
```

### 3. Apply Linear Metadata

- Apply area, phase, and classification labels.
- Add `parallelizable` when the task has no unresolved dependencies.
- Set cycle, project, assignee, and workflow state only when configured.

### 4. Represent Dependencies

- Use native issue relations when supported by the workspace.
- Preserve dependency IDs in the description so issue relationships can be rebuilt deterministically.
- Keep dependency links in the output payload even when the target relation is a no-op.

### 5. Idempotency and Retry Behavior

- Compute an idempotency key per issue before mutation.
- Discover existing issues by stored ADLC metadata, not by fuzzy title matching.
- On retry, return the existing issue metadata and mark the result `deduplicated`.

### 6. Sync Behavior

If the Build Brief changes:
- Update matching issues for changed task IDs.
- Create issues for new task IDs.
- Move or relabel issues only when the phase mapping changes in the brief.
- Close or archive obsolete issues only with explicit operator approval.

## Required Local MCP Capabilities

ADLC expects a locally installed MCP provider. Provider tool names may differ; repo configuration maps them to the logical capability set. The payloads below are normalized examples, not a requirement that the provider expose these exact tool names.

### Logical operation: create work items from brief

```json
{
  "name": "create_linear_issues_from_brief",
  "description": "Create Linear issues from Build Brief task breakdown",
  "inputSchema": {
    "type": "object",
    "properties": {
      "contract_version": {
        "type": "string",
        "description": "Expected contract version range, e.g. 1.x"
      },
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown or Section 9 + Section 11"
      },
      "team_key": {
        "type": "string",
        "description": "Linear team key"
      },
      "project_name": {
        "type": "string",
        "description": "Linear project name"
      },
      "dry_run": {
        "type": "boolean",
        "default": true,
        "description": "If true, show the issue plan without creating issues"
      }
    },
    "required": ["contract_version", "build_brief", "team_key", "project_name"]
  }
}
```

### Logical operation: update work items from brief

```json
{
  "name": "update_linear_issues_from_brief",
  "description": "Sync existing Linear issues when the Build Brief changes",
  "inputSchema": {
    "type": "object",
    "properties": {
      "contract_version": {
        "type": "string",
        "description": "Expected contract version range, e.g. 1.x"
      },
      "build_brief": {
        "type": "string",
        "description": "Updated Build Brief markdown"
      },
      "team_key": {
        "type": "string",
        "description": "Linear team key"
      },
      "project_id": {
        "type": "string",
        "description": "Existing Linear project ID"
      }
    },
    "required": ["contract_version", "build_brief", "team_key", "project_id"]
  }
}
```

## Provider Resolution Example

```json
{
  "server_name": "linear-local-mcp",
  "capability_bindings": {
    "search_by_metadata": "issues.searchByMetadata",
    "upsert_parent_artifact": "projects.upsertProject",
    "upsert_artifact": "issues.upsertIssue",
    "apply_artifact_metadata": "issues.applyLabelsCycleAndState",
    "link_dependencies": "issues.linkDependency"
  }
}
```

## Quality Gates

- [ ] Every task in the Build Brief has a corresponding Linear issue.
- [ ] Issue bodies preserve `task_classification`, `verification_spec`, dependencies, and file targets.
- [ ] Phase and area metadata are represented with deterministic labels or fields.
- [ ] Configured local MCP provider exposes the required logical capability bindings.
- [ ] Retries deduplicate by stored ADLC metadata.
- [ ] Suppressed sections are omitted instead of rendered as filler.

## Framework Hardening Addendum

- **Contract versioning:** Require `contract_version` in input and output, with semver checks per `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate the Build Brief against `docs/schemas/build-brief.schema.json` before mutation.
- **Provider resolution:** Fail fast if the configured local MCP provider is missing required logical capabilities.
- **Idempotency:** Use durable idempotency keys and stored ADLC metadata to prevent duplicate issues.
- **Permission logging:** Emit structured approval and denial records for every create, update, or close mutation.
- **Stop reasons:** Return structured reasons when blocked by contract mismatch, permission denial, unavailable Linear MCP dependencies, or missing capability bindings.
