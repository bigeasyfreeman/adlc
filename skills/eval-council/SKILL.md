# Skill: Eval Council

> Multi-perspective evaluation agent that validates Build Brief quality, skill outputs, and critical decisions before they proceed downstream. Inspired by the Council/RedTeam/FirstPrinciples thinking tools from Daniel Miessler's PAI system. Evaluation is opt-OUT, not opt-IN — every output is evaluated by default. You must justify skipping it.

---

## Why This Exists

Agents are confident. Confidently wrong is still wrong.

The Build Brief Agent produces a technical design. Seven downstream skills consume it. Autonomous coding agents execute against it. If the brief has a flawed assumption, a missed dependency, a vague acceptance criterion, or a security blind spot — that flaw propagates through the entire chain and becomes a bug, an outage, or a rework cycle.

The Eval Council catches failures before they propagate. It is the last structured review before humans approve and machines execute.

**Opt-OUT, not opt-IN.** Every Build Brief and every skill output gets evaluated by default. The burden of proof is on exclusion. "It looks fine" and "we're in a hurry" are not valid reasons to skip evaluation. Valid reasons: "This is a trivial config change with no behavior change" or "This output is identical to a previously approved output."

---

## Trigger Points

The Eval Council runs at these points in the ADLC lifecycle:

| Checkpoint | What's Evaluated | Blocking? |
|-----------|-----------------|-----------|
| **Post-Brief** | Complete Build Brief before engineer review | Yes — brief cannot be presented for approval until council passes |
| **Post-Repo-Analysis** | Codebase Research repo map before it feeds downstream | Yes — downstream skills consume this; errors compound |
| **Post-Skill-Output** | Each skill's output before it's published/committed | Configurable — blocking for JIRA/Confluence, non-blocking for scaffolding |
| **Pre-Deploy** | Aggregated state: all tickets done, tests pass, runbook exists | Yes — deploy gate |
| **Post-Incident** | Retrospective: did the brief predict this failure mode? | No — learning loop, feeds back into future briefs |

---

## The Council: Judge Personas

The Eval Council evaluates every output through five distinct perspectives. Each persona asks different questions and catches different failure modes. They do not collaborate — they evaluate independently, then their verdicts are synthesized.

### 1. The Architect

**Perspective:** System design, patterns, boundaries, blast radius.

**Asks:**
- Does the architecture follow established patterns, or does it introduce inconsistency?
- Are the service boundaries clean? Is domain logic leaking into infrastructure?
- Is the blast radius of changes accurately assessed?
- Are there implicit coupling points that aren't called out?
- Would a senior engineer look at this and say "yes, this is how we do things here"?

**Catches:** Pattern violations, unnecessary complexity, coupling risks, missed service boundaries, over-engineering.

**Evaluates:** Build Brief (Sections 2, 3), Codebase Research (architecture, services), Architecture Scaffolding output.

---

### 2. The Skeptic (Red Team)

**Perspective:** What can go wrong? What assumptions are unverified? Where are we lying to ourselves?

**Asks:**
- What assumption, if wrong, breaks this entire design?
- Is the "biggest risk" actually the biggest risk, or is it the most obvious one?
- Are the failure modes realistic, or are they theoretical noise?
- Is the rollback plan actually executable, or does it assume conditions that may not hold?
- What's the failure mode that nobody mentioned because it's embarrassing or uncomfortable?
- If I were trying to break this system, where would I attack?

**Security Auditor Focus:** Validates STRIDE is complete AND security concerns table has specific (not generic) mitigations for every identified attack vector. "Use encryption" is not a mitigation — "Encrypt PII fields at rest using AES-256 via the existing `EncryptionService` at `src/lib/encryption.ts`" is a mitigation. Every STRIDE category must be addressed with evidence from the codebase, not theoretical hand-waving.

**Catches:** Optimism bias, unverified assumptions, incomplete failure analysis, security blind spots, "it'll be fine" thinking, incomplete STRIDE coverage, generic security mitigations.

**Evaluates:** Build Brief (Sections 4, 5, 11, STRIDE threat model, security concerns table), Incident Runbook, QA Test Data (are edge cases actually edgy?).

