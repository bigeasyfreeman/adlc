# Emitter Contract

## Purpose

Define the shared contract for any ADLC skill that publishes Build Brief output into an external system. This keeps work-item and documentation emitters swappable without changing the Build Brief schema or downstream execution expectations.

## Emitter Families

| Family | Skills | Output |
|---|---|---|
| Work-item emitter | `jira-ticket-creation`, `github-issue-creation`, `linear-ticket-creation` | Executable tickets or issues |
| Document emitter | `confluence-decomposition`, `notion-decomposition` | Structured design or runbook pages |

Every emitter is a `pr_prep`-phase mutating skill. Every emitter must preserve the Build Brief's applicability-aware shape and must not invent sections the brief suppressed.

## Local MCP Provider Model

ADLC owns the normalized emitter payloads, verification rules, idempotency, and permission semantics. It does **not** ship vendor SDK clients, session managers, or transport-specific integrations for GitHub, Linear, Notion, JIRA, or Confluence.

Each emitter resolves a locally installed MCP provider that is responsible for:

- authentication and session state
- vendor API transport
- object lookup and mutation
- provider-specific tool naming

Repo configuration binds ADLC's logical emitter capabilities to whatever tool names the local MCP provider exposes.

## Shared Input Contract

```json
{
  "contract_version": "1.x",
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "applicability_manifest": {
    "task_classification": "feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security"
  },
  "task_breakdown": {},
  "phased_plan": {},
  "architecture_patterns": {},
  "failure_modes": [],
  "mcp_provider": {
    "server_name": "string",
    "capability_bindings": {
      "search_by_metadata": "string",
      "upsert_parent_artifact": "string",
      "upsert_artifact": "string"
    }
  },
  "artifact_config": {
    "target": "jira | github | linear | confluence | notion"
  }
}
```

## Shared Work-Item Output Contract

```json
{
  "contract_version": "1.0.0",
  "target": "jira | github | linear",
  "parent_artifact": {
    "id": "string",
    "title": "string",
    "url": "string"
  },
  "artifacts": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "area": "backend | frontend | infra | observability",
      "phase": 1,
      "linked_failure_modes": ["FM-001"],
      "idempotency_key": "string"
    }
  ],
  "dependency_links": [],
  "summary": "string"
}
```

## Shared Document Output Contract

```json
{
  "contract_version": "1.0.0",
  "target": "confluence | notion",
  "pages_created": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "type": "parent | architecture | risk | tasks | runbook | adr",
      "parent_id": "string"
    }
  ],
  "database_entries": [],
  "summary": "string"
}
```

## Required Task Preservation

Every work-item emitter must carry these fields forward from the Build Brief task:

- `task_classification`
- `verification_spec`
- acceptance criteria or Given/When/Then contract
- `dependencies`
- `reference_impl`
- reuse or extend instructions, including any explicit "do not reimplement" guidance
- `files_to_create` and `files_to_modify`
- failure-mode cross references
- prerequisite debt-paydown tasks or deferred-cleanup notes when present
- explicit out-of-scope or escalation notes when present

Every document emitter must preserve:

- active Build Brief sections only
- architecture and reuse guidance, including reference implementations when the brief names them
- failure mode roll-up
- decision log and open questions
- task breakdown and verifier contract
- tech-debt paydown, sequencing, or deferral notes when the brief includes them
- suppressed-section rationale where omission could look accidental

## Logical Capability Sets

### Work-Item Emitters

Required logical capabilities:

- `search_by_metadata`
- `upsert_parent_artifact`
- `upsert_artifact`
- `apply_artifact_metadata`
- `link_dependencies` when the target system supports relations

Optional logical capabilities:

- `close_artifact`
- `attach_to_project_or_milestone`

### Document Emitters

Required logical capabilities:

- `search_by_metadata`
- `upsert_artifact`

Optional logical capabilities:

- `upsert_database_entry`
- `link_artifacts`
- `archive_artifact`

## Target Config Extensions

| Target | Platform-specific config |
|---|---|
| JIRA | project key, epic metadata, sprint or board info, issue type mapping |
| GitHub | repository, tracking issue or milestone config, label mapping, optional project placement |
| Linear | team key, project or cycle config, workflow state mapping, label mapping |
| Confluence | space key, parent page, template style |
| Notion | parent page, page or database targets, template style |

Platform-specific config may extend the shared contract, but it must not redefine the meaning of the Build Brief task fields or the logical MCP capability set.

## Required Behavior

1. Resolve the configured local MCP provider and verify the required logical capabilities are bound.
2. Validate the Build Brief against `docs/schemas/build-brief.schema.json` before mutation.
3. Validate `contract_version` using `docs/specs/skill-contract-versioning.md`.
4. Preserve the applicability manifest. Suppressed sections stay omitted or marked not applicable.
4.5. Preserve reuse and debt context. Do not collapse reference implementations, "do not reimplement" rules, or prerequisite paydown tasks into generic prose.
5. Compute per-artifact idempotency keys before any external mutation.
6. Emit permission logging entries before and after every mutating external action.
7. Return created artifact metadata and dedupe status in a structured response.
8. Surface structured stop reasons on contract mismatch, permission denial, provider capability gaps, or dependency failure.

## Idempotency and Permission Logging

- Key format is defined in [docs/specs/idempotency-keys.md](/Users/eric/adlc/docs/specs/idempotency-keys.md).
- Permission log shape is defined in [docs/specs/permission-logging.md](/Users/eric/adlc/docs/specs/permission-logging.md).
- Retries must return prior artifact metadata when the key is already terminal.

## Stop Reasons

Emitters must stop with one of:

- `contract_version_incompatible`
- `schema_validation_failed`
- `permission_denied`
- `provider_capability_missing`
- `dependency_unavailable`
- `external_mutation_partial`

## Verification Expectations

- Work-item emitters are verified by artifact template completeness and field preservation.
- Document emitters are verified by section coverage, hierarchy correctness, and applicability-manifest fidelity.
- No emitter may pass by publishing placeholder titles, empty sections, tickets lacking verifier contracts, or artifacts that drop reuse/debt constraints from the brief.
