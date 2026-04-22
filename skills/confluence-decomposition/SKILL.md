# Skill: Confluence Decomposition

> Decomposes a completed Build Brief into structured Confluence pages following the team's documentation hierarchy. Creates living docs that stay linked to JIRA tickets and runbooks.

---

## Trigger

Activated immediately on Build Brief completion. Consumes the full Build Brief markdown.

## Emitter Contract Alignment

This skill is a document emitter and must conform to [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md). Honor the Build Brief's `applicability_manifest`; suppressed sections stay omitted or explicitly marked not applicable. Every mutation requires `contract_version`, idempotency handling, and permission logging.

## Local MCP Model

ADLC does not ship a Confluence client. This skill targets a locally installed MCP provider that can search, create, update, and relate Confluence pages. Repo configuration resolves the provider name and binds the logical capabilities from the shared emitter contract to the provider's actual tool names.

## Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_markdown": "string (full Build Brief)",
  "confluence_config": {
    "space_key": "string",
    "parent_page_id": "string",
    "template_style": "adr | design_doc | runbook | default"
  },
  "mcp_provider": {
    "server_name": "string",
    "capability_bindings": {
      "search_by_metadata": "string",
      "upsert_artifact": "string",
      "link_artifacts": "string (optional)"
    }
  },
  "jira_config": {
    "project_key": "string",
    "epic_key": "string (if already created)"
  },
  "owner": "string",
  "feature_name": "string"
}
```

Honor the Build Brief's `applicability_manifest` when decomposing pages. Suppressed sections stay omitted or explicitly marked "not applicable"; the skill must not fabricate security, observability, or performance pages for tasks that do not activate them. Preserve explicit reuse tables, reference implementations, and tech-debt sequencing notes from the brief; those are execution constraints, not optional narrative flavor.

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
  "pages_created": [
    {
      "page_id": "string",
      "title": "string",
      "url": "string",
      "type": "parent | architecture | risk | tasks | runbook | adr",
      "parent_page_id": "string",
      "idempotency_key": "BRF-123:confluence:architecture:create"
    }
  ],
  "links": {
    "parent_page": "url",
    "architecture_page": "url",
    "risk_page": "url",
    "task_page": "url",
    "runbook_page": "url"
  },
  "summary": "string"
}
```

## Behavior

### 1. Create Page Hierarchy

Decompose the Build Brief into this page structure:

```
[Feature Name] -- Design Doc (parent page)
├── Architecture & Patterns
│   └── Contains: active architecture/repo-finding sections + Mermaid diagram + reuse/reference-implementation guidance
├── Risk & Security Assessment
│   └── Contains: failure modes always, security analysis only when active
├── Operations & Observability
│   └── Contains: observability/SLO/incident ownership only when active
├── Implementation Plan
│   └── Contains: phased plan, task breakdown, verifier contracts, and debt-prerequisite sequencing
├── Decision Log
│   └── Contains: All Type 1/Type 2 decisions extracted from active sections
├── Open Questions & Blockers
│   └── Contains: unresolved items, deferred tech debt with owners, and suppressed-section rationale where needed
└── Runbook (created shell, populated by Incident Runbook Skill)
    └── Contains: incident ownership + failure mode roll-up when operational surfaces exist
```

### 2. Format for Confluence

- Convert Mermaid diagrams to Confluence macro format or embedded image
- Convert markdown tables to Confluence table markup
- Add Confluence status macros for decision status (Decided / Open / Blocked)
- Add work-item links for created tickets or issues (JIRA, GitHub, or Linear)
- Add `info`, `warning`, and `expand` macros where appropriate:
  - `warning` for unresolved Type 1 decisions
  - `info` for out-of-scope items
  - `expand` for failure mode detail tables

### 3. Create ADR (if architectural decisions made)

If Phase 2 (Architecture Patterns) contains any Type 1 decisions, create an ADR page:

