# ADLC v2 Implementation Tickets

**Date:** 2026-04-05
**Source:** adlc-v2-specification.md
**Decomposition principle:** Every ticket is binary (done/not-done). One ticket = one verifiable outcome. No ticket requires judgment to determine completion — it either passes its acceptance criteria or it doesn't.

> Alignment note: this roadmap predates the applicability-manifest refactor. Tickets that describe universal observability, security, or TDD ceremony should now be interpreted through the live contract in `agents/triage.md`, `agents/planner.md`, and `docs/schemas/*.json`.

---

## Phase 1: Stop Slop Wiring (Quick Win)

### ADLC-001: Create universal stop-slop skill with code + content modes
- **Repo:** `~/.claude/skills/stop-slop/`
- **What:** Update the existing stop-slop SKILL.md to formalize two modes: code slop (placeholders, god functions, duplicates, hardcoded values) and content slop (8 rules, banned phrases, 5-dimension scoring with 35/50 threshold)
- **Acceptance criteria:**
  - [ ] SKILL.md defines code slop patterns with regex/AST detection rules
  - [ ] SKILL.md defines content slop: 8 rules, banned phrase list, 5-dimension scoring rubric
  - [ ] Thresholds documented: 35/50 general, 38/50 outreach
  - [ ] Skill has `when:` trigger conditions for auto-activation
- **DoD:** Skill file exists with both modes fully specified. Passes self-consistency review.

### ADLC-002: Wire content slop gate into Magnus content-forge
- **Repo:** `magnus`
- **What:** Modify `skills/content-forge/SKILL.md` to invoke stop-slop content mode on all output before delivery. Add 5-dimension scoring with 35/50 threshold as a hard gate.
- **Acceptance criteria:**
  - [ ] content-forge SKILL.md references stop-slop skill
  - [ ] Scoring rubric (5 dimensions) is inlined or referenced
  - [ ] Output below 35/50 is blocked with specific feedback on which dimensions failed
  - [ ] Banned phrase list is present
- **DoD:** content-forge invokes slop gate. Output below threshold cannot proceed.

### ADLC-003: Wire content slop gate into Magnus content-adapt
- **Repo:** `magnus`
- **What:** Modify `skills/content-adapt/SKILL.md` to run stop-slop on all platform-adapted output.
- **Acceptance criteria:**
  - [ ] content-adapt SKILL.md references stop-slop skill
  - [ ] Each platform adaptation is individually scored
  - [ ] Output below 35/50 is blocked
- **DoD:** Adapted content cannot be published without passing slop gate.

### ADLC-004: Wire content slop gate into Ratatosk morning-briefing
- **Repo:** `ratatosk`
- **What:** Modify `skills/morning-briefing/SKILL.md` to run stop-slop content mode on briefing output before Telegram delivery.
- **Acceptance criteria:**
  - [ ] morning-briefing SKILL.md references stop-slop skill
  - [ ] Briefing output is scored on 5 dimensions
  - [ ] Output below 35/50 is revised before sending
- **DoD:** Briefings cannot be sent to Telegram without passing slop gate.

### ADLC-005: Wire content slop gate into Ratatosk performance-review
- **Repo:** `ratatosk`
- **What:** Modify `skills/performance-review/SKILL.md` to run stop-slop on weekly performance reports.
- **Acceptance criteria:**
  - [ ] performance-review SKILL.md references stop-slop skill
  - [ ] Reports scored on 5 dimensions
  - [ ] Output below 35/50 is revised
- **DoD:** Performance reports pass slop gate before delivery.

### ADLC-006: Add code slop scanning to SWElfare PR description generation
- **Repo:** `swelfare`
- **What:** Wire content slop gate into Phase 6 PR creation. PR descriptions, issue comments, and documentation must pass stop-slop content mode.
- **Acceptance criteria:**
  - [ ] PR description template includes slop gate check
  - [ ] Content slop score is included in PR metadata
  - [ ] Descriptions below 35/50 are rewritten before PR creation
- **DoD:** No PR is created with a description that fails the slop gate.

---

## Phase 2: Security (STRIDE + OWASP)

### ADLC-007: Create security-review skill with STRIDE + OWASP modes
- **Repo:** `~/.claude/skills/`
- **What:** Create `security-review/SKILL.md` that defines two modes: STRIDE threat modeling (per-task, during brief) and OWASP Top 10 scanning (per-diff, post-execution).
- **Acceptance criteria:**
  - [ ] STRIDE template with all 6 categories and risk rating scale (L/M/H/C)
  - [ ] OWASP Top 10 checklist with detection patterns for each vulnerability class
  - [ ] Domain adaptation notes for SWElfare (software), Ratatosk (trade execution), Magnus (brand/content)
  - [ ] `when:` trigger conditions for auto-activation at Phase 1 and Phase 5
- **DoD:** Skill file exists with both modes fully specified.

### ADLC-008: Add Security Auditor persona to SWElfare eval council
- **Repo:** `swelfare`
- **What:** Add `security_auditor` as a permanent 6th persona in `swelfare_core/gates/eval_council.py`. Focus: STRIDE validation, OWASP applicability, trust boundaries, secrets handling.
- **Acceptance criteria:**
  - [ ] `security_auditor` persona defined with system prompt
  - [ ] Persona participates in all 3 council rounds
  - [ ] Persona specifically validates STRIDE completeness in post-brief review
  - [ ] Persona validates STRIDE mitigation implementation in post-execution review
  - [ ] Tests updated to include security_auditor in council composition
