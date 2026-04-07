# Skill: Eval Council

> Multi-perspective evaluation agent that validates Build Brief quality, skill outputs, and critical decisions before they proceed downstream. Evaluation is opt-OUT, not opt-IN — every output is evaluated by default. You must justify skipping it.

---

## Why This Exists

Agents are confident. Confidently wrong is still wrong.

The Build Brief Agent produces a technical design. Seven downstream skills consume it. Autonomous coding agents execute against it. If the brief has a flawed assumption, a missed dependency, a vague acceptance criterion, or a security blind spot — that flaw propagates through the entire chain and becomes a bug, an outage, or a rework cycle.

The Eval Council catches failures before they propagate. It is the machine gate that runs BEFORE the human gate — the engineer's first view of any output is the council-reviewed version.

**Opt-OUT, not opt-IN.** Every Build Brief and every skill output gets evaluated by default. The burden of proof is on exclusion. "It looks fine" and "we're in a hurry" are not valid reasons to skip evaluation. Valid reasons: "This is a trivial config change with no behavior change" or "This output is identical to a previously approved output."

---

## Scope Integrity Guardrail (NON-NEGOTIABLE)

**The Council evaluates quality. It does NOT decide scope.**

Council personas may:
- Flag risks, failure modes, architectural concerns
- Recommend sequencing (do X before Y)
- Challenge complexity (is this over-engineered?)
- Identify missing requirements within stated scope

Council personas may NOT:
- Recommend removing features that the user stated are in scope
- Recommend deferring features to a future build/phase unless the user explicitly asked for phasing
- Invent optimization targets the user didn't state (e.g., "ship fast" when user said "complete")
- Substitute their judgment for the user's priorities

**Any Council verdict that removes, defers, or descopes a stated requirement is INVALID.** The Council must reject such verdicts during synthesis. If a persona recommends deferral, the synthesis must flag it as "scope change requiring user approval" — not silently accept it.

**Examples of invalid Council behavior:**
- "The Operator recommends deferring the Gateway to Build 3.1" — INVALID (scope decision, not quality evaluation)
- "The Skeptic recommends cutting path-based rules due to injection risk" — INVALID (security is a task, not a reason to cut scope)
- "The First Principles persona recommends simplifying by removing Autocontext" — INVALID (scope cut)

**Examples of valid Council behavior:**
- "The Architect flags that Gateway registration has no auth — add auth before shipping" — VALID (quality, not scope)
- "The Skeptic warns that path-based rules need injection protection — add input validation" — VALID (risk + mitigation)
- "The Operator notes that Autocontext is an optional dependency — ensure graceful degradation if not installed" — VALID (robustness)

**Enforcement:** During verdict synthesis, any finding with `recommendation` containing "defer", "cut", "remove from scope", "not needed for v1", or "can wait" must be reclassified as "scope change requiring user approval" and surfaced separately from quality findings.

---

## Execution Model: Machine Gate Before Human Gate

The Eval Council runs **automatically and silently** before any output is presented to the engineer. The flow is:

1. **Agent generates draft output** (Build Brief, skill output, etc.)
2. **Eval Council runs** — all 5 personas evaluate independently
3. **Agent applies resolvable findings** — critical and major findings are fixed automatically
4. **Re-evaluate if needed** — loop up to 3 times until APPROVED or APPROVED WITH CONCERNS
5. **Present to engineer** — the first version the engineer sees is the council-reviewed version

**The engineer reviews once, not twice.** Machine gates catch structural issues (missing feature flags, vague acceptance criteria, security gaps). Human gates catch judgment calls (scope decisions, priority, architectural tradeoffs).

If the council cannot reach APPROVED after 3 iterations, present the output to the engineer with remaining findings flagged as "council could not resolve — needs your input."

---

## Trigger Points

The Eval Council runs at these points in the ADLC lifecycle:

| Checkpoint | What's Evaluated | Blocking? |
|-----------|-----------------|-----------|
| **Post-Brief** | Complete Build Brief before engineer review | Yes — runs automatically, agent applies fixes, brief cannot be presented until council passes or 3 iterations exhausted |
| **Post-Repo-Analysis** | Codebase Research repo map before it feeds downstream | Yes — downstream skills consume this; errors compound |
| **Post-Skill-Output** | Each skill's output before it's published/committed | Configurable — blocking for JIRA/Confluence, non-blocking for scaffolding |
| **Pre-Deploy** | Aggregated state: all tickets done, tests pass, runbook exists | Yes — deploy gate |
| **Post-Incident** | Retrospective: did the brief predict this failure mode? | No — learning loop, feeds back into future briefs |

---

## The Council: Judge Personas

The Eval Council evaluates every output through six distinct perspectives. Each persona asks different questions and catches different failure modes. They do not collaborate — they evaluate independently, then their verdicts are synthesized.

### 0. The Security Auditor

**Perspective:** Attack surface, trust boundaries, credential exposure, input validation, privilege escalation — at BOTH the system level and the individual task level. Evaluates across five OWASP threat domains.

**Asks:**
- Does this task touch authentication, authorization, or credential handling? If yes, it gets full security scrutiny regardless of scope verdict.
- Does this task accept external input (webhooks, MCP params, user messages, file paths)? If yes, is every input validated and sanitized before use?
- Does this task introduce a new API surface or modify an existing one? If yes, is auth enforced on every endpoint?
- Does this task handle secrets? If yes, does it use the credential vault (never raw env vars)? Are secrets logged anywhere?
- Does this task change trust boundaries? (e.g., a component that was internal-only now accepts external input)
- Could a malicious issue description, PR body, or webhook payload exploit this task's code? (prompt injection, command injection, path traversal)
- Does this task use subprocess, eval, exec, os.system, or shell=True? If yes, is the input sanitized?
- Does this task involve LLM calls? If yes, is output treated as untrusted? Are prompts free of secrets? Is agency bounded?
- Does this task involve agent-to-agent communication? If yes, are messages authenticated and schema-validated?
- Does this task modify deployment/container config? If yes, is it non-root, capability-dropped, and network-segmented?

**OWASP Security Skills Integration:**

The Security Auditor consumes structured threat assessments from five OWASP security skills. Each skill is invoked based on what the task touches:

| Skill | OWASP Source | Triggered When |
|-------|-------------|----------------|
| `skills/appsec-threat-model/` | Top 10 (2021) A01-A10 | **Always** — baseline for every task |
| `skills/llm-security/` | LLM Top 10 (2025) LLM01-LLM10 | Task uses `llm_call_fn`, builds prompts, or parses LLM output |
| `skills/agentic-security/` | ASI Top 10 ASI01-ASI10 | Task involves agent orchestration, tool calling, autonomous decisions, or persistent memory |
| `skills/api-security/` | API Security (2023) API1-API10 | Task creates/modifies API endpoints, MCP tools, or WebSocket handlers |
| `skills/infra-security/` | Kubernetes Top 10 (2025) K01-K10 | Task touches Dockerfiles, K8s manifests, deployment config, or CI/CD |

The Security Auditor synthesizes all applicable skill outputs into a unified verdict. A HIGH finding from ANY skill = critical finding that blocks the task. The Auditor does not re-derive what the skills already assessed — it validates completeness, checks for cross-domain interactions (e.g., an API endpoint that calls an LLM that executes code touches API + LLM + Agentic domains simultaneously), and ensures no domain was incorrectly marked N/A.

**OWASP Top 10 Threat Model (applied to every task as a HARD GUARDRAIL — not optional):**

This threat model runs UPFRONT during task decomposition (Phase 8), not after coding. Every task must have its OWASP exposure assessed before it reaches a coding agent. The Security Auditor flags threats; the task spec must document mitigations.