```
ADR-[number]: [Decision Title]

Status: [Proposed | Accepted | Deprecated]
Date: [YYYY-MM-DD]
Deciders: [names]

Context: [Why this decision was needed]
Decision: [What was decided]
Consequences: [What changes as a result]
Alternatives Considered: [What was rejected and why]
```

### 4. Link Pages

- Parent page links to all child pages
- Decision Log links to relevant sections
- Task page links to created work-item artifacts
- Runbook links to monitoring dashboards and alerting configs
- Each page has breadcrumb back to parent

### 5. Set Page Properties

- Add labels: feature name, team name, sprint, status
- Set page restrictions if security-sensitive content
- Add watchers: owner + escalation contact from brief

## Required Local MCP Capabilities

ADLC expects a locally installed MCP provider. Provider tool names may differ; repo configuration maps them to the logical capability set. The payloads below are normalized examples, not a requirement that the provider expose these exact tool names.

### Logical operation: create document artifacts from brief

```json
{
  "name": "decompose_to_confluence",
  "description": "Decompose a Build Brief into structured Confluence pages",
  "inputSchema": {
    "type": "object",
    "properties": {
      "contract_version": {
        "type": "string",
        "description": "Expected contract version range, e.g. 1.x"
      },
      "build_brief": {
        "type": "string",
        "description": "Full Build Brief markdown content"
      },
      "space_key": {
        "type": "string",
        "description": "Confluence space key"
      },
      "parent_page_id": {
        "type": "string",
        "description": "Parent page ID to nest under"
      },
      "dry_run": {
        "type": "boolean",
        "default": true,
        "description": "If true, show page structure without creating"
      }
    },
    "required": ["contract_version", "build_brief", "space_key", "parent_page_id"]
  }
}
```

### Logical operation: update document artifacts from brief

```json
{
  "name": "update_confluence_from_brief",
  "description": "Update existing Confluence pages when the Build Brief changes",
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
      "parent_page_id": {
        "type": "string",
        "description": "Existing parent page ID to update"
      }
    },
    "required": ["contract_version", "build_brief", "parent_page_id"]
  }
}
```

## Provider Resolution Example

```json
{
  "server_name": "confluence-local-mcp",
  "capability_bindings": {
    "search_by_metadata": "pages.searchByMetadata",
    "upsert_artifact": "pages.upsertPage",
    "link_artifacts": "pages.appendBacklinks"
  }
}
```

## Quality Gates

- [ ] All active Build Brief sections have a corresponding Confluence page
- [ ] Mixed acceptance-criteria handlers read `.then` from objects and raw text from strings
- [ ] Any acceptance-criteria `id` present upstream is preserved in the emitted Confluence content
- [ ] Any `measurable_post_condition` present upstream is preserved in the emitted Confluence content
- [ ] Reference implementations and explicit reuse instructions survive decomposition without being reduced to generic prose
- [ ] Blocking or deferred tech-debt notes survive decomposition with sequencing or owner context intact
- [ ] Mermaid diagrams render correctly in Confluence
- [ ] All Type 1 decisions are marked with warning macros
- [ ] JIRA links are valid (if tickets exist)
- [ ] Page hierarchy matches the defined structure
- [ ] Labels and watchers are set
- [ ] ADR created for architectural Type 1 decisions
- [ ] Configured local MCP provider exposes the required logical capability bindings.

## Framework Hardening Addendum

- **Contract versioning:** Section decomposition input/output contracts require `contract_version` and semver compatibility checks.
- **Schema validation:** Validate Build Brief structure against `docs/schemas/build-brief.schema.json` before decomposition.
- **Provider resolution:** Fail fast if the configured local MCP provider is missing required logical capabilities.
- **Idempotency:** Page creation and updates must use idempotency keys and existence checks to avoid duplicate pages on retries.
- **Permission logging:** Emit structured approval and denial records for every create or update mutation.
- **Stop reasons:** Emit structured terminal reasons when blocked by contract mismatch, permission denial, unavailable Confluence MCP dependencies, or missing capability bindings.