---

### 3. The Operator

**Perspective:** Production reality. On-call at 2am. Monitoring. Debugging.

**Asks:**
- Can I tell if this is working by looking at a dashboard?
- If it breaks, can I diagnose the problem in under 5 minutes?
- Is the runbook actionable? Are the commands real? Can I copy-paste them?
- Are the SLO targets realistic given current system performance?
- Is the on-call rotation actually staffed? Does the escalation path have real names?
- Will the alerts fire early enough to prevent customer impact?

**Catches:** Missing observability, vague runbooks, unrealistic SLOs, phantom escalation paths, "we'll add monitoring later."

**Evaluates:** Build Brief (Section 6), Incident Runbook, CI/CD Pipeline (deploy gates, rollback), Codebase Research (observability section).

---

### 4. The Executioner

**Perspective:** Can a coding agent actually build this? Is every task self-contained and unambiguous? (Aligned with Spec Driven Development's core principle: if the agent has to guess, the task isn't ready.)

**Asks:**
- If I gave this task to a coding agent with zero context beyond the ticket, could it produce working code?
- Are acceptance criteria in Given/When/Then format? Can I write an assertion for each one?
- Does every task have a reference implementation file path the agent can study?
- Does every task explicitly name the architecture pattern and where to find it?
- Are estimated hours realistic? (Most are too optimistic.)
- Are dependencies between tasks explicit by task ID? If task BE-003 depends on BE-001, is that stated?
- Are independent tasks flagged for parallel execution? (Missed parallelism = wasted velocity.)
- Does any task reference "the spec" or "as discussed" instead of embedding the actual context? (This breaks agent agnosticism.)

**Self-containment test (applied to every task):**
```
SELF-CONTAINMENT CHECK for [Task ID]:
│ Deliverable described without external references?  [PASS/FAIL]
│ File paths to modify/create are explicit?            [PASS/FAIL]
│ Pattern named with reference implementation path?    [PASS/FAIL]
│ Acceptance criteria in Given/When/Then?              [PASS/FAIL]
│ Dependencies explicit by task ID?                    [PASS/FAIL]
│ Could a cold-start coding agent execute this?        [PASS/FAIL]
```

Any FAIL = the task is not agent-ready. This is a **major finding**.

**Catches:** Vague tasks, untestable acceptance criteria, missing pattern references, implicit dependencies, tasks that are actually 3 tasks pretending to be 1, missed parallelism opportunities.

**Evaluates:** Build Brief (Section 8), JIRA tickets, QA Test Data fixtures, Architecture Scaffolding (are stubs complete enough to code against?).

---

### 5. The First Principles Challenger

**Perspective:** Are we solving the right problem? Are we building what we should build?

**Asks:**
- Why are we building this? (Not "what does the PRD say" — why does this matter?)
- Is there a simpler solution we dismissed too quickly?
- Are we building a new thing when a configuration change would suffice?
- Is the phasing right? Is Phase 1 truly the smallest meaningful slice, or is it still too big?
- Are any Type 2 decisions actually Type 1 decisions in disguise?
- What would we do differently if we had half the time?

**Catches:** Scope creep dressed as requirements, over-engineering, misclassified decisions, "Phase 1" that's actually Phase 1+2+3, cargo-culted patterns.

**Evaluates:** Build Brief (Sections 1, 7, 10), all decision logs.

---

## Gate 0: Static Pre-Checks (Before Council Tokens Are Spent)

Before any persona evaluates, run these static checks against the Build Brief. If any mandatory check fails, reject immediately with the specific failure — do not spend council tokens on a brief that is structurally incomplete.

### Mandatory Checks

Every Build Brief must pass ALL of these before the council convenes:

