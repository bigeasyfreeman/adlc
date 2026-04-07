# Infrastructure Primitives Audit — ADLC System

> Gap analysis of the ADLC system against the 12 infrastructure primitives that constitute the plumbing beneath the LLM call in production agentic AI systems.

**Audit Date:** 2026-04-06
**System Tier:** Day-One Partial / Week-One Aspirational
**Verdict:** Agent intelligence layer (prompts, skills, evaluation criteria) is sophisticated. Agent infrastructure layer (runtime plumbing) is almost entirely absent. All behavioral rules depend on prompt compliance rather than enforced runtime constraints.

---

## System Summary

The ADLC (Agentic Development Lifecycle) is a multi-agent orchestration system that converts feature ideas into production code through a structured pipeline. Two core agents (PM-PRD Agent, Build Brief Agent) plus 21 specialized skills covering security (5 OWASP domains), code generation, testing, observability, CI/CD, and workflow management. Runs inside IDE agent contexts with skills deployed as MCP servers.

---

## Day One Primitives Assessment

| Primitive | Status | Finding | Risk |
|-----------|--------|---------|------|
| Tool Registry with Metadata-First Design | ⚠️ Partial | Skills define MCP server contracts with `inputSchema` but no centralized `listTools()`, no runtime filtering, no side-effect profiles | Coding agents can invoke out-of-scope tools (JIRA, Slack) mid-task |
| Permission System with Trust Tiers | ⚠️ Partial | Type 1/2 decision model exists conceptually; no runtime permission enforcement, no tool-level risk classification, no permission decision logging | Prompt-level "do not deploy" is the only guardrail; no defense in depth |
| Session Persistence That Survives Crashes | ❌ Missing | No persistence layer, no `resumeSession()`, no crash recovery | Losing a Build Brief mid-conversation wastes hours of engineer + agent compute |
| Workflow State and Idempotency | ❌ Missing | 15-step pipeline with no state machine, no checkpointing, no idempotency keys | Retry after partial JIRA/Confluence creation produces duplicates |
| Token Budget Tracking with Pre-Turn Checks | ❌ Missing | No token tracking anywhere; zero-read principle + 5-persona Council = unbounded cost | Runaway Council loop on complex brief can consume hundreds of dollars |
| Structured Streaming Events | ❌ Missing | Slack messages at transitions but no typed event system | No real-time visibility into autonomous pipeline progress |
| System Event Logging | ⚠️ Partial | Logging mandated in generated code but not in the agent system itself | Cannot audit Council decisions, tool selections, or permission grants |
| Basic Verification Harness | ⚠️ Partial | Eval Council is sophisticated prompt-based verification; no deterministic invariant tests | Model upgrade or prompt change can silently break guardrails |

## Week One Primitives Assessment

| Primitive | Status | Finding | Risk |
|-----------|--------|---------|------|
| Tool Pool Assembly | ⚠️ Partial | Phase-specific skill triggers documented but not runtime-enforced | Phase 9 coding agent can invoke Phase 11 tools |
| Transcript Compaction | ❌ Missing | Zero-read principle creates massive context; no compaction/summarization | Context overflow or excessive cost on large codebases |
| Permission Audit Trail | ❌ Missing | Type 1 decisions tracked via Slack messages, not structured data | Cannot answer "who approved this migration and when?" for compliance |
| Doctor Pattern + Staged Boot + Stop Reasons + Provenance | ⚠️ Partial | Staged pipeline exists; no health check, no credential validation at boot, no stop reason taxonomy | Expired API tokens discovered mid-pipeline, not at start |

## Month One Primitives

Not the priority. The system's Month One aspirations (agent type system, memory, skills framework, multi-agent coordination) are conceptually present but built on missing Day One foundations. Implement Day One and Week One first.

---

## Priority 1: Workflow State Machine with Idempotent Skill Execution

### Binary Task Decomposition

#### P1-WF-001: Define workflow state schema
- [ ] Create `docs/schemas/workflow-state.schema.json` defining the pipeline state data structure
- [ ] Schema includes: `brief_id`, `phase` (enum of all 15 pipeline steps), `step` (current sub-step), `status` (enum: planned, awaiting_approval, executing, waiting_on_external, completed, failed), `started_at`, `updated_at`, `checkpoint` (arbitrary JSON blob for step-specific state)
- [ ] Schema includes `side_effects[]` array tracking every external mutation (JIRA ticket created, Confluence page created, Git branch created) with timestamps and idempotency keys
- [ ] Schema validated with JSON Schema draft-07

