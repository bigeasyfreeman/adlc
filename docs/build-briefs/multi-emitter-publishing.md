# Build Brief: Multi-Emitter Publishing

**Date:** 2026-04-14  
**Owner:** ADLC  
**Task Classification:** `feature`

## Applicability Manifest

- **Core baseline:** active
- **Active overlays:** external integration, interface contract, docs truthfulness
- **Suppressed overlays:** persistent storage, observability, performance, rollout
- **Primary verifier style:** command and content validation

## 1. Overview

ADLC says integrations are swappable, but the repo only defines JIRA and Confluence emitters concretely. The framework needs a shared emitter contract plus first-class GitHub, Linear, and Notion emitters so the claim is operational instead of aspirational.

## 2. What Changes

- Add a shared emitter contract for work-item and documentation publishers.
- Add `github-issue-creation`, `linear-ticket-creation`, and `notion-decomposition` skills.
- Align existing `jira-ticket-creation` and `confluence-decomposition` skills with the shared contract, idempotency, and permission logging rules.
- Make the emitter layer target locally installed third-party MCP providers instead of shipping vendor SDK clients inside ADLC.
- Update manifest, specs, README, and contract tests so the supported emitter matrix is truthful.

## 3. Architecture & Patterns

- **Pattern:** One normalized Build Brief input, many platform adapters.
- **Transport boundary:** ADLC emits normalized payloads; local MCP providers own auth and vendor API transport.
- **Shared contract:** [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md)
- **Existing references:** [skills/jira-ticket-creation/SKILL.md](/Users/eric/adlc/skills/jira-ticket-creation/SKILL.md), [skills/confluence-decomposition/SKILL.md](/Users/eric/adlc/skills/confluence-decomposition/SKILL.md)
- **Constraint:** Platform-specific configuration belongs in emitter-specific config blocks. The Build Brief task schema stays platform-neutral.

## 4. Data Model Changes

Not applicable. This work adds emitter contracts and skills only.

## 5. API Changes

Not applicable. This work defines MCP skill contracts, not runtime product APIs.

## 6. Security Review

- External artifact creation remains a `pr_prep`-phase mutating action only.
- Every emitter must require `contract_version`, idempotency keys, and permission logging.
- Every emitter must resolve a locally installed MCP provider with the required logical capabilities before mutation.
- No emitter may fabricate suppressed sections from the applicability manifest.

## 7. Failure Modes

| ID | Failure | Impact | Mitigation |
|---|---|---|---|
| FM-EMIT-001 | New emitters drift from JIRA/Confluence semantics | Swappability claim stays false | Shared emitter contract plus manifest/test assertions |
| FM-EMIT-002 | Platform adapters drop `verification_spec` or `task_classification` | Tickets become too vague for coding agents | Preserve mandatory task fields in every emitter template |
| FM-EMIT-003 | Retries create duplicate issues or pages | External state becomes noisy and misleading | Require per-artifact idempotency keys and dedupe behavior |
| FM-EMIT-004 | Docs claim support that manifest/tests do not reflect | Repo truthfulness regresses | Update README, spec, and contract checks together |

## 8. SLOs & Performance

Not applicable. No runtime path is introduced.

## 9. Task Breakdown

### EMIT-001: Define shared emitter contract

- **Problem statement:** JIRA and Confluence encode their own assumptions, so adding GitHub, Linear, and Notion would otherwise duplicate and drift.
- **Files to create:** `docs/specs/emitter-contract.md`
- **Files to modify:** `README.md`, `docs/adlc-v2-specification.md`, `docs/specs/version-compatibility-matrix.md`
- **Reference implementation:** `skills/jira-ticket-creation/SKILL.md`, `skills/confluence-decomposition/SKILL.md`
- **Dependency IDs:** none
- **Acceptance criteria:**
  - [ ] Shared contract defines work-item and document emitter families.
  - [ ] Shared contract requires `contract_version`, idempotency, permission logging, and applicability-manifest preservation.
  - [ ] README/spec surfaces reference the shared contract instead of implying only JIRA/Confluence are real.
- **Verification spec:**
  - Primary verifier: command
  - Target: `rg -n 'GitHub|Linear|Notion|contract_version|idempotency' docs/specs/emitter-contract.md README.md docs/adlc-v2-specification.md`

### EMIT-002: Add GitHub issue emitter

- **Problem statement:** ADLC needs a first-class GitHub work-item emitter instead of requiring teams to translate JIRA semantics manually.
- **Files to create:** `skills/github-issue-creation/SKILL.md`
- **Files to modify:** `skills/manifest.json`, `tests/test_adlc_contracts.sh`
- **Reference implementation:** `skills/jira-ticket-creation/SKILL.md`
- **Dependency IDs:** `EMIT-001`
- **Acceptance criteria:**
  - [ ] Skill defines a GitHub tracking-issue plus per-task issue model.
  - [ ] Issue bodies preserve `task_classification`, `verification_spec`, dependencies, and out-of-scope details.
  - [ ] Idempotency and retry behavior use durable metadata instead of title matching.