- [ ] **Existing patterns listed with file paths and reuse instructions** — Section 2 must include a pattern table mapping each pattern to its file path and explicit reuse/extend instructions
- [ ] **Behavior changes documented (current to new)** — Every behavior modification must have a "current behavior" and "new behavior" description, not just the end state
- [ ] **New component file tree specified** — Any new module/service/package must include the complete file tree (directories and files) that will be created
- [ ] **STRIDE threat model complete (all 6 categories)** — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege must each be addressed (even if "N/A — [reason]")
- [ ] **Security concerns table with specific mitigations** — Each identified threat must have a concrete mitigation, not generic advice like "follow best practices"
- [ ] **Failure modes table with impact and specific mitigation** — Every failure mode must include severity/impact rating AND a specific (not generic) mitigation strategy
- [ ] **Backwards compatibility assessed** — Section 10 must explicitly state what breaks, what doesn't, and migration path for any breaking change
- [ ] **Degradation strategy for external dependencies** — Every external dependency must have a documented behavior when that dependency is unavailable
- [ ] **Performance/latency targets defined** — Section 8 must include numeric latency targets per operation (e.g., "p95 < 200ms"), not vague statements like "should be fast"
- [ ] **Per-task: files_to_create/files_to_modify specified** — Every task must list explicit file paths for creation and modification, not just descriptions
- [ ] **Per-task: reference_impl for extensions** — Every task that extends existing code must name the reference implementation file path the coding agent should study
- [ ] **Per-task: dependency_ids form valid DAG** — Task dependency graph must be a directed acyclic graph (no circular dependencies, no missing dependency IDs)
- [ ] **G/W/T roll-up covers all testable behaviors** — Every testable behavior described in the functional spec must have at least one Given/When/Then acceptance criterion
- [ ] **Revision history section present** — Brief must include a revision history table tracking changes across council iterations

### Conditional Checks (Only If Applicable)

These checks apply only when the project has the relevant capability. Skip with justification if not applicable:

- [ ] **Data model changes documented** *(if project has DB)* — New/modified tables, columns, indexes, and migrations must be fully specified with types and constraints
- [ ] **API changes with request/response schemas** *(if project has APIs)* — Every new or modified endpoint must include full request/response JSON schemas with example payloads
- [ ] **Feature flag configuration** *(if project uses flags)* — Flag name, default state, targeting rules, and kill-switch behavior must be specified

### Gate 0 Verdict

```
GATE 0 PRE-CHECK:
│ Mandatory checks passed:  [X/14]
│ Conditional checks:       [X applicable, X passed]
│ Gate 0 verdict:           PASS / FAIL
│
│ If FAIL — return immediately with list of failed checks.
│ Do NOT proceed to council evaluation.
```

---

## Evaluation Process

### Step 1: Select Active Personas

For each evaluation checkpoint, determine which personas are relevant. **All five are active by default.** To exclude one, you must provide a justification:

```
EVAL COUNCIL ASSESSMENT (justify exclusion):
│ Architect:           INCLUDE — new service boundary being introduced
│ Skeptic (Red Team):  INCLUDE — data migration with rollback complexity
│ Operator:            INCLUDE — new on-call responsibilities
│ Executioner:         INCLUDE — 14 tasks need autonomous execution
│ First Principles:    EXCLUDE — scope was already challenged and locked in Phase 0
```

**"Too simple" is not a valid exclusion.** Simple tasks can have hidden assumptions. "Already reviewed by a human" is valid only if the human review was documented.

### Step 2: Independent Evaluation

Each active persona evaluates the output independently. They do not see each other's evaluations. This prevents anchoring bias.

Each persona produces:

```json
{
  "persona": "architect | skeptic | operator | executioner | first_principles",
  "verdict": "PASS | CONCERN | FAIL",
  "findings": [
    {
      "severity": "critical | major | minor | observation",
      "location": "string (section, task ID, file path, or line reference)",
      "finding": "string (what's wrong)",
      "evidence": "string (why this is wrong — cite specific content)",
      "recommendation": "string (how to fix it)",
      "blocks_approval": true
    }
  ],
  "confidence": 0.0-1.0,
  "summary": "string (1-2 sentences)"
}
```

### Step 3: Verdict Synthesis

Individual evaluations are synthesized into a council verdict:

| Condition | Council Verdict | Action |
|-----------|----------------|--------|
| All personas PASS | **APPROVED** | Proceed to next stage |
| Any persona has CONCERN, none FAIL | **APPROVED WITH CONCERNS** | Proceed, but concerns logged and tracked |
| Any persona FAIL with `critical` finding | **BLOCKED** | Cannot proceed until critical findings resolved |
| Any persona FAIL with `major` finding | **REVISION REQUIRED** | Author must address findings, re-submit for eval |
| Multiple personas FAIL | **BLOCKED** | Full re-evaluation required after revision |

### Step 4: Findings Report

The council produces a structured report:

```markdown
## Eval Council Report: [Feature Name]

**Checkpoint:** [Post-Brief | Post-Repo-Analysis | Post-Skill | Pre-Deploy]
**Evaluated:** [what was evaluated]
**Date:** [ISO date]
**Verdict:** [APPROVED | APPROVED WITH CONCERNS | REVISION REQUIRED | BLOCKED]

### Persona Verdicts

| Persona | Verdict | Critical | Major | Minor | Confidence |
|---------|---------|----------|-------|-------|------------|
| Architect | PASS | 0 | 0 | 1 | 0.85 |
| Skeptic | CONCERN | 0 | 2 | 0 | 0.70 |
| Operator | PASS | 0 | 0 | 0 | 0.90 |
| Executioner | FAIL | 1 | 1 | 3 | 0.80 |
| First Principles | EXCLUDE | — | — | — | — |
| | | | | | |
| **Council** | **REVISION REQUIRED** | **1** | **3** | **4** | |

### Critical Findings (must resolve)

**[C-001] Executioner:** Task BE-003 "Add widget endpoint" has no acceptance criteria for error responses.
- **Location:** Section 8, Backend, Task 3
- **Evidence:** Acceptance criteria says "returns 201 on success" but does not specify 400, 401, 404, or 409 behavior.
- **Recommendation:** Add: "Returns 400 with validation errors on invalid input. Returns 401 if unauthenticated. Returns 409 if widget name conflicts."
- **Blocks:** Yes — coding agent will not handle errors without this.

### Major Findings (should resolve)

**[M-001] Skeptic:** Rollback plan assumes feature flag exists, but no task creates the feature flag.
- **Location:** Section 4, Rollback Mechanism
- **Evidence:** Rollback mechanism says "disable via LaunchDarkly flag" but no task in Section 8 creates this flag.
- **Recommendation:** Add task: "Create LaunchDarkly flag `widget-v2-enabled` with kill switch targeting."

**[M-002] Skeptic:** Failure mode FM-003 (database timeout) lists prevention as "add connection pooling" but connection pooling already exists per repo map.
- **Location:** Section 11, FM-003
- **Evidence:** Codebase Research `data_layer` shows Prisma connection pool configured in `src/server/config.ts`.
- **Recommendation:** Update FM-003 prevention to address the actual risk (query optimization, read replica, or timeout tuning).

**[M-003] Executioner:** Backend task 5 estimated at 2h but requires schema migration + backfill + rollback script — this is 3 tasks.
- **Location:** Section 8, Backend, Task 5
- **Recommendation:** Decompose into: (a) migration script 1h, (b) backfill script 1h, (c) rollback script 1h.

### Minor Findings (consider resolving)

[Listed with same format, lower urgency]

### Observations (informational)

[Non-actionable notes for context]
```

---

## Evaluation Criteria by Checkpoint

### Post-Brief Evaluation

The council evaluates the complete Build Brief against these criteria:

**Spec/Plan/Task Separation (Spec Driven Development)**
- [ ] Section 1 (Functional Spec) contains only what, not how — no implementation details
- [ ] Sections 2-6 (Plan) contain technical decisions with codebase references
- [ ] Section 8 (Tasks) are self-contained — each embeds all context needed
- [ ] Acceptance criteria are Given/When/Then throughout (Section 1 and Section 8)
- [ ] No task references "the spec" or "as discussed" — context is embedded, not pointed at

**Completeness**
- [ ] All 12 sections present and filled (not placeholder text)
- [ ] Every task has G/W/T acceptance criteria, pattern reference, and reference implementation path
- [ ] Every failure mode has prevention, mitigation, and early warning
- [ ] Every Type 1 decision has a named owner and deadline
- [ ] SLO targets are numeric and measurable
- [ ] On-call rotation and escalation path have real names