#### P1-WF-002: Define idempotency key generation spec
- [ ] Create `docs/specs/idempotency-keys.md` specifying key format: `{brief_id}:{skill_name}:{task_id}:{operation}` 
- [ ] Document idempotency key requirements for each side-effecting skill:
  - [ ] JIRA Ticket Creation: key = `{brief_id}:jira:{task_id}`
  - [ ] Confluence Decomposition: key = `{brief_id}:confluence:{section_id}`
  - [ ] Architecture Scaffolding: key = `{brief_id}:scaffold:{component_name}`
  - [ ] Grafana Observability: key = `{brief_id}:grafana:{dashboard_name}`
  - [ ] CI/CD Pipeline: key = `{brief_id}:cicd:{pipeline_name}`
  - [ ] Slack Orchestration: key = `{brief_id}:slack:{event_type}:{target}`
  - [ ] Git operations: key = `{brief_id}:git:{operation}:{ref}`
- [ ] Document deduplication behavior: on retry with existing key, return existing artifact ID without creating duplicate

#### P1-WF-003: Define checkpoint spec for each pipeline phase
- [ ] Create `docs/specs/workflow-checkpoints.md`
- [ ] For each of the 15 pipeline steps, document:
  - [ ] What state is captured at the checkpoint
  - [ ] What artifacts have been created
  - [ ] What is needed to resume from this checkpoint
  - [ ] What cleanup is needed if the step failed mid-execution
- [ ] Document the `resumeWorkflow(briefId)` function contract: inputs, outputs, behavior on corrupted state

#### P1-WF-004: Define partial failure recovery spec
- [ ] Document recovery behavior for each skill when it fails mid-batch:
  - [ ] JIRA: query existing tickets by idempotency key label, create only missing ones
  - [ ] Confluence: check page exists by title in target space, create only missing pages
  - [ ] Scaffolding: check file exists at target path, create only missing files
  - [ ] Grafana: check dashboard exists by UID, create only missing dashboards
- [ ] Document the structured recovery report format: `{ total: N, completed: M, failed: F, remaining: R, failures: [...] }`

#### P1-WF-005: Add workflow state requirements to Build Brief Agent spec
- [ ] Add a "Workflow State" section to `agents/ADLC-BUILD-BRIEF-AGENT.md` referencing the workflow state schema
- [ ] Add checkpoint emission requirements after each phase completion
- [ ] Add idempotency key requirements to each skill trigger in Section 12

#### P1-WF-006: Add workflow state requirements to each side-effecting skill
- [ ] Update `skills/jira-ticket-creation/SKILL.md`: add idempotency key input field, add deduplication check before create, add partial batch recovery behavior
- [ ] Update `skills/confluence-decomposition/SKILL.md`: add idempotency key input field, add existence check before create
- [ ] Update `skills/architecture-pattern/SKILL.md`: add idempotency check (file exists at path)
- [ ] Update `skills/grafana-observability/SKILL.md`: add dashboard UID-based deduplication
- [ ] Update `skills/ci-cd-pipeline/SKILL.md`: add pipeline config deduplication
- [ ] Update `skills/slack-orchestration/SKILL.md`: add message deduplication for escalations
- [ ] Update `skills/incident-runbook/SKILL.md`: add page existence check before create

#### P1-WF-007: Add workflow state to Eval Council loop
- [ ] Update `skills/eval-council/SKILL.md`: add iteration counter to workflow state, add hard stop at iteration 3 with structured "council exhausted" state, add per-iteration checkpoint

#### P1-WF-008: Update README with workflow state architecture
- [ ] Add workflow state section to `README.md` explaining the state machine, checkpointing, and recovery model

---

## Priority 2: Token Budget Tracking with Pre-Turn Circuit Breaker

### Binary Task Decomposition

#### P2-TB-001: Define token budget schema
- [ ] Create `docs/schemas/token-budget.schema.json`
- [ ] Schema includes: `session_id`, `budget_limit` (configurable), `tokens_used` (running total), `tokens_by_phase` (breakdown per pipeline phase), `tokens_by_skill` (breakdown per skill invocation), `cost_estimate` (derived from model pricing)
- [ ] Schema includes alert thresholds: `warn_at` (default 50%), `alert_at` (default 80%), `hard_stop_at` (default 100%)

#### P2-TB-002: Define per-phase and per-skill token budgets
- [ ] Create `docs/specs/token-budgets.md`
- [ ] Define default budget allocations:
  - [ ] Codebase Research: max 100K tokens
  - [ ] Build Brief conversation (all phases): max 200K tokens
  - [ ] Eval Council per iteration: max 100K tokens
  - [ ] Eval Council total (all iterations): max 300K tokens
  - [ ] Codegen Context Assembly per task: max 50K tokens
  - [ ] Coding Agent per task: max 80K tokens
  - [ ] Security skills per task: max 30K tokens
  - [ ] Total session budget: configurable, default 1M tokens