- **DoD:** Council runs with 6 personas. Security Auditor findings appear in council verdicts.

### ADLC-009: Add STRIDE threat model generation to SWElfare brief generator
- **Repo:** `swelfare`
- **What:** Enhance `swelfare_core/adlc/llm_brief_generator.py` to generate a STRIDE threat model per TaskSpec. Each task gets a `stride_threats` field with the 6 STRIDE categories analyzed.
- **Acceptance criteria:**
  - [ ] TaskSpec model has `stride_threats: list[StrideThreat]` field
  - [ ] StrideThreat dataclass: category, analysis, risk_rating, mitigation_required
  - [ ] Brief generator populates STRIDE for each task
  - [ ] Static fallback emits conservative STRIDE output with `unknown` risk and explicit mitigation-required fields if LLM unavailable
  - [ ] Tests validate STRIDE presence in generated briefs
- **DoD:** Every TaskSpec generated by the brief generator includes a STRIDE threat model.

### ADLC-010: Add OWASP Top 10 scan to SWElfare post-execution gate
- **Repo:** `swelfare`
- **What:** Add an OWASP Top 10 scanner to `swelfare_core/adlc/post_execution_slop.py` (or new file) that runs on the diff at Phase 5. Blocks on High/Critical findings.
- **Acceptance criteria:**
  - [ ] Scanner checks for all 10 OWASP categories using pattern matching + LLM review
  - [ ] Findings classified by severity (Info/Low/Medium/High/Critical)
  - [ ] High/Critical findings block the pipeline
  - [ ] Findings report includes specific line numbers and remediation guidance
  - [ ] Tests validate detection of common vulnerability patterns
- **DoD:** OWASP scan runs on every diff. High/Critical findings block merge.

### ADLC-011: Add STRIDE to Ratatosk trade execution context
- **Repo:** `ratatosk`
- **What:** Add STRIDE threat modeling section to `skills/trade-signal/SKILL.md` focused on trade execution risks: order spoofing, parameter tampering, trade repudiation, API key disclosure, exchange DoS, privilege escalation.
- **Acceptance criteria:**
  - [ ] trade-signal SKILL.md includes STRIDE analysis section
  - [ ] Each STRIDE category has domain-specific analysis prompts for trade execution
  - [ ] Risk mitigations are required before trade execution proceeds
- **DoD:** Trade signals include STRIDE analysis. Unmitigated High/Critical risks block execution.

### ADLC-012: Add STRIDE to Magnus content pipeline
- **Repo:** `magnus`
- **What:** Add STRIDE threat modeling to `skills/content-judge/SKILL.md` focused on brand risks: voice impersonation, content tampering, attribution repudiation, PII disclosure, publish flooding, unauthorized tone override.
- **Acceptance criteria:**
  - [ ] content-judge SKILL.md includes STRIDE analysis section
  - [ ] Each STRIDE category has domain-specific analysis prompts for content/brand risk
  - [ ] High/Critical brand risks block content publication
- **DoD:** Content pipeline includes STRIDE analysis. Unmitigated brand risks block publishing.

---

## Phase 3: Lint-Driven Development

### ADLC-013: Create LDD enforcement skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `ldd-enforcement/SKILL.md` that defines lint-driven development: run linters/formatters/type-checkers BEFORE test execution. Violations block TDD entry.
- **Acceptance criteria:**
  - [ ] Skill defines LDD sequence: lint → fix → re-lint → proceed to TDD
  - [ ] Skill specifies per-language linter defaults (Python: black+ruff+mypy, JS/TS: prettier+eslint+tsc, etc.)
  - [ ] Violations block test execution (hard gate, not advisory)
  - [ ] `when:` trigger: Phase 4 entry, before TDD
- **DoD:** Skill file exists with LDD protocol fully specified.

### ADLC-014: Add LDD gate to SWElfare execution pipeline
- **Repo:** `swelfare`
- **What:** Add LDD step to `swelfare_core/daemon/orchestrator.py` Phase 3 execution. Before TDD cycles run, execute configured linters. Block on violations.
- **Acceptance criteria:**
  - [ ] Orchestrator runs linters before TDD
  - [ ] Lint failures block test execution
  - [ ] Lint results logged in pipeline audit
  - [ ] Linter configuration is repo-configurable (not hardcoded)
  - [ ] Tests validate LDD gate blocks on violations
- **DoD:** SWElfare execution pipeline runs linters before tests. Lint violations block progress.

### ADLC-015: Add LDD configuration to Ratatosk
- **Repo:** `ratatosk`
- **What:** Add lint configuration to `config.yaml` for any Python code Ratatosk generates or modifies. Configure ruff + mypy.
- **Acceptance criteria:**
  - [ ] config.yaml has `adlc.ldd.linters` section
  - [ ] ruff and mypy configured with project-appropriate rules
  - [ ] SKILL.md files reference LDD requirement for code-producing skills
- **DoD:** Ratatosk has lint configuration. Code-producing skills reference LDD gate.