- **Verification spec:**
  - Primary verifier: command
  - Target: `rg -n 'Verification Contract|task_classification|verification_spec|idempotency' skills/github-issue-creation/SKILL.md tests/test_adlc_contracts.sh`

### EMIT-003: Add Linear ticket emitter

- **Problem statement:** The framework claims Linear can replace JIRA, but no Linear adapter exists today.
- **Files to create:** `skills/linear-ticket-creation/SKILL.md`
- **Files to modify:** `skills/manifest.json`, `tests/test_adlc_contracts.sh`
- **Reference implementation:** `skills/jira-ticket-creation/SKILL.md`
- **Dependency IDs:** `EMIT-001`
- **Acceptance criteria:**
  - [ ] Skill defines project/cycle-aware Linear issue creation.
  - [ ] Ticket bodies preserve the same minimum execution contract as JIRA and GitHub.
  - [ ] Dependency and dedupe behavior are explicit rather than implied.
- **Verification spec:**
  - Primary verifier: command
  - Target: `rg -n 'Verification Contract|task_classification|verification_spec|idempotency' skills/linear-ticket-creation/SKILL.md tests/test_adlc_contracts.sh`

### EMIT-004: Add Notion decomposition emitter

- **Problem statement:** The framework claims Confluence can be swapped for Notion, but there is no Notion decomposition contract.
- **Files to create:** `skills/notion-decomposition/SKILL.md`
- **Files to modify:** `skills/manifest.json`, `tests/test_adlc_contracts.sh`
- **Reference implementation:** `skills/confluence-decomposition/SKILL.md`
- **Dependency IDs:** `EMIT-001`
- **Acceptance criteria:**
  - [ ] Skill defines a parent-page plus child-page structure for Build Brief decomposition in Notion.
  - [ ] Suppressed sections stay omitted or explicitly marked not applicable.
  - [ ] Optional task database publishing is documented without making it mandatory.
- **Verification spec:**
  - Primary verifier: command
  - Target: `rg -n 'applicability_manifest|active Build Brief sections|idempotency' skills/notion-decomposition/SKILL.md tests/test_adlc_contracts.sh`

### EMIT-005: Align existing emitters and framework surfaces

- **Problem statement:** Adding new skills without updating the existing emitters, docs, and tests would keep the framework internally inconsistent.
- **Files to modify:** `skills/jira-ticket-creation/SKILL.md`, `skills/confluence-decomposition/SKILL.md`, `docs/specs/idempotency-keys.md`, `docs/specs/permission-logging.md`, `docs/specs/workflow-checkpoints.md`, `docs/specs/tool-pools.md`, `docs/specs/health-check.md`, `docs/tests/idempotency-tests.md`, `skills/eval-council/SKILL.md`, `skills/ci-cd-pipeline/SKILL.md`
- **Reference implementation:** `docs/specs/skill-contract-versioning.md`, `docs/specs/idempotency-keys.md`
- **Dependency IDs:** `EMIT-001`, `EMIT-002`, `EMIT-003`, `EMIT-004`
- **Acceptance criteria:**
  - [ ] Existing JIRA and Confluence skills reference the shared emitter contract.
  - [ ] Framework specs treat work-item/document emitters as families, not hardcoded vendor pairs.
  - [ ] Contract tests cover all newly supported emitters.
- **Verification spec:**
  - Primary verifier: command
  - Target: `bash tests/test_adlc_contracts.sh`

## 10. Compatibility & Resilience

- Keep the Build Brief schema platform-neutral.
- New emitters must remain compatible with Build Brief `1.x`.
- Platform-specific fallback behavior must be explicit where a target lacks native dependency or hierarchy primitives.

## 11. G/W/T Roll-Up

- **Given** the repo claims integrations are swappable, **when** a reader inspects `README.md`, manifest, and supporting specs, **then** GitHub, Linear, and Notion appear as first-class supported emitters.
- **Given** a task in a Build Brief includes `task_classification` and `verification_spec`, **when** any work-item emitter publishes it, **then** those fields survive in the emitted artifact template.
- **Given** a retry against a mutating emitter, **when** the idempotency key already exists, **then** the skill returns the prior artifact metadata instead of creating duplicates.

## 12. Skill Handoffs

- `jira-ticket-creation`: align to shared emitter contract
- `github-issue-creation`: GitHub work-item publishing
- `linear-ticket-creation`: Linear work-item publishing
- `confluence-decomposition`: align to shared emitter contract
- `notion-decomposition`: Notion documentation publishing
- `eval-council`: validate post-skill-output artifacts against the same minimum execution contract

## 13. Open Items

- Runtime MCP server implementations are out of scope here; this brief covers framework contracts and skill definitions only.
- If a future repo needs Asana, Shortcut, or ClickUp support, it should extend the shared emitter contract rather than fork the task schema.

## 14. Revision History

- 2026-04-14: Initial brief created to decompose multi-emitter publishing into contract, skill, and framework-alignment tasks.