- [ ] Document override mechanism (per-brief configuration)

#### P2-TB-003: Define pre-turn budget check spec
- [ ] Create `docs/specs/pre-turn-check.md`
- [ ] Document the check: before every LLM API call, estimate input tokens (prompt size) + expected output tokens (model-specific estimate), verify `current_used + estimate <= budget`
- [ ] Document "wrap up" mode behavior: when budget > 80%, agent summarizes remaining work instead of continuing, produces a structured "budget approaching limit" report
- [ ] Document hard stop behavior: when budget exceeded, return structured stop reason `{ reason: "budget_exhausted", tokens_used: N, budget: M, phase: "...", recommendation: "..." }`

#### P2-TB-004: Define Eval Council circuit breaker spec
- [ ] Document: if Council iteration 1 consumed > 50% of Council budget, iteration 2 uses a compressed brief (summary, not full inline code)
- [ ] Document: if Council iteration 2 still fails, iteration 3 is blocked; present to engineer with "budget constrained — Council could not complete 3 iterations"
- [ ] Document: Council budget is separate from session budget (Council cannot starve codegen)

#### P2-TB-005: Add token budget requirements to Build Brief Agent spec
- [ ] Add "Token Budget" section to `agents/ADLC-BUILD-BRIEF-AGENT.md`
- [ ] Add pre-turn check requirement before every LLM call
- [ ] Add budget reporting to the Build Brief output (total tokens consumed during brief generation)

#### P2-TB-006: Add token budget requirements to Eval Council spec
- [ ] Update `skills/eval-council/SKILL.md`: add per-iteration token tracking, add circuit breaker, add budget-aware iteration logic

#### P2-TB-007: Add token budget requirements to Codegen Context Assembly
- [ ] Update `skills/codegen-context/SKILL.md`: add per-task token budget, add context compression when budget tight (summarize inlined code instead of full paste), add budget exceeded behavior

#### P2-TB-008: Define cost reporting format
- [ ] Create `docs/specs/cost-reporting.md`
- [ ] Define the session cost report: tokens by phase, tokens by skill, estimated cost by model, top 3 most expensive operations
- [ ] Document where the cost report is emitted (appended to Build Brief, posted to Slack, stored in workflow state)

---

## Priority 3: Deterministic Verification Harness for Agent Guardrails

### Binary Task Decomposition

#### P3-VH-001: Define verification harness architecture
- [ ] Create `docs/specs/verification-harness.md`
- [ ] Document the harness approach: deterministic tests (not prompt-based) that validate agent system invariants
- [ ] Document test categories: permission enforcement, gate enforcement, budget enforcement, idempotency, scope immutability
- [ ] Document test execution: run on every change to agent prompts, skill specs, or pipeline configuration
- [ ] Document mock strategy: mock LLM responses with canned outputs, mock skill endpoints with deterministic behavior

#### P3-VH-002: Define scope immutability test specs
- [ ] Create `docs/tests/scope-immutability-tests.md`
- [ ] Test 1: Feed Council a brief where a persona recommends removing an in-scope feature → verify final verdict retains the feature
- [ ] Test 2: Feed Council 10 different phrasings of "let's defer this" → verify all 10 are caught
- [ ] Test 3: Feed Council a recommendation that paraphrases scope removal as "quality improvement" → verify it's caught
- [ ] Test 4: Verify the Build Brief Agent never removes items from the PRD's out-of-scope section

#### P3-VH-003: Define idempotency test specs
- [ ] Create `docs/tests/idempotency-tests.md`
- [ ] Test 1: Run JIRA creation for 18 tasks, kill at task 12, retry → verify exactly 18 tickets exist (not 30)
- [ ] Test 2: Run Confluence creation, kill mid-page, retry → verify no duplicate pages
- [ ] Test 3: Run Grafana provisioning, kill mid-dashboard, retry → verify no duplicate dashboards
- [ ] Test 4: Run full pipeline twice with same brief ID → verify identical artifacts (not double)

#### P3-VH-004: Define gate enforcement test specs
- [ ] Create `docs/tests/gate-enforcement-tests.md`
- [ ] Test 1: When Eval Council verdict is BLOCKED, verify downstream skills do not execute
- [ ] Test 2: When Type 1 decision is unresolved, verify pipeline halts and Slack escalation fires
- [ ] Test 3: When engineer has not approved brief, verify JIRA/Confluence/scaffolding skills do not execute
- [ ] Test 4: When pre-deploy Eval Council fails, verify deploy gate stays closed