### ADLC-016: Add LDD configuration to Magnus
- **Repo:** `magnus`
- **What:** Add lint configuration to `config.yaml` for any code Magnus generates. Configure ruff + mypy.
- **Acceptance criteria:**
  - [ ] config.yaml has `adlc.ldd.linters` section
  - [ ] Linters configured with project-appropriate rules
- **DoD:** Magnus has lint configuration for generated code.

---

## Phase 4: Observability Contract

### ADLC-017: Create observability-contract skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `observability-contract/SKILL.md` that defines logging requirements for tasks that introduce runtime paths, services, or user-facing operations.
- **Acceptance criteria:**
  - [ ] Skill defines three log types (error, audit, general) with required fields
  - [ ] Skill specifies structured JSON format
  - [ ] Skill requires correlation IDs across service boundaries
  - [ ] Skill defines verification: AST scan for required log statements
  - [ ] `when:` triggers at Phase 1 (specification) and Phase 5 (verification)
- **DoD:** Skill file exists with logging mandate fully specified.

### ADLC-018: Add observability requirements to SWElfare TaskSpec
- **Repo:** `swelfare`
- **What:** Enhance `swelfare_core/spec/models.py` TaskSpec to carry an optional `observability_contract` that activates only when the applicability manifest marks observability as active.
- **Acceptance criteria:**
  - [ ] TaskSpec supports `observability_contract: ObservabilityContract | None`
  - [ ] ObservabilityContract dataclass: error_points (list), audit_points (list), general_points (list), log_format, correlation_id_required
  - [ ] Brief generator populates observability contract per task
  - [ ] Tests validate observability contract activation only for tasks with active observability overlays
- **DoD:** TaskSpecs include an observability contract when the overlay is active.

### ADLC-019: Add observability verification to SWElfare post-execution gate
- **Repo:** `swelfare`
- **What:** Add AST-based scan to post-execution gate that verifies required logging is present in the implementation per the observability contract.
- **Acceptance criteria:**
  - [ ] Scanner checks for required error logging at failure points
  - [ ] Scanner checks for required audit logging at state change points
  - [ ] Scanner checks for correlation ID propagation
  - [ ] Missing logging blocks the pipeline (hard gate)
  - [ ] Tests validate detection of missing logging
- **DoD:** Post-execution gate verifies logging. Missing required logging blocks merge.

### ADLC-020: Add observability requirements to Ratatosk skills
- **Repo:** `ratatosk`
- **What:** Add observability sections to trade-signal, market-scan, and nightly-experiment SKILL.md files. Trade logging (entry/exit/P&L), risk logging (limit checks, drawdown), audit logging (all decisions with rationale).
- **Acceptance criteria:**
  - [ ] trade-signal SKILL.md specifies required trade execution logs
  - [ ] market-scan SKILL.md specifies required data ingestion logs
  - [ ] nightly-experiment SKILL.md specifies required experiment result logs
  - [ ] All logs use structured JSON format
- **DoD:** Ratatosk skills specify observability requirements.

### ADLC-021: Add observability requirements to Magnus skills
- **Repo:** `magnus`
- **What:** Add observability sections to content-forge, content-publish, and content-mirror SKILL.md files. Content performance (engagement, reach), pipeline metrics (acceptance rate, edit distance), audit logging (editorial decisions).
- **Acceptance criteria:**
  - [ ] content-forge SKILL.md specifies required draft quality logs
  - [ ] content-publish SKILL.md specifies required publication logs
  - [ ] content-mirror SKILL.md specifies required engagement analysis logs
  - [ ] All logs use structured JSON format
- **DoD:** Magnus skills specify observability requirements.

---

## Phase 5: PRD Agent

### ADLC-022: Create PRD Agent specification
- **Repo:** `~/.claude/agents/`
- **What:** Update `PM-PRD-AGENT.md` to align with ADLC v2: 3-5 turn discovery, extract-first principle, mandatory output sections (problem statement, success metrics, out of scope, constraints/antipatterns, dependencies, personas).
- **Acceptance criteria:**
  - [ ] Agent spec defines 3-5 turn interaction model
  - [ ] Extract-first principle documented (analyze input + codebase before asking)
  - [ ] PRD output contract matches ADLC v2 Phase 0 spec
  - [ ] Domain adaptation notes for SWElfare, Ratatosk, Magnus
  - [ ] Exit criteria are binary (no ambiguous language, all sections populated)
- **DoD:** PRD Agent spec aligns with ADLC v2 Phase 0.

### ADLC-023: Wire PRD Agent into SWElfare pipeline as Phase 0
- **Repo:** `swelfare`
- **What:** Add Phase 0 to `swelfare_core/daemon/orchestrator.py` that runs PRD Agent structured discovery before brief generation. Raw GitHub issues enter Phase 0; structured PRDs enter Phase 1.
- **Acceptance criteria:**
  - [ ] Orchestrator has `_run_phase_0()` method
  - [ ] Phase 0 takes raw issue and produces structured PRD
  - [ ] Structured PRD feeds into Phase 1 brief generation
  - [ ] Pipeline audit log emits Phase 0 entry
  - [ ] Tests validate Phase 0 produces structured output from raw input
- **DoD:** SWElfare pipeline has Phase 0. Raw issues are structured before brief generation.

