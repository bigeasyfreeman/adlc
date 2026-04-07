# Backwards & Forwards Compatibility Analysis — ADLC System

> Analysis of contract surfaces, versioning gaps, and migration risks across the ADLC pipeline's inter-component boundaries.

**Audit Date:** 2026-04-06
**Verdict:** 7 contract surfaces with zero versioning, zero schema validation at boundaries, and zero deprecation mechanisms. Every contract change is currently a breaking change with no migration path.

---

## Contract Surface Inventory

| # | Contract Surface | Producer | Consumer(s) | Format | Versioned? |
|---|-----------------|----------|-------------|--------|-----------|
| 1 | PRD Template | PM-PRD Agent | Build Brief Agent (Phase 0), PRD Quality Evaluator, Gong Skill, Figma Skill, UX Flow Builder | Markdown sections | No |
| 2 | Repo Map (Codebase Research Output) | Codebase Research Skill | Build Brief Agent (all phases), Eval Council, Architecture Scaffolding, Codegen Context, 5 security skills, Grafana Observability | Cached JSON (untyped) | No |
| 3 | Build Brief Output | Build Brief Agent | Eval Council, Confluence, JIRA, QA, CI/CD, Scaffolding, Codegen, Runbook, Grafana, Slack | Markdown sections | No |
| 4 | Eval Council Verdict | Eval Council | Build Brief Agent, Slack Orchestration, deploy gate | Structured verdict | No |
| 5 | MCP Skill I/O Contracts | Each skill's caller | Each skill | JSON with inputSchema | No |
| 6 | Task Ticket Format | Build Brief Agent (Phase 8) | Codegen Context, JIRA Skill, TDD Enforcement, Systematic Debugging | Markdown with mandatory fields | No |
| 7 | Security Skill Threat Assessment | 5 OWASP security skills | Eval Council (Security Auditor), Build Brief tasks | Structured checklist + findings | No |

---

## Backwards Compatibility Risks

### BC-RISK-001: PRD Template Evolution Breaks Build Brief Extraction
**Severity:** High
**Description:** Build Brief Phase 0 does programmatic extraction from the PRD by parsing section headers and table structures. Renaming "Traffic & Load Expectations" to "Load Profile" causes silent empty fields in extraction.
**Evidence:** The Traffic & Load section, Technology Considerations section, and Engineering Architecture Input section are recent additions. Each required coordinated updates to Build Brief extraction logic. No mechanism ensures sync.
**Impact:** Incomplete Build Brief with missing SLO targets, missing technology suitability evaluation, missing architecture input validation.

### BC-RISK-002: Repo Map Schema Changes Break All Downstream Skills
**Severity:** Critical
**Description:** Codebase Research produces a cached JSON repo map consumed by ~15 downstream components. Sections include `architecture`, `services`, `schema_intelligence`, `security`, `observability`, `ci_cd`, `conventions`. No typed interface exists. Consumers access fields by convention.
**Impact:** One section rename or restructure breaks 15 consumers silently. Highest fan-out contract in the system.

### BC-RISK-003: Build Brief Section Changes Break Skill Consumers
**Severity:** High
**Description:** The Build Brief has 12 numbered sections. Different skills parse different sections. Adding Section 2.7 or restructuring Section 8's task format (adding "Contract Changes" or "BPE Classification" mandatory fields) breaks consumers that don't expect new fields.
**Impact:** Codegen Context Assembly is the most sensitive consumer — incorrect parsing produces incomplete coding agent prompts, which produce stub code instead of working code.

### BC-RISK-004: Task Ticket Format Field Additions
**Severity:** High
**Description:** Phase 8 task format has 15+ mandatory fields. Each field addition (Failure Modes, Observability, Contract Changes, BPE Classification) is a breaking change for every consumer: Codegen Context Assembly, JIRA Ticket Creation, TDD Enforcement, Systematic Debugging.
**Impact:** New mandatory fields on tasks that existing consumers don't parse are silently dropped from assembled codegen prompts and JIRA tickets.

---

## Forwards Compatibility Risks

### FC-RISK-001: Eval Council Persona Addition
**Severity:** Medium
**Description:** Council has 5 core + 1 Security Auditor personas. Adding a 7th persona changes prompt-based verdict synthesis. No structured aggregation algorithm exists.
**Impact:** New persona may dilute or distort existing persona verdicts. Synthesis quality may degrade unpredictably.

