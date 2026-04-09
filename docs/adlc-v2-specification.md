# ADLC v2 Specification

**Version:** 2.0
**Date:** 2026-04-05
**Status:** Draft
**Scope:** Universal — governs SWElfare, Ratatosk, Magnus, and all future Torbin Network agents

---

## 0. Governing Philosophy

### 0.1 Bitter Lesson Engineering (BLE)

> Specify outcomes and constraints, never procedures. The ADLC defines *what must be true* at each stage, not *how the agent should code*.

**Core rules:**
- Tickets define problems, context, and success criteria — never solution code
- Every piece of scaffolding must get simpler over time, not more complex
- Invest in verification (tests, linters, security scans, councils), not guidance (step-by-step instructions)
- Provide the best tools and richest context, then let the agent work
- A system that needs more guardrails as models improve is BLE-violating

**Anti-pattern:** Adding orchestration complexity to compensate for model limitations. If a workaround exists because today's model can't do X, wrap it so it can be removed when models can.

### 0.2 Bitter Pilled Engineering (BPE)

> Whatever structure you build, ensure it gets *better* — not worse — as models improve.

**Core rules:**
- Gates test outcomes (does the code have vulnerabilities?) not process (did the agent follow secure coding guidelines?)
- Every structural decision must be anti-fragile to smarter models
- If a gate would handicap a more capable model, it is BPE-violating
- Design for removal: every scaffolding component should have a clear "remove when" condition

**Quarterly audit question:** "What structure can we remove because the models no longer need it?"

### 0.3 Skills as Actions

Skills are contextual behaviors, not static prompts. A skill is something the agent *does*, not something the agent *reads*.

**Properties of a well-designed skill:**
1. **Context-triggered:** Activates automatically based on pipeline state and domain tags, not manual invocation (manual override preserved)
2. **Scoped execution:** Runs in isolated context, results compressed back to the pipeline — does not pollute main context
3. **Chainable:** Can be composed into orchestration sequences where output of skill N feeds input of skill N+1
4. **Self-improving:** Feedback loops record diffs between agent output and human edits; patterns distilled and written back to the skill definition
5. **Outcome-defined:** Skill specifies exit criteria (verifiable outcomes), not step-by-step procedures

**Skill lifecycle:**
```
Trigger (context match or manual) → Activate (load into isolated context) → Execute (produce output) → Verify (exit criteria met?) → Deactivate (compress results, release context) → Feedback (record human edits, update skill)
```

### 0.4 The Three Loops

ADLC v2 operates three concurrent loops:

```
┌─────────────────────────────────────────────────────────┐
│                     BUILD LOOP                          │
│  Intake → PRD → Brief → Council → Execute → Ship       │
└────────────────────────┬────────────────────────────────┘
                         │ shares codebase
┌────────────────────────┴────────────────────────────────┐
│                      FIX LOOP                           │
│  Capture → Confirm → Investigate → Fix → Prove → Ship  │
└────────────────────────┬────────────────────────────────┘
                         │ feeds learning store
┌────────────────────────┴────────────────────────────────┐
│                    FEEDBACK LOOP                         │
│  Human edits → Diff capture → Pattern distill → Update  │
└─────────────────────────────────────────────────────────┘
```

The Build Loop ships features. The Fix Loop repairs production. The Feedback Loop makes both loops better over time. All three run independently and concurrently.

---

## 1. The Build Loop Pipeline

### Phase Map

```
Phase -1: Intake & Scope Routing
Phase  0: PRD Agent (structured discovery)
Phase  1: Build Brief (technical design + security + observability + reuse)
Phase  2: Eval Council — HEAVY GATE (post-brief)
Phase  3: Scaffold + Codegen Context Assembly
Phase  4: Execution (LDD → TDD → Implement)
Phase  5: Post-Execution Quality Gate — HEAVY GATE
Phase  6: PR + Ship
```

---

### Phase -1: Intake & Scope Routing

**Purpose:** Classify every input before it enters the pipeline. No ambiguous inputs pass.

**Inputs:** GitHub issue, market signal, content bookmark, error alert, human request, cross-agent handoff.

**Classification outputs:**

| Field | Values | Purpose |
|-------|--------|---------|
| Scope | NARROW / WIDE | Determines decomposition depth |
| Risk tier | Routine / Elevated / Critical | Determines council weight |
| Domain tags | Auto-detected | Determines skill activation |
| Origin type | delegated / cron-triggered / finding-generated / cross-agent / fix-loop | Traceability |

**Routing thresholds (configurable per repo):**

| Threshold | Default | Controls |
|-----------|---------|----------|
| FILE_THRESHOLD | 8 | Files touched → WIDE if exceeded |
| SUBSYSTEM_THRESHOLD | 2 | Subsystems touched → WIDE if exceeded |
| LOC_THRESHOLD | 300 | Lines changed → WIDE if exceeded |
| CONCERN_MIX_THRESHOLD | 3 | Distinct concerns → WIDE if exceeded |

**Exit criteria:**
- [ ] Input classified with scope, risk tier, domain tags, and origin
- [ ] Ambiguous inputs rejected with specific questions back to requester
- [ ] Pipeline audit log entry created: `{ phase: -1, input_id, scope, risk_tier, domain_tags, origin, timestamp }`

---

### Phase 0: PRD Agent (Structured Discovery)

**Purpose:** Force specificity before any design work begins. Ambiguity caught here costs 1x to fix; ambiguity caught in execution costs 100x.

**Interaction model:** 3-5 conversational turns maximum. Not a 20-question interview. Extract first (from input + codebase), ask second (only about gaps). BLE-compliant: don't over-process.

**PRD output contract:**

```markdown
## Problem Statement
- What: (the problem, not the solution)
- Why: (business/user impact)
- For whom: (affected personas/systems)

## Success Metrics
- (measurable outcomes, not activity)

## Out of Scope
- (explicit exclusions with rationale for each)

## Constraints
- (what this ISN'T — antipatterns, approaches that are OFF LIMITS)
- (architecture boundaries that must not be crossed)
- (known failure modes from prior attempts)

## Dependencies & Risks
- (upstream/downstream, external, timing)

## Personas / Consumers
- (who/what is affected and how)
```

**Domain adaptation:**