**Consistency**
- [ ] Architecture patterns in Section 2 match what Codebase Research found
- [ ] Task breakdown references correct file paths (verified against repo map)
- [ ] Failure modes in Section 11 match failure modes in per-phase tables
- [ ] SLO targets are achievable given current system performance (from repo map observability)
- [ ] Estimated hours are realistic (calibrated against similar tasks in repo history)

**Task Self-Containment & Parallelism**
- [ ] Every task passes the self-containment checklist (deliverable, file paths, pattern, G/W/T, dependencies)
- [ ] No task exceeds 2h estimate (decomposed if larger)
- [ ] Independent tasks are flagged for parallel execution
- [ ] Dependency chain is a DAG (no circular dependencies)
- [ ] Parallel execution groups are identified

**Executability**
- [ ] A coding agent with only the Build Brief and repo map could produce working code
- [ ] A coding agent with only a single task ticket could produce working code for that task (agent agnostic)
- [ ] A QA agent with only the G/W/T acceptance criteria could produce deterministic tests
- [ ] An on-call engineer with only the runbook could diagnose and mitigate an incident

### Post-Repo-Analysis Evaluation

- [ ] All 12 analysis sections produced non-empty output
- [ ] File paths referenced in the repo map actually exist
- [ ] Tech stack detection matches package manifests
- [ ] Architecture pattern detection is accurate (spot-check 3 reference files)
- [ ] Risk areas include quantitative evidence (change frequency, file size, coupling)
- [ ] Security findings are real (not false positives from grep patterns)

### Post-Skill-Output Evaluation