### FC-RISK-002: New Security Domain Addition
**Severity:** Medium
**Description:** 5 OWASP domains currently. Adding a 6th (e.g., OWASP Mobile Top 10) requires updates to: Security Auditor persona, Build Brief Phase 5 trigger table, every task's "Security Impact" field, Codegen Context Assembly. No single manifest enumerates all integration points.
**Impact:** New skill author misses 3-4 wiring points. Partial integration produces inconsistent security coverage.

### FC-RISK-003: MCP Tool Schema Evolution
**Severity:** High
**Description:** Skills define `inputSchema` in MCP contracts with no versioning. Adding a required field to `figma_extract` breaks every caller. Removing a field gives callers undefined behavior. No schema version negotiation.
**Impact:** "Skills are composable" design principle (swap Confluence for Notion) doesn't work without versioned contracts. Swapping means rewriting every caller.

### FC-RISK-004: Pipeline Phase Addition or Reordering
**Severity:** High
**Description:** The 15-step pipeline is hardcoded in documentation and prompt instructions. Adding a phase between existing phases (e.g., "Phase 2.7: Cost Estimation") requires updating every reference to phase numbers in agent prompts, skill triggers, tool pool definitions, and workflow state.
**Impact:** Phase references are scattered across 25+ files. A phase insertion causes cascade of stale references.

---

## Binary Task Decomposition

### Priority A: Contract Schema Definitions (Foundation — do first)

#### COMPAT-001: Define PRD template contract schema
- [ ] Create `docs/schemas/prd-template.schema.json`
- [ ] Define every section header, table structure, and field name the Build Brief Agent extracts from
- [ ] Include `version` field (start at `1.0.0`, semver)
- [ ] Document which sections are required vs optional
- [ ] Document which sections are machine-parsed vs human-read-only

#### COMPAT-002: Define repo map contract schema
- [ ] Create `docs/schemas/repo-map.schema.json`
- [ ] Define typed interface for every section: `meta`, `tech_stack`, `architecture`, `services`, `schema_intelligence`, `security`, `observability`, `ci_cd`, `conventions`, `tech_debt`, `improvement_opportunities`
- [ ] Each section: required fields, field types, nested structures
- [ ] Include `version` field (start at `1.0.0`, semver)
- [ ] This is the highest-leverage typing investment in the system (15 consumers)

#### COMPAT-003: Define Build Brief contract schema
- [ ] Create `docs/schemas/build-brief.schema.json`
- [ ] Define every numbered section (1-12), subsection, and table structure
- [ ] Define the task ticket schema as a sub-schema (Section 8)
- [ ] Include `version` field (start at `1.0.0`, semver)
- [ ] Document which sections each downstream skill consumes

#### COMPAT-004: Define Eval Council verdict schema
- [ ] Create `docs/schemas/eval-council-verdict.schema.json`
- [ ] Define: `verdict` (enum: APPROVED, APPROVED_WITH_CONCERNS, REVISION_REQUIRED, BLOCKED), `personas[]` (each with name, findings[], verdict, confidence), `synthesis` (combined verdict with rationale), `iteration` (which loop iteration), `version`
- [ ] Define finding schema: `id`, `severity` (critical, major, minor), `persona`, `description`, `recommendation`, `resolved` (boolean)

#### COMPAT-005: Define security assessment contract schema
- [ ] Create `docs/schemas/security-assessment.schema.json`
- [ ] Define: `domain` (enum: appsec, llm, agentic, api, infra), `version`, `checklist[]` (each item: category, check, status, finding), `findings[]` (severity, description, mitigation, blocking)
- [ ] Common schema shared by all 5 security skills

#### COMPAT-006: Define MCP skill I/O contract versioning standard
- [ ] Create `docs/specs/skill-contract-versioning.md`
- [ ] Standard: every skill's `inputSchema` and output format includes a `contract_version` field
- [ ] Callers declare expected version; skill validates compatibility
- [ ] Semver rules: patch = additive optional fields, minor = additive required fields with defaults, major = breaking changes
- [ ] Document version negotiation: caller sends `contract_version: "1.x"`, skill checks compatibility

### Priority B: Validation at Contract Boundaries

#### COMPAT-007: Add contract validation requirements to Build Brief Phase 0
- [ ] Update `agents/ADLC-BUILD-BRIEF-AGENT.md` Phase 0: before extraction, validate PRD against `prd-template.schema.json`
- [ ] On validation failure: report which sections are missing or malformed, do not silently produce empty fields
- [ ] On version mismatch: report which PRD template version was found vs expected

