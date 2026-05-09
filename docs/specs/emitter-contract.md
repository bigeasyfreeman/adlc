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
  "adlc_mode": "prd_only | decompose_only | prd_and_decompose",
  "build_brief_id": "string",
  "feature_name": "string",
  "owner": "string",
  "applicability_manifest": {
    "task_classification": "feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security"
  },
  "task_breakdown": {},
  "phased_plan": {},
  "architecture_patterns": {},
  "enterprise_readiness_contract": {
    "production_grade_target": "string",
    "backward_compatibility": "string",
    "forward_compatibility": "string",
    "failure_mode_coverage": [],
    "definition_of_done": [],
    "validation_tasks": [],
    "compliance_posture": "string"
  },
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
      "artifact_type": "scope_lock_epic | decision_gate | implementation_task | validation_task",
      "executable": true,
      "blocks_implementation": false,
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

- `artifact_type`
- `task_classification`
- `work_item_metadata` when present (`area`, `area_label`, `phase_label`, `target_project`, `labels`, `external_refs`)
- `decision_contract`
- `verification_spec`
- acceptance criteria or Given/When/Then contract
- `dependencies`
- `reference_impl`
- reuse or extend instructions, including any explicit "do not reimplement" guidance
- `files_to_create` and `files_to_modify`
- `tech_debt_boundaries`
- `compatibility_contract`
- `evidence_responsibilities`
- `definition_of_done`
- failure-mode cross references
- prerequisite debt-paydown tasks or deferred-cleanup notes when present
- explicit out-of-scope or escalation notes when present
- the top-level `enterprise_readiness_contract`

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
4.6. Preserve artifact taxonomy. `scope_lock_epic` artifacts are parent/context artifacts only, `decision_gate` artifacts block implementation, `implementation_task` artifacts are executable coding work, and `validation_task` artifacts own evidence capture and final readiness proof.
4.7. Reject unresolved dependency aliases before mutation. Every dependency must resolve to a Build Brief artifact ID or an already-emitted target artifact ID.
4.8. Ensure decomposition-mode payloads include automatic validation tasks in the enterprise readiness contract, and emit those validation tasks as first-class work items when the target supports work-item artifacts.
5. Compute per-artifact idempotency keys before any external mutation.
6. Emit permission logging entries before and after every mutating external action.
7. Return created artifact metadata and dedupe status in a structured response.
8. Surface structured stop reasons on contract mismatch, permission denial, provider capability gaps, or dependency failure.

## Idempotency and Permission Logging

- Key format is defined in [docs/specs/idempotency-keys.md](/Users/eric/adlc/docs/specs/idempotency-keys.md).
- Permission log shape is defined in [docs/specs/permission-logging.md](/Users/eric/adlc/docs/specs/permission-logging.md).
- Retries must return prior artifact metadata when the key is already terminal.

## Readiness Gate

Before any external mutation, ADLC computes a deterministic readiness report on the normalized payload. The report is included in the emitter output under `readiness_report`.

```json
{
  "status": "ready | blocked",
  "issues": [
    {
      "severity": "blocking",
      "rule": "unresolved_dependency_alias",
      "task_id": "TASK-001",
      "message": "dependency GOV-A1 does not resolve to a task_id"
    }
  ],
  "totals": {
    "tasks": 6,
    "ready": 5,
    "blocked": 1,
    "issues": 1
  }
}
```

### Readiness Rules

The readiness checker validates:

1. **Dependency resolution** — every `dependencies` entry resolves to a `task_id` in the brief.
2. **Validation task resolution** — every `enterprise_readiness_contract.validation_tasks` entry resolves to an emitted `validation_task` artifact.
3. **Decision gate semantics** — `decision_gate` tasks must have `blocks_implementation=true`, `decision_contract.status=unresolved`, and `decision_contract.type1_decision=true`.
4. **Implementation task semantics** — `implementation_task` tasks must not block implementation and must have `decision_contract.status` in `[resolved, not_applicable]`.
5. **Required fields** — `implementation_task` and `validation_task` artifacts must have non-empty:
   - `verification_spec.primary_verifier.target`
   - `acceptance_criteria`
   - `evidence_responsibilities`
   - `definition_of_done`
   - `compatibility_contract`
   - `tech_debt_boundaries`
   - `failure_modes`
6. **Phase-project map** — when a `--phase-project-map` is provided, any task with a `phase_label` that exists in the map must have a matching `target_project` in `work_item_metadata`.

### CLI Flags

- `--require-ready`: dry-runs and mutations exit nonzero when readiness status is `blocked`.
- `--bypass-readiness-check`: permits mutation even when readiness is `blocked`.
- `--phase-project-map <json-or-path>`: optional JSON object, or path to one, mapping phase labels to project names (e.g. `{"coding":"ProjectX"}`).

## Stop Reasons

Emitters must stop with one of:

- `contract_version_incompatible`
- `schema_validation_failed`
- `permission_denied`
- `provider_capability_missing`
- `dependency_unavailable`
- `unresolved_dependency_alias`
- `unresolved_decision_blocks_implementation`
- `external_mutation_partial`
- `readiness_check_blocked`

## Verification Expectations

- Work-item emitters are verified by artifact template completeness, artifact taxonomy preservation, decision-gate blocking semantics, automatic validation task preservation, and field preservation.
- Document emitters are verified by section coverage, hierarchy correctness, and applicability-manifest fidelity.
- No emitter may pass by publishing placeholder titles, empty sections, tickets lacking verifier contracts, or artifacts that drop reuse/debt constraints from the brief.