Per-skill criteria (in addition to each skill's own quality gates):

| Skill | Key Eval Criteria |
|-------|------------------|
| JIRA | Every task from brief has a ticket. No ticket exceeds 2h. Dependencies are linked. |
| Confluence | Page hierarchy matches structure. Mermaid renders. Type 1 warnings visible. |
| QA | Tests are deterministic (no randomness). Every AC has a test. Edge cases are real edge cases. |
| CI/CD | Workflows match repo conventions. Secrets exist. Rollback mechanism matches brief. |
| Scaffolding | Ports match existing conventions. Domain has no infra imports. Files compile. |
| Runbook | Every step is executable (commands, not descriptions). Escalation path has names. |

### Pre-Deploy Evaluation

- [ ] All Phase 1 JIRA tickets marked done
- [ ] CI pipeline passes (green build)
- [ ] QA test suite passes (all deterministic tests green)
- [ ] Runbook populated (not shell)
- [ ] SLO dashboards exist and show data
- [ ] On-call rotation confirmed
- [ ] Feature flag created (if rollback plan depends on it)
- [ ] No unresolved critical/major findings from previous eval rounds

### Post-Incident Evaluation (Learning Loop)

- [ ] Was this failure mode predicted in the Build Brief?
- [ ] If yes: was the prevention measure implemented? Was the early warning configured?
- [ ] If no: what question should the Build Brief Agent have asked to surface it?
- [ ] Was the runbook useful? What was missing?
- [ ] Was the escalation path followed? Did it work?
- [ ] **Output:** Concrete improvements to the Build Brief Agent spec, eval criteria, or skill definitions.

---

## Cross-Referencing: Repo Map as Ground Truth

The Eval Council uses the Codebase Research repo map as ground truth for verification. This is what makes evaluation concrete rather than theoretical.

**Example cross-references:**

| Brief Claims | Repo Map Validates |
|-------------|-------------------|
| "We'll add a new endpoint to WidgetRouter" | `api_surface.endpoint_groups` confirms WidgetRouter exists at stated path |
| "Follow ports-and-adapters pattern" | `architecture.pattern` confirms this is the convention |
| "Tests will use Vitest" | `testing.framework` confirms Vitest is the test framework |
| "Deploy via Argo canary" | `ci_cd.deployment_strategy` confirms Argo Rollouts with canary |
| "Rollback via feature flag" | `tech_stack.feature_flags` confirms LaunchDarkly is in use |
| "Error rate < 0.1% target" | `observability.existing_slos` shows whether any SLOs exist to baseline against |
| "Schema migration for widgets table" | `data_layer.models` confirms Widget model exists; `data_layer.migration_patterns` shows how migrations are done |

If the brief claims something that contradicts the repo map, the Skeptic persona flags it as a **critical finding**.

---

## MCP Server Contract

### Tool: `evaluate_output`

```json
{
  "name": "evaluate_output",
  "description": "Run the Eval Council against a Build Brief, skill output, or deployment state",
  "inputSchema": {
    "type": "object",
    "properties": {
      "checkpoint": {
        "type": "string",
        "enum": ["post_brief", "post_repo_analysis", "post_skill_output", "pre_deploy", "post_incident"],
        "description": "Which evaluation checkpoint"
      },
      "content": {
        "type": "string",
        "description": "The content to evaluate (markdown, JSON, or YAML)"
      },
      "repo_map": {
        "type": "string",
        "description": "Repo map JSON from Codebase Research skill (used as ground truth)"
      },
      "exclude_personas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Personas to exclude WITH justification objects"
      },
      "previous_findings": {
        "type": "string",
        "description": "Previous eval report (for re-evaluation after revision)"
      }
    },
    "required": ["checkpoint", "content"]
  }
}
```

### Tool: `evaluate_decision`

```json
{
  "name": "evaluate_decision",
  "description": "Run council evaluation on a specific Type 1 decision",
  "inputSchema": {
    "type": "object",
    "properties": {
      "decision_description": {
        "type": "string",
        "description": "The decision to evaluate"
      },
      "options": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Available options"
      },
      "context": {
        "type": "string",
        "description": "Relevant context from the Build Brief"
      },
      "repo_map_section": {
        "type": "string",
        "description": "Relevant repo map section"
      }
    },
    "required": ["decision_description", "options", "context"]
  }
}
```

### Tool: `check_findings_resolved`

```json
{
  "name": "check_findings_resolved",
  "description": "Verify that critical and major findings from a previous eval have been addressed",
  "inputSchema": {
    "type": "object",
    "properties": {
      "previous_report": {
        "type": "string",
        "description": "Previous eval council report"
      },
      "updated_content": {
        "type": "string",
        "description": "Updated content after revision"
      }
    },
    "required": ["previous_report", "updated_content"]
  }
}
```

---

## CLI Interface

```bash
# Evaluate a build brief
adlc-eval brief --input ./build-brief.md --repo-map ./repo-map.json --output ./eval-report.md

# Evaluate a specific skill output
adlc-eval skill --skill jira --input ./jira-tickets.json --repo-map ./repo-map.json

# Evaluate with persona exclusion (must provide justification)
adlc-eval brief --input ./build-brief.md --exclude "first_principles:scope locked in Phase 0"

# Re-evaluate after revision
adlc-eval brief --input ./build-brief-v2.md --previous ./eval-report-v1.md

# Evaluate a Type 1 decision
adlc-eval decision --description "Change auth provider from Clerk to Auth0" \
  --options "Keep Clerk" "Migrate to Auth0" "Abstract behind port" \
  --context ./build-brief.md

# Pre-deploy check
adlc-eval deploy --epic ENG-123 --repo-map ./repo-map.json

# Post-incident learning
adlc-eval incident --incident-report ./incident.md --build-brief ./build-brief.md
```

---

## Integration with ADLC Workflow

**The Council is a loop, not a gate.** When the Council fails a brief, the Build Brief Agent revises and re-submits automatically. The human never sees a rejected brief. The human sees only the final, Council-approved package.

```
Build Brief Agent completes
  │
  ├─→ Eval Council (post_brief checkpoint)
  │     │
  │     ├── APPROVED → proceed to preparation phase
  │     │
  │     ├── REVISION REQUIRED → ┐
  │     │                        ├─→ Build Brief Agent revises based on findings
  │     │                        ├─→ Re-submit to Eval Council
  │     │                        └─→ Max 3 iterations, then escalate to human
  │     │
  │     └── BLOCKED (after 3 iterations) → Escalate to engineer with all findings
  │
  ├─→ Skills execute (Confluence, JIRA, Scaffolding, QA Tests)
  │     │
  │     └─→ Eval Council (post_skill_output, per skill)
  │           ├── APPROVED → output committed
  │           └── REVISION REQUIRED → skill re-runs with findings (auto-retry)
  │
  ├─→ Codegen executes (coding agents make tests pass)
  │
  ├─→ Eval Council (pre_deploy checkpoint)
  │     │
  │     ├── APPROVED → package ready for human review
  │     └── BLOCKED → flag issues, coding agent fixes, re-verify
  │
  ├─→ ════════════════════════════════════════════════
  │    SINGLE HUMAN GATE: Engineer reviews complete package
  │    - Research deliverable
  │    - Build Brief (Council-approved)
  │    - Council report (what was validated)
  │    - PR with generated code
  │    - All tests green
  │    - Runbook
  │    ════════════════════════════════════════════════
  │     │
  │     ├── APPROVED → deploy
  │     └── CHANGES REQUESTED → loop back to Build Brief with feedback
  │
  └─→ [If incident occurs post-deploy]
        │
        └─→ Eval Council (post_incident checkpoint)
              │
              └── Learning output → feeds back into Build Brief Agent + Council criteria
```

### Auto-Revision Behavior

When the Council returns REVISION REQUIRED:

1. **Findings are structured** — each has a specific location, evidence, and recommendation
2. **Build Brief Agent applies recommendations** — not guessing, following specific instructions
3. **Only affected sections are revised** — unchanged sections are preserved
4. **Re-submission includes a diff** — what changed and why, referencing the Council finding ID
5. **Council re-evaluates only changed sections** — faster second pass
6. **After 3 iterations without PASS** — escalate to human with full history of findings and revisions

Typical iteration count:
- Simple briefs (clear PRD, clean codebase): 1 iteration (passes first time)
- Moderate briefs (some ambiguity): 2 iterations
- Complex briefs (many integration points, tech debt): 2-3 iterations
- 3+ iterations (rare): indicates a fundamental issue the agent can't resolve — needs human judgment

### Slack Integration

The Eval Council posts its verdicts through the Slack Orchestration Skill:

**APPROVED:**
```
✅ *Eval Council: [Feature Name] — APPROVED*
5/5 personas passed. 2 minor observations logged.
Ready for engineer review.
```

**REVISION REQUIRED:**
```
⚠️ *Eval Council: [Feature Name] — REVISION REQUIRED*
3 critical findings, 2 major findings.

*Critical:*
• [C-001] Task BE-003 has no error handling acceptance criteria
• [C-002] Rollback plan references non-existent feature flag
• [C-003] Schema migration has no rollback script task

@[owner] — findings attached. Please revise and re-submit.
```

**BLOCKED:**
```
🚫 *Eval Council: [Feature Name] — BLOCKED*
Multiple personas flagged critical issues.

*Architect:* Service boundary violation — domain imports infrastructure
*Skeptic:* Rollback plan is not executable
*Executioner:* 6 of 14 tasks have vague acceptance criteria

This brief cannot proceed to approval. @[owner] — see full report.
```

---

## Quality Gates for the Eval Council Itself

The Eval Council must also be evaluated. These meta-criteria prevent the council from becoming rubber-stamp theater:

- [ ] **Finding specificity:** Every finding cites a specific location, specific evidence, and specific recommendation. "Could be better" is not a finding.
- [ ] **False positive rate:** Track findings that engineers dismiss as invalid. If > 20% of findings are dismissed, the evaluation criteria need recalibration.
- [ ] **False negative rate:** Track issues found in production that the council missed. Every miss triggers a post-incident eval and criteria update.
- [ ] **Evaluation time:** Council evaluation should complete in < 5 minutes for a standard brief. If it takes longer, the brief is probably too complex.
- [ ] **Actionability:** Every critical/major finding has a recommendation that can be acted on immediately. "Be more careful" is not a recommendation.
- [ ] **Consistency:** Same input should produce materially similar verdicts across runs. Track verdict stability.
- [ ] **Persona coverage:** If a persona is excluded in > 50% of evaluations, the exclusion criteria may be too loose.