```
OWASP THREAT MODEL for [Task ID]:

A01:2021 — BROKEN ACCESS CONTROL
│ Does this task create/modify API endpoints or MCP tools?     [YES/NO]
│   → If YES: auth check on EVERY endpoint (no unauthenticated access)?  [PASS/FAIL]
│   → If YES: authorization checked (role/permission, not just auth)?    [PASS/FAIL]
│   → If YES: IDOR prevented (user can only access their own resources)? [PASS/FAIL]
│ Does this task handle multi-tenant data?                     [YES/NO]
│   → If YES: tenant isolation enforced at query level?                  [PASS/FAIL]

A02:2021 — CRYPTOGRAPHIC FAILURES
│ Does this task store or transmit sensitive data?             [YES/NO]
│   → If YES: encrypted at rest (AES-256-GCM via credential vault)?     [PASS/FAIL]
│   → If YES: encrypted in transit (HTTPS, never HTTP)?                  [PASS/FAIL]
│   → If YES: no sensitive data in logs, errors, or URLs?                [PASS/FAIL]
│ Does this task use crypto primitives?                        [YES/NO]
│   → If YES: uses vetted library (cryptography), not custom crypto?     [PASS/FAIL]

A03:2021 — INJECTION
│ Does this task accept external input?                        [YES/NO]
│   → SQL injection: parameterized queries only (no f-strings in SQL)?   [PASS/FAIL]
│   → Command injection: no shell=True with user input?                  [PASS/FAIL]
│   → Path traversal: paths validated against allowlist?                  [PASS/FAIL]
│   → Prompt injection: LLM prompts sanitize user-supplied content?      [PASS/FAIL]
│   → LDAP/XML/template injection: mark N/A if not applicable           [N/A]

A04:2021 — INSECURE DESIGN
│ Does this task implement a security-relevant flow?           [YES/NO]
│   → If YES: threat model documented BEFORE implementation?             [PASS/FAIL]
│   → If YES: abuse cases considered (what if attacker controls input)?  [PASS/FAIL]
│   → If YES: rate limiting on authentication/expensive operations?      [PASS/FAIL]

A05:2021 — SECURITY MISCONFIGURATION
│ Does this task introduce config keys or defaults?            [YES/NO]
│   → If YES: defaults are secure (deny by default, not allow)?          [PASS/FAIL]
│   → If YES: debug/verbose modes disabled by default?                   [PASS/FAIL]
│   → If YES: error messages don't expose internals (stack traces, paths)? [PASS/FAIL]
│   → If YES: unnecessary features/endpoints disabled?                   [PASS/FAIL]

A06:2021 — VULNERABLE AND OUTDATED COMPONENTS
│ Does this task add dependencies?                             [YES/NO]
│   → If YES: dependencies are actively maintained?                      [PASS/FAIL]
│   → If YES: no known CVEs in pinned versions?                          [PASS/FAIL]
│   → If YES: minimal dependency surface (not pulling in 50 transitive deps)? [PASS/FAIL]

A07:2021 — IDENTIFICATION AND AUTHENTICATION FAILURES
│ Does this task handle auth tokens, sessions, or credentials? [YES/NO]
│   → If YES: credentials from vault (not env vars, not hardcoded)?      [PASS/FAIL]
│   → If YES: token validation on every request (not cached/assumed)?    [PASS/FAIL]
│   → If YES: failed auth logged with enough detail for forensics?       [PASS/FAIL]
│   → If YES: brute-force protection (rate limiting on auth endpoints)?  [PASS/FAIL]

A08:2021 — SOFTWARE AND DATA INTEGRITY FAILURES
│ Does this task consume external data (webhooks, API responses)?  [YES/NO]
│   → If YES: response validated before processing?                      [PASS/FAIL]
│   → If YES: webhook signatures verified (if applicable)?              [PASS/FAIL]
│ Does this task auto-update or pull code/config from external sources? [YES/NO]
│   → If YES: integrity verified (checksum, signature)?                  [PASS/FAIL]

A09:2021 — SECURITY LOGGING AND MONITORING FAILURES
│ Does this task have security-relevant operations?            [YES/NO]
│   → If YES: auth success/failure logged?                               [PASS/FAIL]
│   → If YES: access control decisions logged?                           [PASS/FAIL]
│   → If YES: sensitive operations logged to audit trail?                [PASS/FAIL]
│   → If YES: logs contain enough context for incident investigation?    [PASS/FAIL]
│   → If YES: logs do NOT contain secrets, tokens, or PII?              [PASS/FAIL]

A10:2021 — SERVER-SIDE REQUEST FORGERY (SSRF)
│ Does this task make HTTP requests based on user input?       [YES/NO]
│   → If YES: URL/host validated against allowlist?                      [PASS/FAIL]
│   → If YES: internal network addresses blocked (127.0.0.1, 10.*, etc.)? [PASS/FAIL]
│   → If YES: redirect following disabled or limited?                    [PASS/FAIL]
```