| Domain | PRD manifests as |
|--------|-----------------|
| SWElfare | Engineering PRD: feature spec, API contracts, user stories, system boundaries |
| Ratatosk | Trade thesis: market context, conviction rationale, risk parameters, exit criteria, position sizing logic |
| Magnus | Content brief: topic, angle, ICP target, platform, voice constraints, format, anti-slop rules |

**Council gate:** None. This is intake, not a decision point.

**Exit criteria:**
- [ ] Problem statement is explicit and specific
- [ ] Success metrics are measurable
- [ ] Out of scope is explicit with rationale
- [ ] Constraints and antipatterns are listed
- [ ] No ambiguous language ("improve," "enhance," "better" without quantification)
- [ ] Pipeline audit log entry: `{ phase: 0, prd_id, problem_hash, constraint_count, timestamp }`

---

### Phase 1: Build Brief

**Purpose:** Convert PRD into an executable technical design that an autonomous agent can pick up cold and build without exploratory reads.

**The brief is the contract.** Everything the executor needs must be in the brief. If it's not in the brief, it doesn't get built.

#### 1.1 Task Decomposition

Decompose into verifiable outcomes, not implementation steps (BLE). Each task is binary: done or not done.

Per task:
- `task_id`, `title`, `description`
- `problem_statement` (what this task solves)
- `acceptance_criteria` (binary, testable)
- `gwt_criteria` (Given/When/Then — feeds TDD)
- `file_targets` (files to create or modify)
- `inlined_context` (zero-read code snippets — the executor never needs to read a file)

#### 1.2 STRIDE Threat Model

**Mandatory for every task.** Security is not optional, not a separate review — it is baked into the design.

| Threat | Analysis | Risk | Mitigation Required |
|--------|----------|------|-------------------|
| **S**poofing | Can an attacker impersonate a legitimate actor? | L/M/H/C | |
| **T**ampering | Can data be modified in transit or at rest? | L/M/H/C | |
| **R**epudiation | Can actions be denied without evidence? | L/M/H/C | |
| **I**nformation Disclosure | Can sensitive data leak? | L/M/H/C | |
| **D**enial of Service | Can availability be degraded? | L/M/H/C | |
| **E**levation of Privilege | Can an actor gain unauthorized access? | L/M/H/C | |

**Per-task output:** Mitigations that must appear in the implementation. These become security contracts in the codegen context.

**Domain adaptation:**

| Domain | STRIDE focus |
|--------|-------------|
| SWElfare | Traditional software STRIDE: auth, input validation, data protection, rate limiting, privilege separation |
| Ratatosk | Trade execution STRIDE: order spoofing, parameter tampering, trade repudiation, API key disclosure, exchange DoS, privilege escalation to autonomous mode |
| Magnus | Brand/reputation STRIDE: voice impersonation, content tampering, attribution repudiation, PII disclosure, publish flooding, unauthorized tone override |

#### 1.3 Availability & Scalability Analysis

Per task, document:
- **Load expectations:** reads/writes per second, concurrent users/requests
- **Failure modes:** what breaks under load, what degrades gracefully
- **Degradation strategy:** circuit breakers, fallbacks, queue-based backpressure
- **Horizontal scaling path:** what would need to change to 10x throughput
- **SLA impact:** which SLOs are affected by this change

#### 1.4 Observability Contract

**Every feature or change must include logging.** This is a mandatory deliverable, not an afterthought.

| Log Type | What Must Be Captured | Format | Level |
|----------|----------------------|--------|-------|
| **Error** | Exception context, stack trace, input state, correlation ID, upstream caller | Structured JSON | ERROR |
| **Audit** | State changes: who, what, when, from-state, to-state. Immutable append-only. | Structured JSON | INFO |
| **General** | Operational metrics, health signals, debug breadcrumbs, timing data | Structured JSON | Configurable |

**Rules:**
- Every public function that can fail must have error logging
- Every state mutation must have an audit log entry
- Every external API call must log request/response metadata (not bodies — PII risk)
- Log format and destination are specified per-repo in config, not invented per-task
- Correlation IDs must propagate across service boundaries

#### 1.5 Reuse Analysis

**Before building anything new, prove that it doesn't already exist.**

Per task:
- **Existing patterns to continue:** Functions, utilities, abstractions that MUST be reused (DO NOT REIMPLEMENT)
- **Existing conventions to follow:** Naming, error handling, config patterns already established in the codebase
- **Antipatterns to avoid:** Known bad patterns in the codebase that must not be repeated
- **Prior art:** Previous implementations of similar functionality (in this repo or sibling repos)

The reuse analysis uses AST-based discovery + keyword matching + LLM-filtered relevance scoring (existing SWElfare `reuse_discovery.py` pattern, universalized).

#### 1.6 Antipatterns / Constraints / "What This Isn't"

A dedicated section in every brief that explicitly states:
- Approaches that are OFF LIMITS (with rationale)
- Architecture boundaries that must not be crossed
- Known failure modes from prior attempts
- Things this task is NOT (common misinterpretations)
- Frameworks, libraries, or patterns that must NOT be introduced

This section feeds directly into the "What NOT to Do" section of the codegen context.

#### 1.7 Definition of Done (Per Task)

Every task carries its own DoD checklist. A task is not complete until every item is verified:

- [ ] All linters pass (LDD gate)
- [ ] All tests pass (TDD gate)
- [ ] Logging implemented per observability contract (error + audit + general)
- [ ] STRIDE mitigations implemented per threat model
- [ ] OWASP Top 10 scan clean on the diff
- [ ] Slop gate passed (code slop + content slop where applicable)
- [ ] Reuse analysis confirmed (no reimplementation of existing utilities)
- [ ] Scalability concerns documented and addressed
- [ ] Antipattern checklist cleared
- [ ] Integration wiring complete (upstream callers, downstream dependencies, registration)

**Exit criteria for Phase 1:**
- [ ] All tasks have binary acceptance criteria
- [ ] STRIDE threat model complete for every task
- [ ] Observability contract specified
- [ ] Reuse analysis complete
- [ ] Antipatterns/constraints listed
- [ ] DoD checklist attached to every task
- [ ] Pipeline audit log: `{ phase: 1, brief_id, task_count, stride_threats_identified, reuse_items_found, timestamp }`

---

### Phase 2: Eval Council — HEAVY GATE (Post-Brief)

**Purpose:** Multi-perspective adversarial review before any code is written. Catch design failures when they're cheap to fix.