#### P3-VH-005: Define budget enforcement test specs
- [ ] Create `docs/tests/budget-enforcement-tests.md`
- [ ] Test 1: When session budget is exceeded, verify next LLM call is blocked with structured stop reason
- [ ] Test 2: When Council budget is exceeded at iteration 2, verify iteration 3 does not start
- [ ] Test 3: When per-task codegen budget is exceeded, verify task produces a structured "budget exceeded" output (not truncated garbage)
- [ ] Test 4: When budget hits 80%, verify "wrap up" mode activates

#### P3-VH-006: Define phase boundary enforcement test specs
- [ ] Create `docs/tests/phase-boundary-tests.md`
- [ ] Test 1: During Phase 9 (codegen), attempt to invoke JIRA Ticket Creation → verify denied
- [ ] Test 2: During Phase 9, attempt to invoke Slack Escalation → verify denied
- [ ] Test 3: During Phase 0 (research), attempt to invoke Architecture Scaffolding → verify denied
- [ ] Test 4: During Phase 3 (codegen), attempt to invoke Confluence Decomposition → verify denied

#### P3-VH-007: Define crash recovery test specs
- [ ] Create `docs/tests/crash-recovery-tests.md`
- [ ] Test 1: Start Build Brief, advance to Phase 6, simulate crash, restart → verify resume from Phase 6 with Phases 0-5 context intact
- [ ] Test 2: Start codegen with 8 parallel tasks, kill 3 mid-execution, restart → verify only the 3 killed tasks re-execute
- [ ] Test 3: Kill during Eval Council iteration 2 → verify restart begins at iteration 2 (not iteration 1)

#### P3-VH-008: Add verification harness section to README
- [ ] Add "Verification Harness" section to `README.md` explaining the test categories, execution triggers, and how to add new invariant tests

---

## Priority 4: Remaining Day One Gaps

### Tool Registry

#### P4-TR-001: Define tool registry schema
- [ ] Create `docs/schemas/tool-registry.schema.json`
- [ ] Schema per tool: `name`, `description`, `inputSchema`, `side_effect_profile` (enum: read_only, mutating, destructive), `permission_tier` (enum: unrestricted, requires_approval, requires_escalation), `available_phases[]` (which pipeline phases can invoke this tool)
- [ ] Define `listTools(phase, context)` contract: returns only tools available in the current phase and context

#### P4-TR-002: Create tool registry manifest
- [ ] Create `skills/registry.json` with an entry for every skill/tool
- [ ] Each entry: skill name, MCP tool names, side-effect profile, permission tier, available phases
- [ ] Build Brief Agent and Codegen Context Assembly must reference this registry (not hardcoded skill lists)

#### P4-TR-003: Add runtime filtering requirements to skills
- [ ] Update `agents/ADLC-BUILD-BRIEF-AGENT.md`: reference registry for skill invocation, add phase check before invoking any skill
- [ ] Update `skills/codegen-context/SKILL.md`: assembled prompts must only include tools from the registry's `available_phases` for Phase 9

### Permission System

#### P4-PS-001: Define permission tier classification for all tools
- [ ] Create `docs/specs/permission-tiers.md`
- [ ] Classify every skill/tool:
  - [ ] Read-only (Codebase Research, Grafana baseline pull, Gong search): unrestricted
  - [ ] Mutating (JIRA create, Confluence create, Git branch, Scaffolding write): requires_approval
  - [ ] Destructive (Schema migration, production deploy, feature flag toggle): requires_escalation
- [ ] Document approval flow per tier

#### P4-PS-002: Define permission decision logging spec
- [ ] Create `docs/specs/permission-logging.md`
- [ ] Every permission decision logged as structured data: `{ tool, action, tier, decision (approved/denied), decided_by (human/machine/policy), timestamp, rationale }`
- [ ] Accumulated denials per session tracked and surfaced in session report

### Session Persistence

#### P4-SP-001: Define session state schema
- [ ] Create `docs/schemas/session-state.schema.json`
- [ ] Session state includes: conversation history (messages), token usage (running totals), permission decisions (structured log), configuration (model, budget, skill config), workflow state reference
- [ ] Define `resumeSession(sessionId)` contract: reconstructs full agent state including tools available, permissions granted, tokens consumed, and workflow phase

#### P4-SP-002: Define persistence trigger spec
- [ ] Create `docs/specs/session-persistence.md`
- [ ] Persist after: every engineer message, every skill invocation, every permission decision, every phase transition, every Eval Council verdict
- [ ] Document storage backend requirements (local file, SQLite, or external store)

### Structured Streaming Events

