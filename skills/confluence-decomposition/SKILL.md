# Skill: Confluence Decomposition

> Decomposes a completed Build Brief into structured Confluence pages following the team's documentation hierarchy. Creates living docs that stay linked to JIRA tickets and runbooks.

---

## Trigger

Activated immediately on Build Brief completion. Consumes the full Build Brief markdown.

## Input Contract

```json
{
  "build_brief_markdown": "string (full Build Brief)",
  "confluence_config": {
    "space_key": "string",
    "parent_page_id": "string",
    "template_style": "adr | design_doc | runbook | default"
  },
  "jira_config": {
    "project_key": "string",
    "epic_key": "string (if already created)"
  },
  "owner": "string",
  "feature_name": "string"
}
```

Honor the Build Brief's `applicability_manifest` when decomposing pages. Suppressed sections stay omitted or explicitly marked "not applicable"; the skill must not fabricate security, observability, or performance pages for tasks that do not activate them.

## Output Contract

```json
{
  "pages_created": [
    {
      "page_id": "string",
      "title": "string",
      "url": "string",
      "type": "parent | architecture | risk | tasks | runbook | adr",
      "parent_page_id": "string"
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
│   └── Contains: active architecture/repo-finding sections + Mermaid diagram
├── Risk & Security Assessment
│   └── Contains: failure modes always, security analysis only when active
├── Operations & Observability
│   └── Contains: observability/SLO/incident ownership only when active
├── Implementation Plan
│   └── Contains: phased plan, task breakdown, verifier contracts
├── Decision Log
│   └── Contains: All Type 1/Type 2 decisions extracted from active sections
├── Open Questions & Blockers
│   └── Contains: unresolved items and suppressed-section rationale where needed
└── Runbook (created shell, populated by Incident Runbook Skill)
    └── Contains: incident ownership + failure mode roll-up when operational surfaces exist
```

### 2. Format for Confluence

- Convert Mermaid diagrams to Confluence macro format or embedded image
- Convert markdown tables to Confluence table markup
- Add Confluence status macros for decision status (Decided / Open / Blocked)
- Add JIRA issue macros linking to created tickets (if JIRA skill has run)
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
- Task page links to JIRA tickets (macro or URL)
- Runbook links to monitoring dashboards and alerting configs
- Each page has breadcrumb back to parent

### 5. Set Page Properties

- Add labels: feature name, team name, sprint, status
- Set page restrictions if security-sensitive content
- Add watchers: owner + escalation contact from brief

## MCP Server Contract

### Tool: `decompose_to_confluence`

```json
{
  "name": "decompose_to_confluence",
  "description": "Decompose a Build Brief into structured Confluence pages",
  "inputSchema": {
    "type": "object",
    "properties": {
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
    "required": ["build_brief", "space_key", "parent_page_id"]
  }
}
```

### Tool: `update_confluence_from_brief`

```json
{
  "name": "update_confluence_from_brief",
  "description": "Update existing Confluence pages when the Build Brief changes",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Updated Build Brief markdown"
      },
      "parent_page_id": {
        "type": "string",
        "description": "Existing parent page ID to update"
      }
    },
    "required": ["build_brief", "parent_page_id"]
  }
}
```

## CLI Interface

```bash
# Decompose brief to Confluence (dry run)
adlc-confluence decompose --brief ./build-brief.md --space ENG --parent 12345 --dry-run

# Create pages
adlc-confluence decompose --brief ./build-brief.md --space ENG --parent 12345

# Update existing pages from updated brief
adlc-confluence update --brief ./build-brief.md --parent 12345
```

## Quality Gates

- [ ] All active Build Brief sections have a corresponding Confluence page
- [ ] Mermaid diagrams render correctly in Confluence
- [ ] All Type 1 decisions are marked with warning macros
- [ ] JIRA links are valid (if tickets exist)
- [ ] Page hierarchy matches the defined structure
- [ ] Labels and watchers are set
- [ ] ADR created for architectural Type 1 decisions

## Framework Hardening Addendum

- **Contract versioning:** Section decomposition input/output contracts require `contract_version` and semver compatibility checks.
- **Schema validation:** Validate Build Brief structure against `docs/schemas/build-brief.schema.json` before decomposition.
- **Idempotency:** Page creation and updates must use idempotency keys and existence checks to avoid duplicate pages on retries.
- **Stop reasons:** Emit structured terminal reasons when blocked by contract mismatch, permission denial, or dependency failure.