**Opt-OUT, not opt-IN.** Every brief gets council review by default. Exclusion requires explicit justification logged in the audit trail.

#### 2.1 Council Composition

Six personas evaluate independently, then synthesize:

| Persona | Focus | Key questions |
|---------|-------|--------------|
| **Architect** | System fit, boundaries, blast radius, scalability | Does this respect existing architecture? What's the blast radius if it fails? |
| **Skeptic (Red Team)** | Assumptions, failure modes, edge cases | What assumptions are untested? Where will this break? |
| **Operator** | Production reality, observability, runbooks, SLOs | Can I debug this at 3am? Are the logs sufficient? |
| **Executioner** | Agent executability, self-containment, zero-read completeness | Can an autonomous agent build this without asking questions? Is all context inlined? |
| **Security Auditor** | STRIDE validation, OWASP applicability, trust boundaries, secrets | Is the STRIDE model complete? Are mitigations sufficient? Any OWASP Top 10 exposure? |
| **First Principles** | Problem validity, scope correctness, BLE compliance | Are we solving the right problem? Is the scope right? Are we over-engineering? |

#### 2.2 Review Protocol

- **3 rounds** of independent evaluation
- **Peer review** of round summaries (personas challenge each other)
- **Chairman synthesis** merges all findings into a unified verdict
- **Max 3 revision loops** — if the brief can't pass after 3 revisions, escalate to human

#### 2.3 Verdicts

| Verdict | Action |
|---------|--------|
| **APPROVED** | Proceed to Phase 3 |
| **APPROVED WITH CONCERNS** | Proceed, concerns logged as tech debt or follow-up tasks |
| **REVISION REQUIRED** | Brief returns to Phase 1 with specific feedback. Feedback enriches the next attempt. |
| **BLOCKED** | Cannot proceed. Critical issue requires human decision. |

#### 2.4 Static Checks (Always Run, Pre-Council)

These are automated and non-negotiable:
- [ ] Zero-read context present for every task
- [ ] TDD protocol (G/W/T criteria) present for every task
- [ ] Anti-slop rules present
- [ ] STRIDE threat model present for every task
- [ ] Observability contract present
- [ ] Reuse analysis present
- [ ] DoD checklist present for every task

If any static check fails, the brief is returned to Phase 1 without consuming council tokens.

**Exit criteria:**
- [ ] Council verdict is APPROVED or APPROVED WITH CONCERNS
- [ ] All static checks pass
- [ ] Pipeline audit log: `{ phase: 2, brief_id, verdict, revision_count, persona_scores, static_check_results, timestamp }`

---

### Phase 3: Scaffold + Codegen Context Assembly

**Purpose:** Assemble everything the executor needs into a single, self-contained prompt per task. The executor should be able to start coding immediately with zero exploratory reads.

#### 3.1 Context Assembly (Per Task)

The assembled context document contains:

```markdown
## 1. Your Mission
(Problem statement + acceptance criteria)

## 2. What You're Building
(Task description + GWT criteria)

## 3. Tests You Must Pass
(Full test file content inlined — not referenced, PASTED)

## 4. Files to Modify or Create
(Table: file path, what to do, specific instructions)
(Full current content of each file inlined)

## 5. Reference Implementations
(Existing patterns to follow — code inlined)

## 6. Reusable Functions — DO NOT REIMPLEMENT
(Functions from reuse analysis with signatures, docstrings, file paths)

## 7. Schema / Types
(Relevant type definitions, API contracts inlined)

## 8. What NOT to Do
(From brief's antipatterns section + reuse analysis violations)
(Known failure modes from prior attempts)
(Architecture boundaries)

## 9. Security Contract
(STRIDE mitigations that MUST appear in the code)
(Trust boundaries to enforce)
(Input validation requirements)

## 10. Observability Contract
(Required error logging points)
(Required audit log entries)
(Required operational metrics)
(Log format specification)

## 11. Lint Configuration
(Which linters, which rulesets, which commands to run)
(Must pass BEFORE test execution)

## 12. Scale Considerations
(Load expectations, failure modes, degradation strategy)

## 13. Integration Wiring
(Upstream callers, downstream dependencies, factory registrations)

## 14. Module Health Constraints
(Complexity budgets, SLOC ceilings, existing tech debt)

## 15. Anti-Slop Rules
(Prohibited patterns: placeholders, TODOs, god functions, duplicates, hardcoded values)

## 16. Verification
(Commands to run: lint, test, security scan)
(Expected output for pass)

## 17. Definition of Done
(Complete checklist — all must be green before task is complete)
```

#### 3.2 Parallel Task Dispatch

Tasks flagged `parallel: true` get separate context documents and can be dispatched simultaneously to independent executors. Dependencies are respected — only independent tasks run in parallel.

#### 3.3 Architecture Scaffolding (When Applicable)

For tasks requiring new modules, interfaces, or structural additions:
- Generate port interfaces (following repo convention: trait, interface, ABC, protocol)
- Generate adapter stubs (extends port, has TODO-with-ticket-reference markers)
- Generate domain types (entities, value objects, enums)
- Generate wiring/registration (DI bindings, factory registrations)
- Generate directory structure (following existing conventions)

**Exit criteria:**
- [ ] Every task has a self-contained context document
- [ ] Zero-read principle verified: no file references without inlined content
- [ ] "What NOT to Do" section present
- [ ] Security contract present
- [ ] Observability contract present
- [ ] Lint configuration present
- [ ] Pipeline audit log: `{ phase: 3, brief_id, tasks_assembled, parallel_tasks, scaffold_generated, timestamp }`

---

### Phase 4: Execution (LDD → TDD → Implement)

**Purpose:** Build the thing. Three enforcement layers run in sequence per task.

#### 4.1 Step 1: LDD (Lint-Driven Development) — Formatting & Syntax Gate

**LDD ensures the code is structurally sound before testing begins.**

Sequence:
1. Run all configured linters, formatters, and type-checkers
2. Fix all violations
3. Re-run until clean
4. Only then proceed to TDD

**What LDD covers:**
- Code style and formatting (black, prettier, rustfmt, etc.)
- Type safety (mypy, tsc, etc.)
- Import ordering and dead import removal
- Dead code detection
- Naming convention enforcement
- File structure conventions

**Enforcement:** Lint violations block test execution. A task cannot enter TDD until LDD is clean. This is not advisory — it is a hard gate.

