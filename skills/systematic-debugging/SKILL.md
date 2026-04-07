# Skill: Systematic Debugging

> 4-phase root cause investigation protocol for agent-driven debugging. Prevents "quick patch" guessing by enforcing evidence gathering, hypothesis formation, isolated testing, and defense-in-depth fixes. Designed for use by self-healing-agent on gate failures and by any agent encountering unexpected errors during execution.

---

## Why This Exists

Agents are biased toward action. When a test fails or a gate rejects, the default behavior is: guess what's wrong, apply a patch, retry. This works for trivial issues but compounds failures for anything non-obvious — the agent burns retries on symptoms instead of finding the root cause.

Systematic debugging enforces discipline: gather evidence first, form hypotheses second, test them third, fix last. The same protocol a senior engineer follows at 2am during an incident.

**When to use this skill:**
- Phase 4 gate failure after first retry
- self-healing-agent invoked on any error
- Build failures during Phase 3 that aren't obvious syntax errors
- E2E test failures that don't point to a single line
- Any error where the agent's first fix attempt failed

**When NOT to use this skill:**
- Obvious syntax errors (missing comma, typo)
- Import errors with clear messages
- Type errors with explicit expected/actual

---

## Trigger

```yaml
triggers:
  - event: gate_failure
    condition: retry_count >= 1
    action: invoke systematic-debugging before next retry
  - event: self_healing_invoked
    action: always invoke systematic-debugging
  - event: build_failure
    condition: error_message is not a simple syntax/import/type error
    action: invoke systematic-debugging
  - event: explicit_request
    action: user or coordinator says "debug this"
```

---

## The 4 Phases

### Phase 1: Gather Evidence (DO NOT SKIP)

Before forming any hypothesis, collect ALL available evidence. Agents skip this because they're eager to fix. Force them to slow down.

**Required evidence collection:**

```
EVIDENCE CHECKLIST:
[ ] Exact error message (full text, not summary)
[ ] Full stack trace (if available)
[ ] Which command/test/gate produced the error
[ ] What changed since the last working state (git diff)
[ ] Environment state (versions, config, running services)
[ ] Reproduction steps (can you trigger it reliably?)
[ ] Related log output (structured logs, not just the error line)
[ ] Recent changes to files in the error's dependency chain
```

**Evidence collection commands:**
```bash
# What changed
git diff HEAD~1
git log --oneline -10

# Full error context (not just the failing line)
[test command] 2>&1 | tail -100

# Dependency chain for the failing file
grep -r "import.*[failing_module]" --include="*.ts" --include="*.py"

# Check if the error is environment-specific
env | grep -i [relevant_var]
```

**Rule:** Phase 1 must produce at least 3 pieces of evidence before proceeding. If you have fewer than 3, you haven't looked hard enough.

---

### Phase 2: Form Hypotheses (Ranked by Likelihood)

From the evidence, generate 3 hypotheses. Not 1 (tunnel vision). Not 10 (unfocused). Exactly 3, ranked.

```
HYPOTHESIS TABLE:
| # | Hypothesis | Evidence Supporting | Evidence Against | Likelihood | Test |
|---|-----------|-------------------|-----------------|------------|------|
| H1 | [Most likely] | [What points here] | [What doesn't fit] | High | [How to confirm/reject] |
| H2 | [Second likely] | [What points here] | [What doesn't fit] | Medium | [How to confirm/reject] |
| H3 | [Less likely but possible] | [What points here] | [What doesn't fit] | Low | [How to confirm/reject] |
```

**Hypothesis quality rules:**
- Each hypothesis must explain ALL symptoms, not just some
- Each hypothesis must have a testable prediction (if H1 is true, then X should be observable)
- "The code is wrong" is not a hypothesis. "The share_config validation rejects valid input because the enum doesn't include the new mode" is a hypothesis
- If all 3 hypotheses point to the same area, you need more diverse thinking — consider: is it a data issue? A timing issue? A configuration issue? A dependency issue?

---

### Phase 3: Test Hypotheses (Isolate the Failing Component)

Test each hypothesis **in order of likelihood**, stopping when confirmed.