### ADLC-024: Create Ratatosk trade thesis structuring skill
- **Repo:** `ratatosk`
- **What:** Create `skills/trade-thesis/SKILL.md` that structures market signals into formal trade theses (Ratatosk's domain-adapted PRD). Output: market context, conviction rationale, risk parameters, exit criteria, position sizing logic.
- **Acceptance criteria:**
  - [ ] SKILL.md defines trade thesis output contract
  - [ ] Input: market context packets from market-scan
  - [ ] Output: structured trade thesis with all required sections
  - [ ] No ambiguous signals pass (conviction level must be quantified)
- **DoD:** Trade thesis skill exists. Market signals are structured before execution.

### ADLC-025: Create Magnus content brief structuring skill
- **Repo:** `magnus`
- **What:** Create `skills/content-brief/SKILL.md` that structures content signals (bookmarks, trending topics) into formal content briefs (Magnus's domain-adapted PRD). Output: topic, angle, ICP target, platform, voice constraints, format, anti-slop rules.
- **Acceptance criteria:**
  - [ ] SKILL.md defines content brief output contract
  - [ ] Input: processed bookmarks from content-ingest
  - [ ] Output: structured content brief with all required sections
  - [ ] Ambiguous briefs (no clear ICP, no clear angle) are rejected
- **DoD:** Content brief skill exists. Signals are structured before content creation.

---

## Phase 6: Reuse Analysis + Antipatterns

### ADLC-026: Create reuse-analysis skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `reuse-analysis/SKILL.md` that defines the reuse discovery and antipattern avoidance process. AST-based discovery + keyword matching + LLM-filtered relevance.
- **Acceptance criteria:**
  - [ ] Skill defines discovery process: find existing functions, utilities, patterns
  - [ ] Skill defines "DO NOT REIMPLEMENT" output format
  - [ ] Skill defines antipattern catalog format (known bad patterns to avoid)
  - [ ] Skill defines verification: check implementation doesn't duplicate existing code
  - [ ] `when:` triggers at Phase 1 (discovery) and Phase 5 (verification)
- **DoD:** Skill file exists with reuse analysis and antipattern avoidance fully specified.

### ADLC-027: Add "What NOT to Do" section to SWElfare codegen context
- **Repo:** `swelfare`
- **What:** Enhance `swelfare_core/adlc/context_assembler.py` to include a "What NOT to Do" section in assembled context. Sources: brief's antipatterns, reuse analysis violations, known failure modes.
- **Acceptance criteria:**
  - [ ] Context assembly includes Section 8: "What NOT to Do"
  - [ ] Section populated from brief's antipatterns field
  - [ ] Section includes reimplementation warnings from reuse analysis
  - [ ] Section includes known failure modes from learning store
  - [ ] Tests validate "What NOT to Do" section presence
- **DoD:** Every assembled codegen context includes "What NOT to Do" section.

### ADLC-028: Add reuse verification to SWElfare post-execution gate
- **Repo:** `swelfare`
- **What:** Add reimplementation detection to post-execution gate. AST comparison between new code and existing utilities flagged in reuse analysis. Block on reimplementation.
- **Acceptance criteria:**
  - [ ] Scanner compares new functions against reuse catalog
  - [ ] Near-duplicate detection (>80% similarity) blocks pipeline
  - [ ] Report includes: what was reimplemented, where the original lives, how to use it
  - [ ] Tests validate reimplementation detection
- **DoD:** Post-execution gate catches reimplementation. Duplicates block merge.

### ADLC-029: Add antipatterns section to SWElfare brief generation
- **Repo:** `swelfare`
- **What:** Enhance `swelfare_core/adlc/llm_brief_generator.py` to generate an antipatterns/constraints/"what this isn't" section per TaskSpec.
- **Acceptance criteria:**
  - [ ] TaskSpec has `antipatterns: list[str]` field
  - [ ] TaskSpec has `constraints: list[str]` field
  - [ ] Brief generator populates from: codebase analysis, learning store, issue context
  - [ ] Tests validate antipatterns presence in generated briefs
- **DoD:** Every TaskSpec includes antipatterns and constraints.

---

## Phase 7: Definition of Done Formalization

### ADLC-030: Create universal DoD checklist as a skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `definition-of-done/SKILL.md` that defines the universal DoD checklist applicable to all repos. Machine-verifiable where possible.
- **Acceptance criteria:**
  - [ ] DoD checklist matches ADLC v2 spec Section 4.4
  - [ ] Each item has: check name, verification method (automated/council/manual), blocking behavior
  - [ ] Domain adaptation notes (which items apply to which repo)
  - [ ] `when:` trigger at Phase 4 completion and Phase 5 entry
- **DoD:** Skill file exists with universal DoD fully specified.

### ADLC-031: Add DoD checklist to SWElfare TaskSpec
- **Repo:** `swelfare`
- **What:** Add `definition_of_done: list[DoDItem]` field to TaskSpec in `swelfare_core/spec/models.py`. Each DoDItem has: check_name, verification_method, status, evidence.
- **Acceptance criteria:**
  - [ ] DoDItem dataclass defined
  - [ ] TaskSpec has `definition_of_done` field
  - [ ] Brief generator populates DoD per task
  - [ ] Post-execution gate verifies all DoD items before approval
  - [ ] Tests validate DoD presence and verification
- **DoD:** Every TaskSpec has a DoD checklist. Post-execution gate enforces it.

### ADLC-032: Add DoD verification schema to SWElfare pipeline audit
- **Repo:** `swelfare`
- **What:** Add DoD verification output to pipeline audit log per Appendix C schema.
- **Acceptance criteria:**
  - [ ] Pipeline audit log includes DoD verification results per task
  - [ ] Each DoD item has: status (pass/fail), evidence, timestamp
  - [ ] Failed DoD items block pipeline progression
- **DoD:** Pipeline audit log includes DoD verification. All items tracked.

---

## Phase 8: Fix Loop

### ADLC-033: Create fix-loop skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `fix-loop/SKILL.md` that defines the full fix loop: Capture → Confirm → Investigate → Fix → Prove → Council → Deliver/Escalate.
- **Acceptance criteria:**
  - [ ] Skill defines each step with exit criteria
  - [ ] Confirmation thresholds documented (5 errors in 1 hour = confirmed)
  - [ ] Fix isolation documented (worktree, test suite, lint, OWASP)
  - [ ] Escalation protocol documented (3 failures → create detailed issue)
  - [ ] Light council composition: Skeptic + Operator + Security Auditor
  - [ ] Domain adaptation for SWElfare, Ratatosk, Magnus
- **DoD:** Skill file exists with fix loop fully specified.

### ADLC-034: Formalize SWElfare daemon error handling into fix loop
- **Repo:** `swelfare`
- **What:** Enhance existing daemon error handling to follow the ADLC v2 fix loop protocol. Add: error deduplication, transient filtering, automated investigation, isolated fix execution, proof gathering, light council review, PR delivery, escalation after 3 failures.
- **Acceptance criteria:**
  - [ ] Error deduplication by pattern (not line number)
  - [ ] Transient error filtering (configurable threshold)
  - [ ] Investigation uses codebase context + git blame + recent changes
  - [ ] Fix executed in isolated worktree with TDD (RED: reproduce, GREEN: fix)
  - [ ] LDD + OWASP scan on fix diff
  - [ ] Light council review (3 personas)
  - [ ] PR delivered with: reproduction steps, root cause, fix, test evidence
  - [ ] Escalation after 3 failed fix attempts with detailed issue
  - [ ] Pipeline audit log for every fix loop iteration
- **DoD:** SWElfare daemon uses full fix loop protocol. Fixes are autonomous with council review.

### ADLC-035: Create Ratatosk fix loop for trade failures
- **Repo:** `ratatosk`
- **What:** Add fix loop to Ratatosk that monitors trade execution failures, data feed errors, risk limit breaches, and calibration drift. Follows: detect → confirm → investigate → adjust → re-execute or exit.
- **Acceptance criteria:**
  - [ ] Trade execution failures trigger fix loop
  - [ ] Data feed errors trigger fix loop
  - [ ] Risk limit breaches trigger immediate position review
  - [ ] Investigation includes: recent market data, position state, execution logs
  - [ ] Fix proposals reviewed by light council before execution
  - [ ] Escalation to Eric after 3 failed corrections
- **DoD:** Ratatosk has autonomous fix loop for trade and data failures.

### ADLC-036: Create Magnus fix loop for content failures
- **Repo:** `magnus`
- **What:** Add fix loop to Magnus that monitors publish failures, engagement anomalies, slop gate failures, and platform API errors. Follows: detect → confirm → investigate → adjust → re-execute.
- **Acceptance criteria:**
  - [ ] Publish failures trigger fix loop
  - [ ] Engagement anomalies (>2σ drop from baseline) trigger investigation
  - [ ] Slop gate failures trigger content revision
  - [ ] Platform API errors trigger retry with backoff
  - [ ] Escalation after 3 failed attempts
- **DoD:** Magnus has autonomous fix loop for content pipeline failures.

---

## Phase 9: Feedback Loop

### ADLC-037: Create feedback-loop skill
- **Repo:** `~/.claude/skills/`
- **What:** Create `feedback-loop/SKILL.md` that defines the diff capture → pattern distillation → skill update cycle.
- **Acceptance criteria:**
  - [ ] Skill defines diff capture protocol (what to record when human edits agent output)
  - [ ] Skill defines pattern distillation (10+ similar edits → candidate rule)
  - [ ] Skill defines validation (candidate rule tested against recent outputs)
  - [ ] Skill defines stale rule detection (unused for 30 days → flag for removal)
  - [ ] Skill defines skill file update protocol (version-controlled, auditable)
- **DoD:** Skill file exists with feedback loop fully specified.

### ADLC-038: Add diff capture to SWElfare PR review process
- **Repo:** `swelfare`
- **What:** When a human edits a PR (review comments, requested changes, direct edits), capture the diff between agent output and final merged version. Store in learning store.
- **Acceptance criteria:**
  - [ ] Post-merge hook captures diff between agent PR and merged version
  - [ ] Diffs classified by type: factual correction, style, scope change, security, structural
  - [ ] Diffs tagged with the pipeline phase and skill that produced the original
  - [ ] Diffs stored in learning store with timestamp and classification
- **DoD:** Human edits to SWElfare PRs are captured and classified.

### ADLC-039: Add nightly pattern distillation to SWElfare
- **Repo:** `swelfare`
- **What:** Nightly job that reads accumulated diffs, groups by type and skill, distills candidate rules when threshold (10 similar edits) is reached, validates rules, and writes back to skill files.
- **Acceptance criteria:**
  - [ ] Nightly cron job reads diff store
  - [ ] Groups diffs by skill and edit type
  - [ ] When 10+ similar edits exist, distills candidate rule
  - [ ] Candidate rule validated against recent outputs
  - [ ] Validated rules written to skill file with changelog entry
  - [ ] Rules unused for 30 days flagged for removal
- **DoD:** SWElfare skills auto-improve from human edit patterns. Stale rules are flagged.

### ADLC-040: Add feedback capture to Magnus content pipeline
- **Repo:** `magnus`
- **What:** Capture diffs between Magnus draft content and Eric's edited/published versions. Feed into voice profile and content-forge skill refinement.
- **Acceptance criteria:**
  - [ ] Post-publish hook captures diff between draft and final
  - [ ] Diffs classified: voice adjustment, structure change, fact correction, slop removal
  - [ ] Diffs stored with timestamp and content type
  - [ ] Nightly distillation updates voice profile and content-forge rules
- **DoD:** Magnus voice profile and content skills improve from Eric's edits.

### ADLC-041: Add feedback capture to Ratatosk trade outcomes
- **Repo:** `ratatosk`
- **What:** Capture trade outcome diffs: predicted outcome vs actual outcome. Feed into strategy parameters and signal weighting. (Extends existing experiment loop.)
- **Acceptance criteria:**
  - [ ] Post-settlement captures: predicted P&L vs actual P&L, predicted timeframe vs actual
  - [ ] Diffs classified: thesis error, timing error, sizing error, execution error
  - [ ] Experiment loop integrates outcome diffs for parameter tuning
  - [ ] Nightly distillation updates signal weighting and strategy params
- **DoD:** Ratatosk strategy evolves from trade outcome analysis.

---

## Phase 10: Pipeline Observability

### ADLC-042: Add pipeline audit logging to SWElfare
- **Repo:** `swelfare`
- **What:** Add structured audit log emission at every pipeline phase per Appendix A schema. Every phase, council decision, revision loop, and gate pass/fail is logged.
- **Acceptance criteria:**
  - [ ] Every phase emits structured JSON audit log entry
  - [ ] Schema matches Appendix A
  - [ ] Council verdicts logged per Appendix B schema
  - [ ] DoD verification logged per Appendix C schema
  - [ ] Logs stored in persistent, queryable format
  - [ ] Total pipeline metrics available: duration, tokens, revision count
- **DoD:** Full pipeline trace available for any SWElfare pipeline run.

### ADLC-043: Add pipeline audit logging to Ratatosk
- **Repo:** `ratatosk`
- **What:** Add structured audit logging for trade pipeline: signal classification, thesis generation, council review, risk gate, execution, settlement.
- **Acceptance criteria:**
  - [ ] Every trade pipeline step emits structured JSON audit log
  - [ ] Council decisions logged
  - [ ] Risk gate pass/fail logged
  - [ ] Execution details logged (entry price, size, timing)
  - [ ] Settlement reconciliation logged
- **DoD:** Full trade audit trail available for any Ratatosk trade.

### ADLC-044: Add pipeline audit logging to Magnus
- **Repo:** `magnus`
- **What:** Add structured audit logging for content pipeline: ingest classification, brief generation, council review, draft quality scores, slop gate scores, publish confirmation, engagement tracking.
- **Acceptance criteria:**
  - [ ] Every content pipeline step emits structured JSON audit log
  - [ ] Slop gate scores logged (all 5 dimensions)
  - [ ] Council decisions logged
  - [ ] Publish confirmation logged
  - [ ] Engagement metrics linked to pipeline run
- **DoD:** Full content audit trail available for any Magnus content piece.

---

## Phase 11: Eval Council Upgrades

### ADLC-045: Update eval-council skill to ADLC v2 (6 personas, opt-OUT)
- **Repo:** `~/.claude/skills/eval-council/`
- **What:** Update SKILL.md to: add Security Auditor as 6th persona, formalize opt-OUT default (everything reviewed unless excluded with justification), add static pre-checks that run before council tokens are spent.
- **Acceptance criteria:**
  - [ ] 6 personas defined (Architect, Skeptic, Operator, Executioner, Security Auditor, First Principles)
  - [ ] Opt-OUT default documented with exclusion justification requirement
  - [ ] Static pre-checks listed (zero-read, TDD, STRIDE, observability, reuse, DoD presence)
  - [ ] Static check failures return brief to Phase 1 without council
  - [ ] Domain adaptation notes for all three repos
- **DoD:** Eval council skill matches ADLC v2 spec.

### ADLC-046: Add Ratatosk domain-adapted council
- **Repo:** `ratatosk`
- **What:** Replace single arbiter-review with full 6-persona council adapted to investment domain. Architect=portfolio strategy, Skeptic=bearish thesis, Operator=execution feasibility, Executioner=can agent execute trade, Security=API/funds safety, First Principles=thesis soundness.
- **Acceptance criteria:**
  - [ ] arbiter-review SKILL.md replaced with eval-council SKILL.md
  - [ ] 6 personas with investment-domain system prompts
  - [ ] Council runs for trades > configurable threshold (not just $100)
  - [ ] Verdicts: APPROVED / REVISION REQUIRED / BLOCKED
  - [ ] Trade cannot execute without council approval (for threshold trades)
- **DoD:** Ratatosk has full council. Arbiter replaced with multi-persona review.

### ADLC-047: Add Magnus domain-adapted council
- **Repo:** `magnus`
- **What:** Replace single content-judge with full 6-persona council adapted to content domain. Architect=content strategy, Skeptic=brand damage risk, Operator=platform publishability, Executioner=can agent produce this, Security=PII/reputation, First Principles=does this serve the ICP.
- **Acceptance criteria:**
  - [ ] content-judge SKILL.md enhanced with multi-persona council
  - [ ] 6 personas with content-domain system prompts
  - [ ] Council runs for high-visibility content (configurable threshold)
  - [ ] Verdicts: APPROVED / REVISION REQUIRED / BLOCKED
  - [ ] High-visibility content cannot publish without council approval
- **DoD:** Magnus has full council. Content-judge upgraded to multi-persona review.

---

## Phase 12: TDD Enforcement Hardening

### ADLC-048: Make SWElfare TDD enforcement blocking
- **Repo:** `swelfare`
- **What:** Update `swelfare_core/adlc/tdd_protocol.py` and orchestrator to enforce verifier discipline: no implementation without a task-matched failing signal first. Block execution if violated.
- **Acceptance criteria:**
  - [ ] Feature work requires failing behavior tests or acceptance tests before implementation
  - [ ] Bugfix work requires a failing reproducer before implementation
  - [ ] Build-validation and lint-cleanup work require a failing command or static-analysis signal before implementation
  - [ ] A verifier that passes on first run is flagged for investigation
  - [ ] Tests validate blocking behavior for each verifier mode
- **DoD:** SWElfare verifier discipline is blocking. Violations stop the pipeline.

### ADLC-049: Add security-specific tests to TDD protocol
- **Repo:** `swelfare`
- **What:** Enhance verifier discipline so tasks with active security overlays generate security-specific checks for declared mitigations.
- **Acceptance criteria:**
  - [ ] Active STRIDE mitigations generate corresponding security checks
  - [ ] Security checks run only when the task's applicability manifest activates the security overlay
  - [ ] Missing security checks for active mitigations → pipeline BLOCKED
  - [ ] Tests validate security test generation from STRIDE model
- **DoD:** Tasks with active security overlays carry corresponding security verifiers.

### ADLC-050: Add observability tests to TDD protocol
- **Repo:** `swelfare`
- **What:** Enhance verifier discipline so tasks with active observability overlays generate checks that verify required logging is present.
- **Acceptance criteria:**
  - [ ] Active observability contract logging points generate corresponding checks
  - [ ] Checks verify: log statement exists, correct level, correct format, required fields present
  - [ ] Missing observability checks for active overlays → pipeline BLOCKED
  - [ ] Tests validate observability test generation from contract
- **DoD:** Tasks with active observability overlays carry corresponding observability verifiers.

---

## Phase 13: Build Brief Enhancement

### ADLC-051: Add scalability analysis to SWElfare brief generation
- **Repo:** `swelfare`
- **What:** Enhance brief generator to include availability and scalability analysis per task: load expectations, failure modes, degradation strategy, horizontal scaling path, SLA impact.
- **Acceptance criteria:**
  - [ ] TaskSpec has `scalability_analysis: ScalabilityAnalysis` field
  - [ ] ScalabilityAnalysis dataclass: load_expectations, failure_modes, degradation_strategy, scaling_path, sla_impact
  - [ ] Brief generator populates scalability analysis
  - [ ] Council reviews scalability analysis in Phase 2
- **DoD:** Every TaskSpec includes scalability analysis.

### ADLC-052: Add parallel task dispatch to SWElfare codegen context
- **Repo:** `swelfare`
- **What:** Enhance context assembler to flag independent tasks as `parallel: true` and generate separate context documents for simultaneous dispatch.
- **Acceptance criteria:**
  - [ ] Dependency analysis identifies independent tasks
  - [ ] Independent tasks flagged `parallel: true`
  - [ ] Separate context documents generated for parallel tasks
  - [ ] Orchestrator dispatches parallel tasks simultaneously
  - [ ] Tests validate parallel detection and dispatch
- **DoD:** Independent tasks execute in parallel. Dependencies respected.

### ADLC-053: Add security contract to SWElfare codegen context
- **Repo:** `swelfare`
- **What:** Enhance context assembler to include Section 9 (Security Contract) from STRIDE mitigations. Inlines trust boundaries, input validation requirements, and specific mitigations.
- **Acceptance criteria:**
  - [ ] Context assembly includes Section 9: Security Contract
  - [ ] STRIDE mitigations inlined as implementation requirements
  - [ ] Trust boundary diagram included
  - [ ] Input validation requirements specified
  - [ ] Tests validate security contract section presence
- **DoD:** Every codegen context includes security contract from STRIDE analysis.

### ADLC-054: Add observability contract to SWElfare codegen context
- **Repo:** `swelfare`
- **What:** Enhance context assembler to include Section 10 (Observability Contract). Inlines required error/audit/general logging points with format specification.
- **Acceptance criteria:**
  - [ ] Context assembly includes Section 10: Observability Contract
  - [ ] Required logging points listed with: where, what, format, level
  - [ ] Correlation ID propagation requirements included
  - [ ] Tests validate observability contract section presence
- **DoD:** Every codegen context includes observability contract.

---

## Phase 14: Orchestration Skills

### ADLC-055: Create build-feature orchestration skill
- **Repo:** `~/.claude/skills/`
- **What:** Create orchestration skill that chains the full build loop: PRD → Brief → Council → Scaffold → Codegen → LDD → TDD → Council → PR.
- **Acceptance criteria:**
  - [ ] Skill defines the complete sequence with dependencies
  - [ ] Each step references the corresponding core skill
  - [ ] Failure at any step triggers the appropriate response (revision loop, escalation)
  - [ ] Parallel dispatch opportunities identified
  - [ ] Domain-agnostic (works for SWElfare, Ratatosk, Magnus with config)
- **DoD:** Orchestration skill exists that chains the full build loop.

### ADLC-056: Create fix-bug orchestration skill
- **Repo:** `~/.claude/skills/`
- **What:** Create orchestration skill that chains the fix loop: Investigate → Brief(light) → LDD → TDD → Council(light) → PR.
- **Acceptance criteria:**
  - [ ] Skill defines the fix loop sequence
  - [ ] Light brief (no full decomposition — single fix task)
  - [ ] Light council (3 personas)
  - [ ] Escalation after 3 failures
  - [ ] Domain-agnostic
- **DoD:** Fix-bug orchestration skill exists.

### ADLC-057: Create ship-content orchestration skill (Magnus)
- **Repo:** `~/.claude/skills/`
- **What:** Create orchestration skill for Magnus content delivery: Brief → Council → Draft → Slop Gate → Council(light) → Publish.
- **Acceptance criteria:**
  - [ ] Skill defines the content delivery sequence
  - [ ] Full council for initial brief, light council for final review
  - [ ] Slop gate is hard gate (35/50)
  - [ ] Voice compliance checked at every stage
- **DoD:** Ship-content orchestration skill exists.

### ADLC-058: Create execute-trade orchestration skill (Ratatosk)
- **Repo:** `~/.claude/skills/`
- **What:** Create orchestration skill for Ratatosk trade execution: Thesis → Council → Risk Check → Execute → Audit → Report.
- **Acceptance criteria:**
  - [ ] Skill defines the trade execution sequence
  - [ ] Full council for thesis review
  - [ ] Risk gate is hard gate (position limits, drawdown limits, budget limits)
  - [ ] Audit logging at every step
  - [ ] Escalation for risk limit breaches
- **DoD:** Execute-trade orchestration skill exists.

---

## Summary

| Phase | Tickets | Repos affected |
|-------|---------|---------------|
| 1. Stop Slop | ADLC-001 through ADLC-006 | All three |
| 2. Security | ADLC-007 through ADLC-012 | All three |
| 3. LDD | ADLC-013 through ADLC-016 | All three |
| 4. Observability | ADLC-017 through ADLC-021 | All three |
| 5. PRD Agent | ADLC-022 through ADLC-025 | All three |
| 6. Reuse + Antipatterns | ADLC-026 through ADLC-029 | Shared + SWElfare |
| 7. DoD Formalization | ADLC-030 through ADLC-032 | Shared + SWElfare |
| 8. Fix Loop | ADLC-033 through ADLC-036 | All three |
| 9. Feedback Loop | ADLC-037 through ADLC-041 | All three |
| 10. Pipeline Observability | ADLC-042 through ADLC-044 | All three |
| 11. Council Upgrades | ADLC-045 through ADLC-047 | All three |
| 12. TDD Hardening | ADLC-048 through ADLC-050 | SWElfare |
| 13. Brief Enhancement | ADLC-051 through ADLC-054 | SWElfare |
| 14. Orchestration Skills | ADLC-055 through ADLC-058 | Shared |

**Total: 58 tickets across 14 phases.**

### Dependency Graph

```
Phase 1 (Stop Slop) ──────────────────────────────────────────── independent
Phase 2 (Security) ───────────────────────────────────────────── independent
Phase 3 (LDD) ────────────────────────────────────────────────── independent
Phase 4 (Observability) ──────────────────────────────────────── independent
Phase 5 (PRD Agent) ──────────────────────────────────────────── independent
Phase 6 (Reuse) ──────────────────────────────────────────────── independent
Phase 7 (DoD) ──── depends on: Phase 2 (security in DoD), Phase 3 (LDD in DoD), Phase 4 (observability in DoD)
Phase 8 (Fix Loop) ── depends on: Phase 2 (OWASP in fix), Phase 3 (LDD in fix), Phase 12 (TDD in fix)
Phase 9 (Feedback) ── depends on: Phase 1 (slop), Phase 5 (PRD structure)
Phase 10 (Audit) ──── depends on: Phase 7 (DoD schema)
Phase 11 (Council) ── depends on: Phase 2 (Security Auditor persona)
Phase 12 (Verifier discipline) ───── depends on: Phase 2 (security overlays when active), Phase 4 (observability overlays when active)
Phase 13 (Brief) ──── depends on: Phase 2, Phase 4, Phase 6
Phase 14 (Orchestration) ── depends on: all above
```

**Phases 1-6 can run in parallel.** Phases 7-14 have dependencies and should follow the order above.