**BPE note:** LDD checks outcomes (does the code pass lint?) not process (did the agent format before writing?). If future models produce lint-clean code natively, this gate becomes a no-op and can be removed.

#### 4.2 Step 2: TDD (Test-Driven Development) — Success Criteria Gate

**TDD ensures every acceptance criterion has a corresponding test that proves it works.**

The Iron Law: No production code without a failing test first.

**RED-GREEN-REFACTOR cycle per G/W/T criterion:**

1. **RED:** Write a failing test from the G/W/T acceptance criterion
   - Test MUST fail before any implementation
   - If test passes without code → STOP, investigate (criterion already satisfied or test is wrong)
   - Test includes: unit test for the criterion + security test for STRIDE mitigations + observability test for required log entries

2. **GREEN:** Write minimal code to make the test pass
   - Don't add untested behavior
   - Don't optimize prematurely
   - Run test after each change

3. **REFACTOR:** Clean up, then commit
   - Run full task tests
   - Run full suite for regressions
   - Run linters (LDD re-check)
   - Commit atomically per criterion

**Repeat for each G/W/T criterion in the task.**

**Two modes:**
- **Mode A:** Pre-written tests exist (from QA test data generation) → RED step = verify existing test fails
- **Mode B:** No pre-written tests → RED step = agent writes test from G/W/T criteria

**Violations that block:**
- Code committed without a failing test first → BLOCKED
- Test passes on first run → INVESTIGATE (the test may be wrong or the criterion is already met)
- Test modified to match broken code → BLOCKED (fix the code, not the test)
- Multiple criteria in one cycle → DECOMPOSE (one cycle per criterion)

#### 4.3 Step 3: Implementation Verification

After all TDD cycles complete, verify the full Definition of Done:

- [ ] All linters pass (LDD — re-verify after all changes)
- [ ] All tests pass (TDD — full suite, not just task tests)
- [ ] Logging implemented per observability contract
- [ ] STRIDE mitigations implemented per security contract
- [ ] Reuse confirmed (no reimplementation — AST check + LLM review)
- [ ] Integration wiring complete
- [ ] Anti-slop scan clean on the diff

**Council gate:** None during execution. Let the agent work (BLE). The post-execution gate catches problems.

**Exit criteria:**
- [ ] All DoD items verified
- [ ] Pipeline audit log: `{ phase: 4, task_id, ldd_pass, tdd_cycles, tests_written, tests_passed, slop_violations, security_mitigations_implemented, logging_points_added, timestamp }`

---

### Phase 5: Post-Execution Quality Gate — HEAVY COUNCIL

**Purpose:** Independent verification of the implementation. The executor does not mark its own homework.

#### 5.1 Automated Checks (Always Run)

These are non-negotiable, run on every task:

| Check | Tool | Blocks on |
|-------|------|-----------|
| **LDD** | Configured linters/formatters/type-checkers | Any violation |
| **TDD** | Test runner | Any failure, coverage below threshold |
| **OWASP Top 10** | SAST scanner on the diff | Any High/Critical finding |
| **Code slop** | Anti-slop scanner | Placeholders, TODOs, god functions (SLOC > ceiling), near-duplicates, hardcoded values, identity transforms, unnecessary defensive code |
| **Content slop** | Stop-slop scanner (for human-facing output) | Score below 35/50 threshold |
| **Observability** | AST scan for required log statements | Missing required error/audit/general logging per contract |
| **Reuse** | AST + LLM comparison against reuse analysis | Reimplementation of existing utilities |
| **Complexity** | Cyclomatic complexity + SLOC per function | CC > ceiling (default 15), SLOC > ceiling without decomposition |

#### 5.2 Stop Slop — Dual Mode

**Code slop (all repos):**
- Placeholder detection: `pass`, `TODO`, `FIXME`, `NotImplementedError`, `...`
- God function growth: SLOC exceeds ceiling without decomposition
- Near-duplicate code blocks
- Identity transforms in comprehensions
- Unnecessary defensive comparisons
- Hardcoded URLs, ports, timeouts outside config files
- Missing integration wiring
- Missing TDD protocol

**Content slop (human-facing output):**

The Eight Rules:
1. Active voice. Human subjects.
2. Cut all adverbs (-ly words)
3. No throat-clearing openers
4. No binary contrasts ("Not X. But Y.")
5. No rhetorical setups ("Here's what I mean:")
6. No vague declaratives
7. No dramatic fragmentation (staccato lists)
8. Specificity over abstraction

Banned phrases: "Here's the thing," "The uncomfortable truth is," "Let me be clear," "Full stop," "Make no mistake," navigate, unpack, lean into, landscape, game-changer, synergy, really, just, literally, genuinely, honestly, simply, actually, deeply, truly, "At its core," "In today's," "It's worth noting," "As we'll see," "Let me walk you through"

5-Dimension Scoring (1-10 each, total /50):
- Directness (filtering/softening)
- Rhythm (sentence length variation)
- Trust (authenticity, no false sincerity)
- Authenticity (specificity, concrete detail)
- Density (compression, no filler)

**Thresholds:**
- 35/50: minimum to proceed to human review
- 38/50: minimum for outreach/external content

**Content slop applies to:**