#### COMPAT-008: Add contract validation to Codebase Research output
- [ ] Update `skills/codebase-research/SKILL.md`: output must validate against `repo-map.schema.json` before caching
- [ ] On validation failure: report which sections are incomplete, retry analysis for missing sections
- [ ] Include `version` in cached output

#### COMPAT-009: Add contract validation to Build Brief output
- [ ] Update `agents/ADLC-BUILD-BRIEF-AGENT.md`: before presenting brief to Eval Council, validate against `build-brief.schema.json`
- [ ] On validation failure: report which sections are incomplete, loop back to fill gaps before Council runs
- [ ] Validation runs as a deterministic check (not prompt-based)

#### COMPAT-010: Add contract validation to Eval Council input/output
- [ ] Update `skills/eval-council/SKILL.md`: validate incoming brief against schema, validate verdict output against verdict schema
- [ ] On input validation failure: reject with structured error (not a prompt-based "this looks incomplete")

#### COMPAT-011: Add contract validation to each downstream skill
- [ ] Update `skills/jira-ticket-creation/SKILL.md`: validate task ticket input against task schema from `build-brief.schema.json#/definitions/task`
- [ ] Update `skills/codegen-context/SKILL.md`: validate task + repo map + scaffolding input against expected schemas
- [ ] Update `skills/confluence-decomposition/SKILL.md`: validate Build Brief sections against schema
- [ ] Update `skills/qa-test-data/SKILL.md`: validate G/W/T criteria input against schema
- [ ] Update `skills/ci-cd-pipeline/SKILL.md`: validate infra task input against schema

### Priority C: Deprecation and Migration Support

#### COMPAT-012: Define deprecation protocol
- [ ] Create `docs/specs/deprecation-protocol.md`
- [ ] When a contract field is deprecated: emit both old and new field for N versions (default: 2 major versions)
- [ ] Consumers that use deprecated fields get a structured warning in system logs
- [ ] Document the deprecation lifecycle: announce → dual-emit → warning → removal

#### COMPAT-013: Define migration guide template
- [ ] Create `docs/templates/migration-guide-template.md`
- [ ] Template for every breaking change: what changed, why, which consumers are affected, what to update, before/after examples
- [ ] Require a migration guide for every major version bump of any contract

### Priority D: Skill Discovery and Registration

#### COMPAT-014: Create machine-readable skill manifest
- [ ] Create `skills/manifest.json`
- [ ] For each skill: `name`, `mcp_tool_names[]`, `input_contract_version`, `output_contract_version`, `triggers[]` (which events/phases invoke it), `consumers[]` (which components read its output), `side_effects[]` (what external systems it mutates)
- [ ] Build Brief Agent's Section 12 (Skill Trigger Configuration) is generated from this manifest, not hardcoded
- [ ] Slack Orchestration Skill's trigger table is generated from this manifest

#### COMPAT-015: Add contributing guide for new skills with compatibility checklist
- [ ] Update `README.md` contributing section with compatibility checklist:
  - [ ] Define input/output contract with version
  - [ ] Add entry to `skills/manifest.json`
  - [ ] Add contract schema to `docs/schemas/`
  - [ ] Verify all integration points listed in manifest are updated
  - [ ] Add contract validation to skill implementation
  - [ ] If skill produces output consumed by Eval Council, update Council persona(s)

### Priority E: Pipeline Contract Chain Test

#### COMPAT-016: Define end-to-end contract smoke test spec
- [ ] Create `docs/tests/contract-chain-tests.md`
- [ ] Test 1: Pass a canonical PRD through Build Brief extraction → verify all extracted fields are non-empty and schema-valid
- [ ] Test 2: Pass a canonical repo through Codebase Research → verify output validates against repo-map schema → pass to Build Brief → verify all repo-map-derived fields are populated
- [ ] Test 3: Generate a canonical Build Brief → pass each section to its downstream skill consumer → verify each skill receives valid input (schema validation passes)
- [ ] Test 4: Generate Eval Council verdict → verify Build Brief Agent correctly interprets APPROVED, BLOCKED, and REVISION_REQUIRED verdicts
- [ ] Test 5: Modify a single field name in the PRD template → run test 1 → verify validation catches the break (not silently empty)
- [ ] Test 6: Modify a single section in the repo map → run test 2 → verify validation catches the break

#### COMPAT-017: Define version compatibility matrix
- [ ] Create `docs/specs/version-compatibility-matrix.md`
- [ ] Matrix: for each contract surface, list which versions of each consumer are compatible with which versions of the producer
- [ ] Update on every contract version bump