#### P4-SE-001: Define event schema
- [ ] Create `docs/schemas/streaming-events.schema.json`
- [ ] Event types: `pipeline.started`, `phase.started`, `phase.completed`, `skill.invoked`, `skill.completed`, `skill.failed`, `council.started`, `council.verdict`, `task.dispatched`, `task.completed`, `task.failed`, `budget.warning`, `budget.exceeded`, `permission.decided`, `pipeline.completed`, `pipeline.failed`
- [ ] Each event: `type`, `timestamp`, `session_id`, `brief_id`, `phase`, `payload` (type-specific), `stop_reason` (on terminal events)

#### P4-SE-002: Define stop reason taxonomy
- [ ] Create `docs/specs/stop-reasons.md`
- [ ] Named stop reasons: `completed`, `budget_exhausted`, `council_blocked`, `engineer_rejected`, `type1_unresolved`, `crash_recovered`, `skill_failed_unrecoverable`, `timeout`
- [ ] Each stop reason: definition, what triggered it, what the user should do next

### System Event Logging

#### P4-SL-001: Define system log schema
- [ ] Create `docs/schemas/system-log.schema.json`
- [ ] Log categories: `initialization`, `tool_selection`, `permission_decision`, `council_evaluation`, `skill_execution`, `error`, `persistence`, `budget`
- [ ] Each log entry: `category`, `timestamp`, `session_id`, `message`, `metadata` (category-specific structured data)
- [ ] Distinct from conversation transcript and distinct from generated code's application logs

#### P4-SL-002: Add system logging requirements to agent and skill specs
- [ ] Update `agents/ADLC-BUILD-BRIEF-AGENT.md`: add system log emission requirements for each phase transition, each skill invocation, each decision
- [ ] Update `skills/eval-council/SKILL.md`: add per-persona verdict logging (which persona, what findings, what verdict, what confidence)
- [ ] Update `skills/slack-orchestration/SKILL.md`: add escalation decision logging

---

## Priority 5: Week One Gaps

### Tool Pool Assembly

#### P5-TP-001: Define phase-specific tool pools
- [ ] Create `docs/specs/tool-pools.md`
- [ ] For each pipeline phase, define the exact set of tools available:
  - [ ] Phase 0 (Research): Codebase Research, Grafana baseline pull
  - [ ] Phase 1-7 (Brief): Build Brief tools only (no external mutations)
  - [ ] Phase 8 (Task Breakdown): Build Brief tools, Architecture analysis
  - [ ] Phase 9 (Codegen): File read/write, test runner, git operations only
  - [ ] Phase 10-11 (Prep): JIRA, Confluence, Scaffolding, QA, CI/CD
  - [ ] Phase 12+ (Deploy): CI/CD, Grafana provisioning, Runbook, Slack
- [ ] Each tool pool is a deny-list on top of the full registry (default deny, explicit allow)

### Transcript Compaction

#### P5-TC-001: Define compaction strategy
- [ ] Create `docs/specs/transcript-compaction.md`
- [ ] Define compaction triggers: context window > 80% capacity, token budget > 70% consumed, conversation > 20 turns
- [ ] Define compaction strategy: summarize older turns (keep last 5 verbatim), compress inlined code to signatures + key logic, compress repo map to relevant sections only
- [ ] Document what must never be compacted: current phase state, open questions, Type 1 decisions, G/W/T acceptance criteria

### Permission Audit Trail

#### P5-PA-001: Define audit trail schema
- [ ] Create `docs/schemas/permission-audit-trail.schema.json`
- [ ] Each entry: `decision_id`, `tool_name`, `action`, `reason` (human-readable), `decided_by`, `timestamp`, `session_id`, `brief_id`
- [ ] Accumulated denials per session with count and patterns
- [ ] Export format: JSON for machine consumption, markdown table for human review

### Doctor Pattern / Health Check

#### P5-HC-001: Define health check spec
- [ ] Create `docs/specs/health-check.md`
- [ ] At pipeline start, validate:
  - [ ] Figma API token: valid (if Figma links in PRD)
  - [ ] JIRA connection: authenticated and target project accessible
  - [ ] Confluence connection: authenticated and target space accessible
  - [ ] Grafana connection: authenticated and target org accessible
  - [ ] Slack connection: authenticated and target channels accessible
  - [ ] Git: repo accessible, branch strategy valid
  - [ ] LLM API: model accessible, budget available
- [ ] Health check output: structured report with pass/fail per dependency
- [ ] Pipeline blocks on any critical dependency failure (JIRA, Git, LLM)
- [ ] Pipeline warns on non-critical dependency failure (Figma, Grafana)