| Repo | What gets slop-gated |
|------|---------------------|
| SWElfare | PR descriptions, issue comments, documentation, error messages |
| Ratatosk | Morning briefings, Telegram messages, trade summaries, performance reports |
| Magnus | ALL content output (this is Magnus's primary product) |

#### 5.3 Council Review (Elevated/Critical Risk Tiers)

Same 6 personas as Phase 2, but reviewing the *actual implementation* against the *brief*:

| Persona | Reviews for |
|---------|------------|
| **Architect** | Does the implementation respect the architecture? Any unintended coupling? |
| **Skeptic** | What edge cases are untested? What will break in production? |
| **Operator** | Are the logs sufficient? Can I debug this? Are health checks adequate? |
| **Executioner** | Is the implementation complete per the brief? Any gaps? |
| **Security Auditor** | Are STRIDE mitigations actually implemented and correct? OWASP findings addressed? |
| **First Principles** | Did we over-engineer? Is the solution proportional to the problem? (BLE check) |

**Verdicts:**
- APPROVED → proceed to Phase 6
- REVISION REQUIRED → return to Phase 4 with specific feedback (max 3 revision loops)

#### 5.4 Routine Risk Tier

For Routine risk tasks, skip the full council. Run automated checks only. If all automated checks pass, proceed to Phase 6.

**Exit criteria:**
- [ ] All automated checks pass
- [ ] Council verdict APPROVED (for Elevated/Critical) or automated-only pass (for Routine)
- [ ] Pipeline audit log: `{ phase: 5, task_id, automated_check_results, council_verdict, slop_scores, owasp_findings, complexity_report, timestamp }`

---

### Phase 6: PR + Ship

**Purpose:** Package the work for human review and merge.

#### 6.1 PR Creation

Every PR includes:

```markdown
## Summary
(What changed and why — 1-3 bullet points)

## STRIDE Summary
(Threats identified and mitigations implemented)

## Observability
(Logging added: error points, audit entries, operational metrics)

## Definition of Done
- [x] All linters pass
- [x] All tests pass (N new, M total)
- [x] Logging per observability contract
- [x] STRIDE mitigations implemented
- [x] OWASP scan clean
- [x] Slop gate passed
- [x] Reuse confirmed
- [x] Scalability documented
- [x] Antipatterns cleared

## Council Verdict
(APPROVED / APPROVED WITH CONCERNS — summary of concerns if any)

## Test Results
(Output of test run)

## Risk Tier
(Routine / Elevated / Critical)
```

#### 6.2 Merge Decision

| Risk tier | Merge policy |
|-----------|-------------|
| Routine | Auto-merge if all automated checks pass and council (if run) approved |
| Elevated | Human review required. PR waits for approval. |
| Critical | Human review + explicit sign-off required. |

#### 6.3 Pipeline Audit Log

Final entry for the build loop:

```json
{
  "phase": 6,
  "pr_id": "...",
  "brief_id": "...",
  "task_count": 0,
  "total_revision_loops": 0,
  "council_verdicts": ["..."],
  "automated_check_results": {},
  "risk_tier": "...",
  "merge_decision": "...",
  "total_pipeline_duration_ms": 0,
  "total_tokens_consumed": 0,
  "timestamp": "..."
}
```

---

## 2. The Fix Loop Pipeline

**Purpose:** Autonomous detection and repair of production issues. Runs in parallel with the Build Loop. The Architect reviews fixes, not triages bugs.

```
Capture → Confirm → Investigate → Fix → Prove → [LIGHT COUNCIL] → Deliver PR
                                          ↑                          |
                                          └── Retry (max 3) ────────┘
                                                                     |
                                          Escalate (if 3 fails) ←───┘
```

### 2.1 Capture

Monitor production for errors, failures, anomalies:

| Source | What to capture |
|--------|----------------|
| Error monitoring (Sentry, structured logs) | Exceptions with full context, stack traces, correlation IDs |
| Health checks | Degraded/failed health endpoints |
| Test regressions | Tests that previously passed now failing |
| Performance anomalies | Latency spikes, throughput drops |
| Security alerts | Dependency vulnerabilities, suspicious access patterns |

**Domain adaptation:**

| Repo | Fix loop monitors |
|------|------------------|
| SWElfare | Production errors, daemon failures, test regressions, CI failures |
| Ratatosk | Trade execution failures, data feed errors, risk limit breaches, calibration drift, API rate limits |
| Magnus | Publish failures, engagement anomalies, slop gate failures, platform API errors, content performance drops |

### 2.2 Confirm

Deduplicate and filter before investigation:

- **Deduplication:** By error pattern (not line number). Group related errors.
- **Transient filter:** 1 occurrence = noise. Configurable threshold (default: 5 in 1 hour) = confirmed bug.
- **External filter:** Errors caused by external dependencies (API outages, network issues) are logged but not investigated.
- **Severity classification:** Critical (data loss, security breach, total outage) / High (partial outage, degraded service) / Medium (functionality broken, workaround exists) / Low (cosmetic, logging error)

### 2.3 Investigate

Root cause analysis using codebase context:

1. Trace the call chain from error to origin
2. Check `git blame` and recent changes for related code
3. Build root cause hypothesis
4. Identify the minimal fix scope
5. Run STRIDE on the fix (does the fix introduce new security concerns?)

### 2.4 Fix

Write the fix in isolation:

1. Create isolated worktree
2. Write failing test that reproduces the error (TDD RED)
3. Write minimal fix to pass the test (TDD GREEN)
4. Run full test suite
5. Run linters (LDD)
6. Run OWASP scan on the diff
7. Verify observability (does the fix include appropriate logging for the failure mode?)

**If fix doesn't pass:** Retry with enriched context (failure reason from previous attempt). Max 3 retries.

### 2.5 Prove

Evidence package:
- Reproduction test (the failing test that passes after fix)
- Full test suite results
- Before/after comparison
- Root cause analysis document
- STRIDE assessment of the fix

### 2.6 Light Council

3 personas review the fix (not full 6 — this is a fix, not a feature):

| Persona | Focus |
|---------|-------|
| **Skeptic** | Does this fix actually address the root cause, or just the symptom? |
| **Operator** | Is the fix safe to deploy? Any rollback concerns? |
| **Security Auditor** | Does the fix introduce new security issues? |

Verdicts: APPROVED / REVISION REQUIRED (retry) / ESCALATE (human needed)

### 2.7 Deliver

PR with:
- Reproduction steps
- Root cause analysis
- Fix explanation
- Test evidence
- Council verdict
- Severity classification
- Link to original error/alert

### 2.8 Escalate

If 3 fix attempts fail, create a detailed issue with:
- Everything the fix loop learned during investigation
- Root cause hypotheses tested and results
- Suggested next steps for human investigation
- Severity and impact assessment

**Exit criteria per fix:**
- [ ] Root cause identified
- [ ] Reproduction test exists
- [ ] Fix passes all tests + linters + security scan
- [ ] Council approved
- [ ] PR delivered with evidence
- [ ] Pipeline audit log: `{ loop: "fix", error_id, severity, root_cause, fix_attempts, council_verdict, pr_id, timestamp }`

---

## 3. The Feedback Loop

**Purpose:** Make both the Build Loop and Fix Loop better over time by learning from human edits and execution outcomes.

### 3.1 Diff Capture

After every human edit to agent output:
- Record the diff (what the human changed)
- Classify the edit type: factual correction, style adjustment, scope change, security fix, structural change
- Tag the edit with the skill that produced the original output

### 3.2 Pattern Distillation

On a configurable schedule (default: nightly):
1. Collect all diffs since last distillation
2. Group by edit type and skill
3. When 10+ similar edits accumulate for the same pattern:
   - Distill into a candidate rule
   - Validate the rule against recent outputs (would it have prevented the edits?)
   - If validated, write the rule back to the skill definition
4. When a rule has prevented 0 edits for 30+ days:
   - Flag for potential removal (BPE: don't accumulate stale rules)

### 3.3 Learning Store

Persistent knowledge that informs future pipeline runs:

| Record type | What it captures | How it's used |
|-------------|-----------------|--------------|
| **Module outcomes** | Per-module success/failure rates, common issues | Informs brief generation (known trouble spots) |
| **Council patterns** | Common rejection reasons per persona | Pre-screens briefs before council (catch known issues early) |
| **Fix patterns** | Common error types and their root causes | Informs investigation step in fix loop |
| **Skill evolution** | Version history of skill rules with diff rationale | Audit trail for feedback loop changes |
| **Reuse catalog** | Functions/patterns that have been successfully reused | Strengthens reuse analysis accuracy over time |

### 3.4 Skill Self-Improvement Protocol

```
Human edits output → Diff recorded →
  Nightly: diffs grouped by skill →
    10+ similar edits? → Distill candidate rule →
      Validate against recent outputs →
        Write rule to skill file (version controlled) →
          Next execution uses updated skill
```

**Guardrails:**
- Candidate rules require validation before activation
- All rule changes are version-controlled and auditable
- Rules that don't fire for 30 days are flagged for removal
- Human can override any auto-generated rule

---

## 4. Cross-Cutting Concerns

### 4.1 Pipeline Observability

The ADLC pipeline itself emits structured audit logs at every phase:

```json
{
  "pipeline_run_id": "uuid",
  "input_id": "...",
  "phase": 0,
  "phase_name": "prd_agent",
  "started_at": "ISO8601",
  "completed_at": "ISO8601",
  "duration_ms": 0,
  "tokens_consumed": 0,
  "outcome": "success | failure | revision_required",
  "details": {},
  "errors": []
}
```

Every phase, every council decision, every revision loop, every gate pass/fail is logged. This enables:
- Pipeline performance analysis (where do briefs get stuck?)
- Cost attribution (which phases consume the most tokens?)
- Quality trend analysis (are revision loops decreasing over time?)
- Debugging (what happened in a specific pipeline run?)

### 4.2 Security Posture (Universal)

| Layer | What | When |
|-------|------|------|
| **STRIDE** | Threat modeling per task | Phase 1 (Brief) |
| **STRIDE validation** | Council verifies completeness | Phase 2 (Post-Brief Council) |
| **Security contract** | Mitigations inlined into codegen context | Phase 3 (Assembly) |
| **Security tests** | TDD includes security-specific tests | Phase 4 (Execution) |
| **OWASP Top 10** | Automated SAST scan on diff | Phase 5 (Post-Execution) |
| **Security council** | Security Auditor validates mitigations | Phase 5 (Post-Execution Council) |
| **Fix loop elevation** | Security fixes auto-elevated to Critical risk tier | Fix Loop |

### 4.3 OWASP Top 10 Scan Coverage

The automated OWASP scan checks for:

| # | Vulnerability | Detection method |
|---|--------------|-----------------|
| A01 | Broken Access Control | Pattern match for missing auth checks, privilege escalation paths |
| A02 | Cryptographic Failures | Weak algorithms, hardcoded secrets, missing encryption |
| A03 | Injection | SQL, command, LDAP, XSS, template injection patterns |
| A04 | Insecure Design | Missing rate limiting, trust boundary violations |
| A05 | Security Misconfiguration | Default credentials, verbose errors, unnecessary features |
| A06 | Vulnerable Components | Dependency scanning, known CVE matching |
| A07 | Auth Failures | Weak password rules, missing MFA, session issues |
| A08 | Data Integrity Failures | Missing signature verification, insecure deserialization |
| A09 | Logging Failures | Missing security logging, insufficient audit trail |
| A10 | SSRF | Unvalidated URL inputs, internal network access |

### 4.4 Definition of Done (Universal Reference)

The complete DoD checklist that applies to every task in every repo:

```markdown
## Definition of Done

### Code Quality
- [ ] All linters pass (LDD)
- [ ] All tests pass (TDD) — unit, integration, security
- [ ] Code complexity within budget (CC < ceiling, SLOC < ceiling)
- [ ] No code slop (placeholders, TODOs, god functions, duplicates, hardcoded values)

### Security
- [ ] STRIDE threat model complete
- [ ] STRIDE mitigations implemented
- [ ] OWASP Top 10 scan clean
- [ ] No hardcoded secrets
- [ ] Input validation at trust boundaries

### Observability
- [ ] Error logging at all failure points (structured JSON, correlation IDs)
- [ ] Audit logging for all state changes (who, what, when, from, to)
- [ ] Operational logging for health/debug (configurable level)
- [ ] Log format matches repo convention

### Reuse & Patterns
- [ ] Reuse analysis confirmed (no reimplementation)
- [ ] Existing conventions followed (naming, error handling, config patterns)
- [ ] Antipattern checklist cleared

### Integration
- [ ] Integration wiring complete (upstream, downstream, registration)
- [ ] Scalability concerns documented
- [ ] Degradation strategy defined (if applicable)

### Content (for human-facing output)
- [ ] Stop-slop gate passed (35/50 minimum)
- [ ] Voice/brand compliance verified (if applicable)
```

---

## 5. Domain Adaptation

### 5.1 SWElfare

SWElfare is the reference implementation. It has the most complete ADLC today and needs enhancement, not rebuild.

**Enhancements needed:**
- Add Phase 0 (PRD Agent) before brief generation
- Enhance brief with STRIDE, scalability, observability contract, reuse analysis, antipatterns, DoD
- Add Security Auditor as permanent council persona
- Add LDD as Phase 4 Step 1 (before TDD)
- Make TDD enforcement blocking (iron law)
- Wire content slop into PR descriptions and documentation
- Formalize fix loop from existing daemon error handling
- Add pipeline observability (audit logs at every phase)
- Add feedback loop (diff capture → pattern distillation → skill update)

### 5.2 Ratatosk

Ratatosk needs ADLC adapted to investment operations, not software engineering.

**Domain mapping:**

| ADLC Component | Ratatosk Implementation |
|----------------|------------------------|
| Phase -1 Intake | Market signal classification (asset class, timeframe, conviction signal strength) |
| Phase 0 PRD | Trade thesis structuring (market context, conviction rationale, risk parameters, exit criteria) |
| Phase 1 Brief | Trade plan with STRIDE (execution risk), observability (trade logging, P&L attribution), reuse (existing strategy patterns), DoD (risk gate + arbiter + backtest validation) |
| Phase 2 Council | Full 6-persona council adapted: Architect=portfolio strategy, Skeptic=bearish thesis, Operator=execution feasibility, Executioner=can the agent execute this trade?, Security=API key/funds safety, First Principles=is this trade thesis sound? |
| Phase 3 Assembly | Trade execution context: position sizing, entry/exit rules, risk parameters, market data, all inlined |
| Phase 4 Execution | LDD=parameter validation, TDD=walk-forward backtest validation, Implement=execute trade |
| Phase 5 Post-Execution | Automated: P&L check, risk limit compliance, slippage analysis. Council: for trades > threshold |
| Phase 6 Ship | Trade executed + audit logged + performance report |
| Fix Loop | Trade failure → investigate → adjust → re-execute or exit position |
| Feedback Loop | Trade outcome → calibration update → strategy parameter adjustment |
| Stop Slop | Applied to: morning briefings, Telegram messages, trade summaries, performance reports |
| Observability | Trade logging (entry/exit/P&L), risk logging (limit checks, drawdown), audit logging (all decisions with rationale) |

### 5.3 Magnus

Magnus needs ADLC adapted to content operations.

**Domain mapping:**

| ADLC Component | Magnus Implementation |
|----------------|----------------------|
| Phase -1 Intake | Content signal classification (bookmark source, topic relevance, ICP alignment, format potential) |
| Phase 0 PRD | Content brief structuring (topic, angle, ICP target, platform, voice constraints, format, anti-slop rules) |
| Phase 1 Brief | Content plan with STRIDE (brand risk: voice impersonation, misinformation, PII), observability (engagement tracking, content performance), reuse (voice profile, proven formats, successful angles), DoD (slop gate + voice compliance + platform constraints) |
| Phase 2 Council | Full 6-persona council adapted: Architect=content strategy alignment, Skeptic=will this damage the brand?, Operator=can this be published on the target platform?, Executioner=can the agent produce this?, Security=PII/reputation risk, First Principles=does this serve the ICP? |
| Phase 3 Assembly | Content execution context: voice profile, format template, reference content, ICP profile, platform constraints, all inlined |
| Phase 4 Execution | LDD=format validation (structure, length, platform constraints), TDD=content quality checks (voice match, slop score, ICP alignment), Implement=draft content |
| Phase 5 Post-Execution | Automated: stop-slop (35/50), voice compliance, platform constraint check. Council: for high-visibility content |
| Phase 6 Ship | Publish via Postiz CLI + audit logged + performance tracking initiated |
| Fix Loop | Engagement anomaly → investigate (format? timing? topic?) → adjust strategy → re-execute |
| Feedback Loop | Human edits to content → diff capture → voice profile refinement → content-forge skill update |
| Stop Slop | ALL output — this is Magnus's primary quality gate. Full 8 rules + 5-dimension scoring + banned phrases |
| Observability | Content performance (engagement, reach, conversion), pipeline metrics (acceptance rate, edit distance), audit logging (all editorial decisions) |

---

## 6. Skill Inventory

### 6.1 Core Skills (Required for all domains)

| Skill | Trigger | Phase | Purpose |
|-------|---------|-------|---------|
| `prd-generation` | Phase 0 entry | 0 | Structured discovery and PRD output |
| `build-brief` | Phase 1 entry | 1 | Technical design with STRIDE, observability, reuse, DoD |
| `eval-council` | Phase 2 and Phase 5 | 2, 5 | Multi-persona adversarial review |
| `codegen-context` | Phase 3 entry | 3 | Zero-read context assembly |
| `architecture-pattern` | Phase 3 (when scaffolding needed) | 3 | Port/adapter/type/wiring generation |
| `tdd-enforcement` | Phase 4 Step 2 | 4 | RED-GREEN-REFACTOR per criterion |
| `stop-slop` | Phase 5 (all output) | 5 | Code slop + content slop detection |
| `security-review` | Phase 1 (STRIDE) + Phase 5 (OWASP) | 1, 5 | Threat modeling and vulnerability scanning |
| `reuse-analysis` | Phase 1 (discovery) + Phase 5 (verification) | 1, 5 | Pattern continuation enforcement |
| `observability-contract` | Phase 1 (specification) + Phase 5 (verification) | 1, 5 | Logging mandate enforcement |

### 6.2 Orchestration Skills

These compose core skills into sequences:

| Skill | Sequence | Use case |
|-------|----------|----------|
| `build-feature` | PRD → Brief → Council → Scaffold → Codegen → LDD → TDD → Council → PR | Standard feature delivery |
| `fix-bug` | Investigate → Brief(light) → LDD → TDD → Council(light) → PR | Bug fix via fix loop |
| `ship-content` | Brief → Council → Draft → Slop Gate → Council(light) → Publish | Content delivery (Magnus) |
| `execute-trade` | Thesis → Council → Risk Check → Execute → Audit → Report | Trade execution (Ratatosk) |

### 6.3 Supporting Skills

| Skill | Purpose |
|-------|---------|
| `codebase-research` | Deep repo analysis for brief generation |
| `qa-test-data` | Generate test scenarios from G/W/T criteria |
| `systematic-debugging` | Structured debug framework for fix loop |
| `incident-runbook` | Generate runbooks from incident patterns |
| `jira-ticket-creation` | Create executable tickets from decomposition |
| `confluence-decomposition` | Decompose large tickets into binary actions |

---

## 7. Configuration

### 7.1 Per-Repo Configuration

```yaml
adlc:
  version: 2

  # Pipeline toggles
  pipeline:
    prd_agent: true
    build_brief: true
    eval_council: true
    scaffold: true
    codegen_context: true
    ldd: true
    tdd: true
    post_execution_gate: true
    fix_loop: true
    feedback_loop: true

  # Scope routing thresholds
  routing:
    file_threshold: 8
    subsystem_threshold: 2
    loc_threshold: 300
    concern_mix_threshold: 3

  # Council configuration
  council:
    personas:
      - architect
      - skeptic
      - operator
      - executioner
      - security_auditor
      - first_principles
    max_revision_loops: 3
    rounds_per_review: 3
    skip_for_routine: true  # Routine risk = automated only

  # LDD configuration
  ldd:
    linters: []           # Repo-specific: ["black", "mypy", "ruff"] or ["prettier", "tsc", "eslint"]
    formatters: []
    type_checkers: []
    block_on_violation: true

  # TDD configuration
  tdd:
    iron_law: true        # Block code without failing test
    coverage_threshold: 80
    include_security_tests: true
    include_observability_tests: true

  # Security configuration
  security:
    stride_required: true
    owasp_scan: true
    severity_block_threshold: "high"  # Block on High or Critical

  # Observability configuration
  observability:
    error_logging_required: true
    audit_logging_required: true
    general_logging_required: true
    log_format: "structured_json"
    correlation_ids: true

  # Slop configuration
  slop:
    code_slop: true
    content_slop: true
    content_threshold: 35        # out of 50
    outreach_threshold: 38       # higher bar for external content
    cc_ceiling: 15               # max cyclomatic complexity
    sloc_ceiling_per_function: 50

  # Fix loop configuration
  fix_loop:
    enabled: true
    confirmation_threshold: 5     # errors in 1 hour = confirmed bug
    max_fix_attempts: 3
    auto_escalate: true
    council_weight: "light"       # skeptic + operator + security_auditor

  # Feedback loop configuration
  feedback_loop:
    enabled: true
    distillation_schedule: "nightly"
    similar_edit_threshold: 10    # edits before rule distillation
    stale_rule_days: 30           # flag unused rules after 30 days

  # Reuse configuration
  reuse:
    ast_discovery: true
    llm_filtering: true
    block_on_reimplementation: true
```

---

## 8. Migration Path

### 8.1 Priority Order

1. **Stop Slop wiring** — Quick win. Wire existing content slop gate into Magnus (all output), Ratatosk (briefings/Telegram), SWElfare (PR descriptions).
2. **Security (STRIDE + OWASP)** — Risk reduction. Add STRIDE to brief generation, OWASP scan to post-execution gate. Add Security Auditor persona to council.
3. **LDD** — Add lint gate before TDD in SWElfare execution. Configure per-repo linters for Ratatosk/Magnus.
4. **Observability contract** — Add logging mandate to brief and verify in post-execution gate.
5. **PRD Agent** — Add structured discovery as Phase 0 across all repos.
6. **Reuse analysis + Antipatterns** — Enhance brief with reuse section and "What This Isn't."
7. **Definition of Done** — Formalize and enforce the universal DoD checklist.
8. **Fix Loop** — Formalize SWElfare's existing error handling into full fix loop. Build for Ratatosk/Magnus.
9. **Feedback Loop** — Add diff capture, pattern distillation, and skill self-improvement.
10. **Pipeline observability** — Add structured audit logs at every phase.

### 8.2 BPE Removal Schedule

Review quarterly. Remove structure that models no longer need:

| Structure | Remove when |
|-----------|------------|
| LDD pre-check | Models produce lint-clean code >95% of the time |
| Explicit reuse hints | Models consistently discover and reuse existing patterns without hints |
| Detailed "What NOT to Do" | Models stop making the antipattern mistakes listed |
| Multi-round council | Single-round catches >95% of issues that 3 rounds catch |
| Fix loop retry enrichment | Models fix bugs on first attempt >90% of the time |

---

## Appendix A: Pipeline Audit Log Schema

```json
{
  "pipeline_run_id": "uuid",
  "repo": "swelfare | ratatosk | magnus",
  "loop": "build | fix | feedback",
  "input_id": "issue/signal/bookmark ID",
  "phases": [
    {
      "phase": -1,
      "name": "intake",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "duration_ms": 0,
      "tokens_consumed": 0,
      "outcome": "success | failure | skipped",
      "details": {
        "scope": "NARROW | WIDE",
        "risk_tier": "routine | elevated | critical",
        "domain_tags": []
      }
    }
  ],
  "total_duration_ms": 0,
  "total_tokens_consumed": 0,
  "total_revision_loops": 0,
  "final_outcome": "shipped | blocked | escalated",
  "pr_id": "...",
  "created_at": "ISO8601"
}
```

## Appendix B: Council Verdict Schema

```json
{
  "council_id": "uuid",
  "pipeline_run_id": "uuid",
  "phase": 2,
  "brief_id": "...",
  "round_count": 3,
  "persona_verdicts": {
    "architect": { "verdict": "approved", "findings": [], "score": 0 },
    "skeptic": { "verdict": "revision_required", "findings": ["..."], "score": 0 },
    "operator": { "verdict": "approved_with_concerns", "findings": ["..."], "score": 0 },
    "executioner": { "verdict": "approved", "findings": [], "score": 0 },
    "security_auditor": { "verdict": "approved", "findings": [], "score": 0 },
    "first_principles": { "verdict": "approved", "findings": [], "score": 0 }
  },
  "synthesis_verdict": "approved | approved_with_concerns | revision_required | blocked",
  "synthesis_rationale": "...",
  "revision_instructions": "...",
  "timestamp": "ISO8601"
}
```

## Appendix C: Definition of Done Verification Schema

```json
{
  "task_id": "...",
  "dod_checks": {
    "ldd_pass": { "status": true, "evidence": "lint output" },
    "tdd_pass": { "status": true, "evidence": "test output", "coverage": 87 },
    "logging_complete": { "status": true, "error_points": 3, "audit_points": 2, "general_points": 5 },
    "stride_mitigated": { "status": true, "threats": 4, "mitigations": 4 },
    "owasp_clean": { "status": true, "findings": 0 },
    "slop_clean": { "status": true, "code_violations": 0, "content_score": 42 },
    "reuse_confirmed": { "status": true, "reimplementations": 0 },
    "scalability_documented": { "status": true },
    "antipatterns_cleared": { "status": true, "violations": 0 },
    "integration_complete": { "status": true, "upstream": 2, "downstream": 1 }
  },
  "all_passed": true,
  "timestamp": "ISO8601"
}
```