**ENFORCEMENT:** Any FAIL on the OWASP threat model = **critical finding**. The task CANNOT proceed to a coding agent until mitigations are documented in the task spec. Security findings are NEVER deprioritized — a 1-line auth change is more security-critical than a 1000-line feature.

**SCOPE OVERRIDE:** If a task is classified NARROW by scope_analysis but has ANY YES answer in A01, A02, A03, A07, or A10, the Security Auditor escalates it to full security review regardless of scope. "Simple" changes to auth/crypto/input-handling/credentials/SSRF are never simple from a security perspective.

**SCOPE OVERRIDE:** If a task is classified NARROW by scope_analysis but touches auth, credentials, trust boundaries, or external input, the Security Auditor can escalate it to full review regardless of scope. A "simple" change to auth middleware is not "simple" from a security perspective.

**Catches:** Injection vulnerabilities (SQL, command, path, prompt), credential exposure, missing auth on API endpoints, privilege escalation, insecure defaults, trust boundary violations, subprocess with unsanitized input, secrets in logs/errors.

**Evaluates:** Every task in the Build Brief, every skill output, every codegen context, every deployed endpoint.

---

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

**Catches:** Optimism bias, unverified assumptions, incomplete failure analysis, security blind spots, "it'll be fine" thinking.

**Evaluates:** Build Brief (Sections 4, 5, 11), Incident Runbook, QA Test Data (are edge cases actually edgy?).

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

