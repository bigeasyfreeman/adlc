# Skill: Notion Decomposition

> Decomposes a completed Build Brief into structured Notion pages and optional task database entries. Creates living docs that stay linked to work-item emitters, runbooks, and decision logs.

---

## Trigger

Activated immediately on Build Brief completion. Consumes the full Build Brief markdown.

## Emitter Contract Alignment

This skill is a document emitter and must conform to [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md). Honor the Build Brief's `applicability_manifest`; suppressed sections stay omitted or explicitly marked not applicable. Every mutation requires `contract_version`, idempotency handling, and permission logging.

## Local MCP Model

ADLC does not ship a Notion client. This skill targets a locally installed MCP provider that can search, create, update, and relate Notion pages or database entries. Repo configuration resolves the provider name and binds the logical capabilities from the shared emitter contract to the provider's actual tool names.

## Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_markdown": "string (full Build Brief)",
  "notion_config": {
    "parent_page_id": "string",
    "template_style": "design_doc | runbook | default",
    "docs_database_id": "string (optional)",
    "tasks_database_id": "string (optional)"
  },
  "mcp_provider": {
    "server_name": "string",
    "capability_bindings": {
      "search_by_metadata": "string",
      "upsert_artifact": "string",
      "upsert_database_entry": "string (optional)",
      "link_artifacts": "string (optional)"
    }
  },
  "work_item_links": {
    "target": "jira | github | linear",
    "parent_url": "string (optional)"
  },
  "owner": "string",
  "feature_name": "string",
  "applicability_manifest": {}
}
```

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
      "parent_page_id": "string"
    }
  ],
  "database_entries": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "kind": "task | decision | question",
      "idempotency_key": "BRF-123:notion:tasks:TASK-7:create"
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

```text
[Feature Name] -- Design Doc (parent page)
├── Architecture & Patterns
├── Risk & Security Assessment
├── Operations & Observability (only when active)
├── Implementation Plan
├── Decision Log
├── Open Questions & Blockers
└── Runbook (created shell when operational surfaces exist)
```

### 2. Format for Notion

- Use callout blocks for warnings, blocked items, and out-of-scope notes.
- Use tables or database views for task breakdowns and failure mode roll-ups.
- Preserve code fences, Mermaid source, and file-path references as plain content when native rendering is unavailable.
- Add backlinks to work-item artifacts when GitHub, JIRA, or Linear links exist.

### 3. Respect Applicability Manifest

- Include active Build Brief sections only.
- Omit suppressed sections or add a short "Not applicable for this brief" note when omission could be ambiguous.
- Do not fabricate security, observability, or performance pages when the corresponding overlay is suppressed.

### 4. Create Optional Database Entries

If `tasks_database_id` is provided:
- Create one task database entry per Build Brief task.
- Preserve `task_classification`, `verification_spec`, dependencies, and failure modes in properties or structured content.
- Link each task entry back to the matching work-item artifact when provided.

### 5. Link Pages

- Parent page links to all child pages.
- Task page links to the configured work-item artifacts.
- Runbook links to dashboards, alerts, and incident owners when those surfaces exist.
- Decision log links to the relevant architecture or task sections.

### 6. Idempotency and Retry Behavior

- Compute an idempotency key per page or database entry before mutation.
- Discover existing pages or entries by stored ADLC metadata, not fuzzy title matching alone.
- On retry, return the existing artifact metadata and mark the result `deduplicated`.

## Required Local MCP Capabilities

ADLC expects a locally installed MCP provider. Provider tool names may differ; repo configuration maps them to the logical capability set. The payloads below are normalized examples, not a requirement that the provider expose these exact tool names.

### Logical operation: create document artifacts from brief

```json
{
  "name": "decompose_to_notion",
  "description": "Decompose a Build Brief into structured Notion pages",
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
      "parent_page_id": {
        "type": "string",
        "description": "Parent Notion page ID"
      },
      "dry_run": {
        "type": "boolean",
        "default": true,
        "description": "If true, show page structure without creating"
      }
    },
    "required": ["contract_version", "build_brief", "parent_page_id"]
  }
}
```

### Logical operation: update document artifacts from brief

```json
{
  "name": "update_notion_from_brief",
  "description": "Update existing Notion pages when the Build Brief changes",
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
  "server_name": "notion-local-mcp",
  "capability_bindings": {
    "search_by_metadata": "pages.searchByMetadata",
    "upsert_artifact": "pages.upsertPage",
    "upsert_database_entry": "databases.upsertRow",
    "link_artifacts": "pages.appendBacklinks"
  }
}
```

## Quality Gates

- [ ] All active Build Brief sections have a corresponding Notion page or block area.
- [ ] Suppressed sections are omitted or explicitly marked not applicable.
- [ ] Task database entries preserve verifier contracts when a task database is configured.
- [ ] Work-item backlinks are valid when provided.
- [ ] Configured local MCP provider exposes the required logical capability bindings.
- [ ] Retries deduplicate by stored ADLC metadata.

## Framework Hardening Addendum

- **Contract versioning:** Require `contract_version` in input and output, with semver checks per `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate the Build Brief against `docs/schemas/build-brief.schema.json` before mutation.
- **Provider resolution:** Fail fast if the configured local MCP provider is missing required logical capabilities.
- **Idempotency:** Use durable idempotency keys and stored ADLC metadata to prevent duplicate pages or database items.
- **Permission logging:** Emit structured approval and denial records for every create or update mutation.
- **Stop reasons:** Return structured reasons when blocked by contract mismatch, permission denial, unavailable Notion MCP dependencies, or missing capability bindings.