**For each hypothesis:**
1. Define the test that would confirm or reject it
2. Execute the test (minimal, isolated — don't change production code yet)
3. Record the result
4. If rejected, move to the next hypothesis

**Testing techniques:**

| Technique | When to Use | How |
|-----------|------------|-----|
| **Minimal reproduction** | Complex failures | Strip the scenario to the smallest case that still fails |
| **Bisection** | "It worked before" | `git bisect` or manual binary search through recent commits |
| **Component isolation** | Multi-service errors | Test each component independently with mocked boundaries |
| **Input variation** | Data-dependent errors | Try with different inputs — what specific input triggers the failure? |
| **Condition-based waiting** | Timing/race conditions | Add explicit waits or polling instead of sleep. Check for the condition, not a duration |
| **Log injection** | Black-box failures | Add temporary structured logging at each step of the failing path |
| **Defense in depth** | Intermittent failures | Test multiple layers: Does the data exist? Is the query correct? Is the response parsed correctly? Is the UI rendering the response? |

**Rule:** Each test must produce a clear CONFIRMED or REJECTED result. "Maybe" means you need a better test.

---

### Phase 4: Fix and Verify (Defense in Depth)

Once root cause is confirmed, fix it properly. Not a quick patch — a defense-in-depth fix.

**Fix protocol:**
1. **Fix the root cause** — not the symptom
2. **Add a regression test** — a test that would have caught this before it happened
3. **Check for similar patterns** — if this bug exists here, does it exist in similar code elsewhere?
4. **Verify the fix** — run the originally failing test/gate
5. **Check for regressions** — run the full test suite
6. **Document the root cause** — structured output for learning capture

**Defense-in-depth checklist:**
```
FIX VERIFICATION:
[ ] Root cause fix applied (not a workaround)
[ ] Regression test added (test fails without fix, passes with fix)
[ ] Similar code checked for same bug pattern
[ ] Originally failing test/gate now passes
[ ] Full test suite passes (no regressions)
[ ] Fix does not modify test expectations (unless tests were wrong)
```

---

## Output Format

Every debugging session produces this structured output, whether the bug is found in 2 minutes or 20.

```yaml
debugging_report:
  version: 1
  trigger: "gate_failure | self_healing | build_failure | explicit"
  symptom: "1-line description of what went wrong"

  evidence:
    error_message: "exact error text"
    stack_trace: "if available"
    command: "what command produced the error"
    git_diff_summary: "what changed since last working state"
    reproduction: "reliable | intermittent | once"
    related_logs: []

  hypotheses:
    - id: H1
      description: "string"
      likelihood: "high | medium | low"
      test: "how to confirm/reject"
      result: "confirmed | rejected"
      evidence: "what the test showed"
    - id: H2
      description: "string"
      likelihood: "high | medium | low"
      test: "how to confirm/reject"
      result: "confirmed | rejected"
      evidence: "what the test showed"
    - id: H3
      description: "string"
      likelihood: "high | medium | low"
      test: "how to confirm/reject"
      result: "confirmed | rejected | not_tested"
      evidence: "what the test showed"

  root_cause:
    confirmed_hypothesis: "H1 | H2 | H3 | none"
    description: "what actually caused the failure"
    category: "logic_error | data_issue | config_error | race_condition | dependency_change | schema_mismatch | missing_validation | other"
    affected_files: []

  fix:
    changes: []
    regression_test_added: true
    similar_patterns_checked: true
    full_suite_passes: true

  learnings:
    pattern: "what class of bug this is"
    prevention: "how to prevent this in future"
    detection: "how to catch this earlier"

  time_spent:
    evidence_gathering: "Xm"
    hypothesis_formation: "Xm"
    hypothesis_testing: "Xm"
    fix_and_verify: "Xm"
    total: "Xm"
```

---

## Integration with ADLC Pipeline

### self-healing-agent Integration

When self-healing-agent is invoked on a gate failure:

```
Gate fails (retry_count >= 1)
  │
  ├─→ self-healing-agent invokes systematic-debugging
  │     │
  │     ├── Phase 1: Gather evidence from gate output + git diff
  │     ├── Phase 2: Form 3 hypotheses
  │     ├── Phase 3: Test hypotheses (read-only — no file changes yet)
  │     ├── Phase 4: Apply fix + regression test
  │     │
  │     └── Return debugging_report to coordinator
  │
  ├─→ Re-run ONLY the failed gate
  │
  └─→ If still fails after 3 debugging cycles: escalate to user
```

### Coordinator Integration

The coordinator uses the debugging_report to route fixes:

```yaml
routing:
  logic_error: → agent that owns the failing file
  data_issue: → data-agent
  config_error: → infra-agent
  race_condition: → backend-agent (add proper synchronization)
  dependency_change: → coordinator (may need re-planning)
  schema_mismatch: → data-agent + migration
  missing_validation: → agent that owns the endpoint
```

### History Capture

Every debugging_report with `time_spent.total > 10m` is automatically captured by history-agent as a LEARNING, so the same root cause pattern is recognized faster next time.

---

## Anti-Patterns (What NOT to Do)

| Anti-Pattern | Why It's Bad | Do This Instead |
|-------------|-------------|-----------------|
| Fix without evidence | You're guessing. Guesses compound. | Phase 1 first. Always. |
| Single hypothesis | Tunnel vision. You'll force-fit evidence. | 3 hypotheses minimum. |
| Modify tests to pass | Hides the bug. Ships broken code. | Tests are the spec. Fix the code, not the test. |
| Retry without understanding | Same input, same output. Wasted retries. | Systematic debugging between retries. |
| "It works now" without understanding why | The bug is still there. It'll come back. | Root cause must be identified and documented. |
| Quick patch on symptom | Treats the symptom, not the disease. | Defense-in-depth: root cause + regression test + similar pattern check. |
| Changing multiple things at once | Can't tell which change fixed it. | One change at a time. Test after each. |

---

## Quality Gates

- [ ] Phase 1 produced at least 3 pieces of evidence
- [ ] Phase 2 produced exactly 3 ranked hypotheses with testable predictions
- [ ] Phase 3 tested hypotheses in order, each with clear confirmed/rejected result
- [ ] Phase 4 fix addresses root cause, not symptom
- [ ] Regression test added that fails without fix, passes with fix
- [ ] Full test suite passes after fix
- [ ] debugging_report YAML is complete (no empty fields)
- [ ] If time_spent > 10m, learning captured to history

## Framework Hardening Addendum

- **Contract versioning:** Debug session inputs/outputs include `contract_version` with compatibility checks.
- **Schema validation:** Validate debugging reports against the declared report structure before persistence or handoff.
- **Workflow checkpoints:** Persist checkpoints after each debugging phase (evidence, hypothesis, test, fix) via `docs/specs/workflow-checkpoints.md`.
- **Stop reasons:** Emit structured terminal reasons for unresolved incidents (`dependency_change`, `schema_mismatch`, `timeout`).