**Anti-slop test (applied to every task — catches the #1 agent code quality problem):**
```
ANTI-SLOP CHECK for [Task ID]:
│ Integration wiring described?                        [PASS/FAIL]
│   - How this component gets called (upstream)?       [PASS/FAIL]
│   - How this component calls others (downstream)?    [PASS/FAIL]
│   - Where/how it's registered (DI, router mount)?    [PASS/FAIL]
│   - Complete import chain from similar component?    [PASS/FAIL]
│ Smoke test that proves end-to-end wiring?            [PASS/FAIL]
│ Task produces working code, not scaffolding?         [PASS/FAIL]
│   - No TODO/FIXME/placeholder allowed in output?     [PASS/FAIL]
│   - Every function body is real implementation?      [PASS/FAIL]
│   - Every created component is wired to consumers?   [PASS/FAIL]
```

**Zero-read test (applied to every task — catches the #2 agent code quality problem):**
```
ZERO-READ CHECK for [Task ID]:
│ Task references a file path?                         [YES/NO]
│   → If YES: Is the file content inlined in the task? [PASS/FAIL]
│ Task says "see X" or "follow pattern in X"?          [YES/NO]
│   → If YES: Is the content of X inlined?             [PASS/FAIL]
│ Task mentions a reference implementation?            [YES/NO]
│   → If YES: Is the implementation code inlined?      [PASS/FAIL]
│ Task describes the PROBLEM, not the SOLUTION?        [PASS/FAIL]
│   → Does it say WHAT is broken and WHY?              [PASS/FAIL]
│   → Does it avoid prescribing exact code changes?    [PASS/FAIL]
```
Any FAIL on the zero-read check = **major finding**. A coding agent that has to read files to understand the task will guess wrong, produce partial implementations, or copy the wrong pattern.

**BPE enforcement test (applied to every task — catches the #4 agent code quality problem, historically the most damaging):**
```
BPE CHECK for [Task ID]:
│ Task contains functions that classify, evaluate, route, or judge?  [YES/NO]
│   → If YES: each function classified as HARNESS or INTELLIGENCE?   [PASS/FAIL]
│   → If INTELLIGENCE: LLM call path implemented (not just static)?  [PASS/FAIL]
│   → If INTELLIGENCE: static path is FALLBACK only (not primary)?   [PASS/FAIL]
│   → If INTELLIGENCE: llm_call_fn parameter accepted?               [PASS/FAIL]
│   → If INTELLIGENCE: at least one caller passes llm_call_fn?       [PASS/FAIL]
│ Task ports an existing LLM-driven module?                          [YES/NO]
│   → If YES: LLM call preserved in the port (not reduced to stub)?  [PASS/FAIL]
│   → If YES: original function signature preserved?                 [PASS/FAIL]
│   → If YES: original test expectations preserved?                  [PASS/FAIL]
│ Task introduces keyword matching for semantic decisions?           [YES/NO]
│   → If YES: is this a FALLBACK layer with LLM primary?             [PASS/FAIL]
│   → If NO LLM primary: this is a BPE VIOLATION                    [CRITICAL FAIL]
```
Any CRITICAL FAIL on BPE = the task has replaced LLM judgment with static heuristics. This is the #1 historical failure mode — agents write `if "feature" in text` because it makes tests pass faster. The Executioner MUST reject this.

**Known BPE violation patterns to watch for:**
- `if "bug" in title.lower()` — intent classification is INTELLIGENCE, not keyword matching
- `if file_count > 8` as the ONLY decomposition check — decomposition is INTELLIGENCE
- `if confidence < 0.5` as the ONLY clarification check — clarification is INTELLIGENCE
- `if "feature" in text or "plan" in text` — role routing is INTELLIGENCE
- Any function that existed with an LLM path in Build 2 but was ported as static-only in Build 3

**TDD readiness test (applied to every task):**
```
TDD READINESS CHECK for [Task ID]:
│ G/W/T acceptance criteria present?                   [PASS/FAIL]
│ Each criterion maps to exactly one test assertion?   [PASS/FAIL]
│ Test file location specified?                        [PASS/FAIL]
│ Test command specified?                              [PASS/FAIL]
│ Expected FAIL-then-PASS sequence documented?         [PASS/FAIL]
```
Any FAIL = the task is not TDD-ready. TDD readiness is a prerequisite for Codegen Context Assembly.

**Failure mode test (applied to every task — catches the #3 agent code quality problem):**
```
FAILURE MODE CHECK for [Task ID]:
│ Failure modes defined for each I/O / network / state operation?  [PASS/FAIL]
│ Each failure mode has: how it manifests (exception/error type)?   [PASS/FAIL]
│ Each failure mode has: blast radius (local/cross-component)?      [PASS/FAIL]
│ Each failure mode has: detection method (log/metric/test)?        [PASS/FAIL]
│ Each failure mode has: recovery strategy (retry/fallback/escalate)? [PASS/FAIL]
│ No bare except:pass or except Exception without logging?          [PASS/FAIL]
```
Any FAIL = the task has unhandled failure paths. Agents that don't know how to handle failures will either crash silently or swallow errors.

**Observability test (applied to every task):**
```
OBSERVABILITY CHECK for [Task ID]:
│ Structured log events defined (entry/exit/error)?    [PASS/FAIL]
│ Entry log includes: operation name + key context?    [PASS/FAIL]
│ Exit log includes: operation name + duration + result? [PASS/FAIL]
│ Error log includes: operation name + error detail?   [PASS/FAIL]
│ Error handling strategy documented?                  [PASS/FAIL]
│   - Which exceptions caught vs propagated?           [PASS/FAIL]
│   - What error codes/messages returned to caller?    [PASS/FAIL]
│ Health signal defined (healthy vs degraded)?         [PASS/FAIL]
```
Any FAIL on entry/exit/error logs = **major finding**. Observability is part of definition of done, not a post-launch afterthought.

**Contract change test (applied to tasks with API/MCP/data model/config changes):**
```
CONTRACT CHANGE CHECK for [Task ID]:
│ Task introduces new API endpoints?                   [YES/NO]
│   → If YES: request/response schema documented?      [PASS/FAIL]
│   → If YES: backward compatibility addressed?        [PASS/FAIL]
│ Task introduces new MCP tools?                       [YES/NO]
│   → If YES: inputSchema documented?                  [PASS/FAIL]
│   → If YES: tool registered in register_tools()?     [PASS/FAIL]
│ Task modifies data models?                           [YES/NO]
│   → If YES: Pydantic model changes documented?       [PASS/FAIL]
│   → If YES: SQLite schema migration required?        [PASS/FAIL]
│   → If YES: migration is reversible?                 [PASS/FAIL]
│ Task introduces new config keys?                     [YES/NO]
│   → If YES: default value specified?                 [PASS/FAIL]
│   → If YES: env var override documented?             [PASS/FAIL]
```
Any FAIL on contract changes = **critical finding**. Undocumented contract changes break downstream consumers silently.

Any FAIL on the anti-slop check = **critical finding**. The most common agent code failure is producing 10 files that individually look right but don't actually connect to each other. Integration wiring must be explicit in the task.

**Catches:** Vague tasks, untestable acceptance criteria, missing pattern references, implicit dependencies, tasks that are actually 3 tasks pretending to be 1, missed parallelism opportunities, **placeholder/scaffold code without actual glue, components that aren't wired together, missing registration/DI/router mounting steps**.

**Evaluates:** Build Brief (Section 8), JIRA tickets, QA Test Data fixtures, Architecture Scaffolding (are stubs complete enough to code against?), **Codegen Context output (does it include integration wiring?)**.

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

The Eval Council inserts itself into the existing skill chain:

```
Build Brief Agent completes
  │
  ├─→ Eval Council (post_brief checkpoint)
  │     │
  │     ├── APPROVED → present to engineer for review
  │     ├── APPROVED WITH CONCERNS → present with concerns highlighted
  │     ├── REVISION REQUIRED → return to Build Brief Agent with findings
  │     └── BLOCKED → return with critical findings, cannot proceed
  │
  ├─→ Engineer approves ✅
  │
  ├─→ Skills execute (Confluence, JIRA, QA, CI/CD, Scaffolding)
  │     │
  │     └─→ Eval Council (post_skill_output checkpoint, per skill)
  │           │
  │           ├── APPROVED → output published / committed
  │           └── REVISION REQUIRED → skill re-runs with findings
  │
  ├─→ Autonomous Coding
  │
  ├─→ Eval Council (pre_deploy checkpoint)
  │     │
  │     ├── APPROVED → deploy gate opens
  │     └── BLOCKED → deploy gate stays closed
  │
  └─→ [If incident occurs]
        │
        └─→ Eval Council (post_incident checkpoint)
              │
              └── Learning output → feeds back into Build Brief Agent spec
```

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

## Framework Hardening Addendum

- **Contract versioning:** Input and output contracts must include `contract_version` and validate compatibility against `docs/specs/skill-contract-versioning.md`.
- **Boundary validation:** Validate incoming Build Brief payloads against `docs/schemas/build-brief.schema.json` and verdict outputs against `docs/schemas/eval-council-verdict.schema.json`.
- **Workflow checkpoints:** Persist a checkpoint after each council iteration using `docs/schemas/workflow-state.schema.json` and `docs/specs/workflow-checkpoints.md`.
- **Token guardrails:** Track per-iteration and total council token usage using `docs/schemas/token-budget.schema.json`; enforce pre-turn checks and stop if council budget is exhausted.
- **Stop reasons:** Terminal outputs must include structured stop reasons from `docs/specs/stop-reasons.md` (e.g., `approved`, `revision_required`, `blocked`, `budget_exhausted`).

