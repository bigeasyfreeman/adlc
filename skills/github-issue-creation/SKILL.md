# Skill: GitHub Issue Creation

> Creates structured GitHub tracking issues and task issues from Build Brief task breakdowns. Produces issue bodies that preserve verifier contracts, dependencies, and execution context for coding agents.

---

## Trigger

Activated after the engineer approves the Build Brief. Consumes the schema-validated Build Brief, especially task breakdown, phased plan, and each task's applicability and verifier contract.

## Emitter Contract Alignment

This skill is a work-item emitter and must conform to [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md). Suppressed sections do not become filler issue content. Every mutation requires `contract_version`, idempotency handling, and permission logging.

## Local MCP Model

ADLC does not ship a GitHub client. This skill targets a locally installed MCP provider that can search, create, update, and relate GitHub issues. Repo configuration resolves the provider name and binds the logical capabilities from the shared emitter contract to the provider's actual tool names.

## Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "github_config": {
    "repository": "owner/name",
    "tracking_issue_title": "string (created if missing)",
    "milestone_title": "string (optional)",
    "project_number": "number (optional)",
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

Every emitted issue must preserve the task's `task_classification`, `verification_spec`, `dependency_ids`, `reference_impl`, explicit reuse instructions, and any active overlay expectations from the brief's `applicability_manifest`. If the brief includes prerequisite debt-paydown work or deferred-cleanup notes, those must remain visible in the emitted issue. Unsupported claims and non-sequitur guardrail lines do not become issue scope.

## Output Contract

```json
{
  "contract_version": "1.0.0",
  "tracking_issue": {
    "number": 123,
    "url": "string",
    "title": "string"
  },
  "issues": [
    {
      "number": 124,
      "url": "string",
      "title": "string",
      "area": "backend | frontend | infra | observability",
      "phase": 1,
      "assignee": "string (if provided)",
      "labels": ["area:backend", "phase:1", "parallelizable"],
      "linked_failure_modes": ["FM-001"],
      "idempotency_key": "BRF-123:github:TASK-7:create"
    }
  ],
  "dependency_links": [
    {
      "from": 124,
      "to": 125,
      "type": "blocks | blocked_by | relates_to"
    }
  ],
  "summary": "string"
}
```

## Behavior

### 1. Create or Update Tracking Issue

Create a tracking issue for the feature:
- Title: `[Feature] Tracking`
- Body: Build Brief overview, phase summary, and task checklist
- Metadata: hidden footer containing build brief ID and idempotency keys
- Labels: `adlc`, area-neutral feature labels, optional milestone/project placement

### 2. Create Issues from Task Breakdown

For each task in the Build Brief task breakdown, create one GitHub issue.

**Title format:** `[Area] [Verb] [Specific Deliverable]`

Emitter rules:
- Keep the first sentence concrete and behavior-first.
- Preserve positive invariants from the brief before negative bans.
- Do not emit defensive comparison lines unless they are grounded by the brief's contamination or prior-failure evidence.

**Body template:**
```md
## Task
[Self-contained task description. Lead with the user/system behavior that changes, then the architecture details.]

## Acceptance Criteria (Given/When/Then)
- Given ...
- When ...
- Then ...

## Architecture Pattern
- Follow: [pattern name]
- Reference implementation: [file path]

## Reuse / Existing Patterns
- Reuse: [existing service/helper/pattern to extend]
- Do Not Reimplement: [existing helper/service/pattern that must not be duplicated]

## Constraints
- Must:
- Must not:
- Escalate if:
- Task Classification: [feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security]

## Tech Debt / Cleanup Boundaries
- Prerequisite debt: [blocking debt to pay down first, or "none"]
- Deferred debt: [allowed deferral with owner, or "none"]
- Why deferral is safe: [brief justification when deferred debt exists]

## Dependencies
- Depends on:
- Blocks:

## Verification Contract
- Primary verifier: [test | command | reproducer] — [target]
- Expected before change: fail
- Expected after change: pass
- Verifier phrasing: [feature = intended behavior; bugfix/build/lint = direct reproducer or command]
- Overlay checks: [only when active]

## Agent Instructions
- Files to modify:
- Files to create:
- Pattern to follow:
- Test file to update:

## Failure Modes
- [FM-ID] [description]

<!-- adlc:brief_id=BRF-123 -->
<!-- adlc:idempotency_key=BRF-123:github:TASK-7:create -->
```

### 3. Apply GitHub Metadata

- Apply area, phase, and classification labels.
- Add `parallelizable` when the task has no unresolved dependencies.
- Attach issues to the configured milestone or project when provided.
- Preserve assignee only when the brief or config explicitly sets one.

### 4. Represent Dependencies

- Record dependency edges in the tracking issue checklist or dependency table.
- When supported by the target workflow, add issue relationships.
- Always preserve dependency IDs in the issue body so relation sync is recoverable.

### 5. Idempotency and Retry Behavior

- Compute an idempotency key per issue before mutation.
- Discover existing issues by hidden metadata footer, not by fuzzy title matching.
- On retry, return the existing issue metadata and mark the result `deduplicated`.

### 6. Sync Behavior

If the Build Brief changes:
- Update only matching issues for changed task IDs.
- Create issues for new task IDs.
- Close or mark obsolete issues only when the brief explicitly removes the task and the operator approves the mutation.

## Required Local MCP Capabilities

ADLC expects a locally installed MCP provider. Provider tool names may differ; repo configuration maps them to the logical capability set. The payloads below are normalized examples, not a requirement that the provider expose these exact tool names.

### Logical operation: create work items from brief

```json
{
  "name": "create_github_issues_from_brief",
  "description": "Create a GitHub tracking issue and task issues from Build Brief task breakdown",
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
      "repository": {
        "type": "string",
        "description": "GitHub repository in owner/name form"
      },
      "tracking_issue_title": {
        "type": "string",
        "description": "Tracking issue title"
      },
      "dry_run": {
        "type": "boolean",
        "default": true,
        "description": "If true, show the issue plan without creating issues"
      }
    },
    "required": ["contract_version", "build_brief", "repository", "tracking_issue_title"]
  }
}
```

### Logical operation: update work items from brief

```json
{
  "name": "update_github_issues_from_brief",
  "description": "Sync existing GitHub issues when the Build Brief changes",
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
      "repository": {
        "type": "string",
        "description": "GitHub repository in owner/name form"
      },
      "tracking_issue_number": {
        "type": "integer",
        "description": "Existing tracking issue number"
      }
    },
    "required": ["contract_version", "build_brief", "repository", "tracking_issue_number"]
  }
}
```

## Provider Resolution Example

```json
{
  "server_name": "github-local-mcp",
  "capability_bindings": {
    "search_by_metadata": "issues.searchByMetadata",
    "upsert_parent_artifact": "issues.upsertTrackingIssue",
    "upsert_artifact": "issues.upsertIssue",
    "apply_artifact_metadata": "issues.applyLabelsAndProject",
    "link_dependencies": "issues.linkDependency"
  }
}
```

## Quality Gates

- [ ] Every task in the Build Brief has a corresponding GitHub issue.
- [ ] Issue bodies preserve `task_classification`, `verification_spec`, dependencies, file targets, reference implementations, and reuse/debt context.
- [ ] Tracking issue contains a phase-ordered task view.
- [ ] Configured local MCP provider exposes the required logical capability bindings.
- [ ] Retries deduplicate by idempotency metadata.
- [ ] Suppressed sections are omitted instead of rendered as filler.

## Framework Hardening Addendum

- **Contract versioning:** Require `contract_version` in input and output, with semver checks per `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate the Build Brief against `docs/schemas/build-brief.schema.json` before mutation.
- **Provider resolution:** Fail fast if the configured local MCP provider is missing required logical capabilities.
- **Idempotency:** Use durable idempotency keys and metadata footer lookup to prevent duplicate issues.
- **Permission logging:** Emit structured approval and denial records for every create, update, or close mutation.
- **Stop reasons:** Return structured reasons when blocked by contract mismatch, permission denial, unavailable GitHub MCP dependencies, or missing capability bindings.
