# Skill: TDD Enforcement

> Enforces test-driven development during Phase 3 (Build). Every task follows the RED-GREEN-REFACTOR cycle: write the failing test from G/W/T criteria FIRST, verify it fails, implement until it passes, then commit. Shifts bug detection from Phase 4 gates to Phase 3 execution — catching bugs at the task level is cheaper than catching them at the gate level.

---

## Why This Exists

The ADLC pipeline currently writes tests in two places:
1. **QA Test Data skill** generates test scenarios from G/W/T after the Build Brief is approved
2. **testing-agent** runs in Phase 4 to verify coverage

The gap: during Phase 3 (Build), coding agents implement features and only discover test failures in Phase 4. By then, multiple tasks may have shipped broken code, and the failure feedback loop is slow (implement all → gate fails → figure out which task broke → fix → re-gate).

TDD Enforcement closes this gap by making every coding agent write and run the failing test BEFORE implementing. The agent knows immediately when its code works — no waiting for Phase 4.

**The Iron Law:** No production code without a failing test first. Code written before the test exists gets deleted.

---

## Trigger

This skill operates at TWO levels:

**Level 1 (Brief Time — Phase 8):** TDD protocol is embedded as a MANDATORY FIELD in every task in the Build Brief. The Build Brief Agent includes test file location, test command, and FAIL-then-PASS cycle per G/W/T criterion directly in the task definition. This happens BEFORE any coding agent is dispatched. If a task reaches Phase 3 without TDD protocol in its definition, the Eval Council Executioner rejects it.

**Level 2 (Execution Time — Phase 3):** During coding, the Codegen Context Assembly skill includes the TDD protocol from the task definition and the pre-written test file contents in the assembled prompt. The coding agent follows RED-GREEN-REFACTOR per criterion.

```yaml
triggers:
  - phase: 8  # Task Breakdown (brief time)
    event: task_defined_without_tdd_protocol
    action: reject — Build Brief Agent must add TDD protocol fields
  - phase: 3  # Build (execution time)
    event: task_dispatched_to_coding_agent
    action: verify TDD protocol present in assembled context
  - phase: 3
    event: code_written_without_test
    action: reject — delete code, write test first
```

**Why both levels matter:** If TDD is only injected at execution time (Level 2), it depends on the Codegen Context Assembly skill running — which was previously optional (Gap 1). By embedding TDD in the task definition at brief time (Level 1), every task carries its own test protocol regardless of whether context assembly runs.

---

## The RED-GREEN-REFACTOR Cycle (Per Task)

Every task follows this exact sequence. No exceptions.

### Step 1: RED (Write the Failing Test)

Before writing any production code, the coding agent writes a test from the task's G/W/T acceptance criteria.

```
GIVEN the task has acceptance criteria:
  Given [precondition]
  When [action]
  Then [expected outcome]

The agent writes a test that:
1. Sets up the precondition
2. Performs the action
3. Asserts the expected outcome
```

**Then run the test. It MUST fail.** If the test passes without any new code, either:
- The feature already exists (check with coordinator)
- The test isn't testing the right thing (fix the test)

```bash
# Run ONLY this task's test
[test_command] --filter "[test_name]"

# Expected output: FAIL
# If PASS: stop. Something is wrong. Investigate before proceeding.
```

**What the test looks like:**

For backend (Python/FastAPI):
```python
@pytest.mark.asyncio
async def test_share_deliverable_sends_email():
    """
    GIVEN a deliverable exists and a recipient user is in the same org
    WHEN the sender calls POST /deliverables/{id}/share with recipient_user_ids
    THEN an email is dispatched to each recipient and share_config is updated
    """
    # Setup precondition
    deliverable = await create_test_deliverable(...)
    recipient = await create_test_user(org_id=deliverable.organization_id)

    # Action
    response = await client.post(
        f"/deliverables/{deliverable.deliverable_id}/share",
        json={"recipient_user_ids": [recipient.user_id], "share_mode": "users"}
    )

    # Assertion
    assert response.status_code == 200
    invitation = await get_share_invitation(deliverable_id=deliverable.deliverable_id)
    assert invitation is not None
    assert invitation.recipient_user_id == recipient.user_id
    assert invitation.email_status == "pending"
```

For frontend (Playwright/Vitest):
```typescript
test('share modal shows org user search on open', async ({ page }) => {
  // GIVEN a deliverable is displayed in fullscreen view
  await page.goto(`/organization/${orgId}/team/${teamId}/writer-agent/thread/${threadId}`);
  await page.getByTestId('deliverable-fullscreen').waitFor();

  // WHEN the user clicks Share
  await page.getByRole('button', { name: 'Share' }).click();

  // THEN a searchable dropdown shows org users
  await expect(page.getByTestId('share-modal')).toBeVisible();
  await expect(page.getByPlaceholder('Search people')).toBeVisible();
});
```

### Step 2: GREEN (Make It Pass)

Now write the minimal production code to make the test pass. Not the full feature — just enough to satisfy this specific test.

```
Rules:
- Write the MINIMUM code to make the test pass
- Do not add code for untested behavior
- Do not optimize yet
- Do not handle edge cases that don't have tests yet
- Run the test after every meaningful change
```

```bash
# Run after each change
[test_command] --filter "[test_name]"

# Keep going until: PASS
```

### Step 3: REFACTOR (Clean Up, Then Commit)

Once the test passes:
1. Clean up the implementation (remove duplication, improve naming, extract helpers)
2. Run the test again to make sure it still passes
3. Run the full task test suite (all G/W/T tests for this task)
4. Commit

```bash
# After refactor
[test_command] --filter "[test_name]"       # This test still passes
[test_command] --filter "[task_test_suite]"  # All task tests pass
[full_test_command]                          # No regressions

# Commit
git add [files]
git commit -m "[task_id]: [what was implemented] (RED-GREEN-REFACTOR)"
```

### Repeat for Each G/W/T Criterion

A task with 3 acceptance criteria gets 3 RED-GREEN-REFACTOR cycles:

```
Criterion 1: RED → GREEN → REFACTOR → commit
Criterion 2: RED → GREEN → REFACTOR → commit
Criterion 3: RED → GREEN → REFACTOR → commit
```

Each cycle is small (2-5 minutes). Each commit is atomic and tested.

---

## Integration with Codegen Context

The codegen-context skill already assembles per-task prompts. TDD Enforcement adds a section to that prompt:

```markdown
## TDD Protocol (MANDATORY)

For each acceptance criterion in this task, follow this exact cycle:

### Cycle 1: [First G/W/T criterion]
1. **RED:** Write a test for: "Given [X], When [Y], Then [Z]"
   - Test file: `[path]`
   - Follow test pattern in: `[reference_test_file]` (inlined below)
   - Run: `[test_command] --filter "[test_name]"`
   - Verify: test FAILS (if it passes, stop and investigate)

2. **GREEN:** Write minimal code to make the test pass
   - Implementation file: `[path]`
   - Follow pattern in: `[reference_impl]` (inlined in Section 4)
   - Run: `[test_command] --filter "[test_name]"`
   - Verify: test PASSES

3. **REFACTOR:** Clean up, then commit
   - Run full task tests: `[test_command] --filter "[task_suite]"`
   - Run full suite: `[full_test_command]`
   - Commit: `git commit -m "[task_id]: [criterion description]"`

### Cycle 2: [Second G/W/T criterion]
[Same structure]

### Cycle 3: [Third G/W/T criterion]
[Same structure]

**Iron Law:** If you write production code before a failing test exists for it, DELETE the production code and start with the test.
```

---

## Integration with QA Test Data Skill

Two modes of operation depending on what exists:

### Mode A: Pre-Written Tests Exist (QA skill already ran)
If the QA Test Data skill has already generated failing tests from G/W/T:
- The coding agent's RED step = **run the existing test, verify it fails**
- Skip writing the test — it already exists
- Proceed to GREEN (implement until the pre-written test passes)

### Mode B: Tests Don't Exist Yet (QA skill hasn't run or task-level tests needed)
If no pre-written tests exist:
- The coding agent's RED step = **write the test from the G/W/T in the task ticket**
- The test becomes the spec — it's the source of truth for what "done" means

The codegen-context skill detects which mode applies and adjusts the prompt.

---

## Violations and Enforcement

| Violation | Detection | Response |
|-----------|-----------|----------|
| Production code committed without corresponding test | `git diff` shows new code in `src/` but no new code in `tests/` | Block commit. Agent must write test first. |
| Test passes on first run (before implementation) | Test command returns PASS before any implementation code exists | Flag to agent: "Test passes without implementation — either feature exists or test is wrong. Investigate." |
| Test modified to match broken implementation | `git diff` shows changes to test assertions | Block. Tests are the spec. Fix the code, not the test. Exception: if the test has a genuine bug (wrong expected value from spec). |
| Multiple G/W/T criteria implemented in one cycle | Large diff with multiple behaviors added between test runs | Flag: "Break this into separate RED-GREEN-REFACTOR cycles, one per criterion." |

---

## Quality Gates

- [ ] Every task has at least 1 test per G/W/T acceptance criterion
- [ ] Every test was verified to FAIL before implementation (RED confirmed)
- [ ] Every test PASSES after implementation (GREEN confirmed)
- [ ] No test assertions were modified to match broken code
- [ ] Each G/W/T criterion has its own commit (atomic, bisectable)
- [ ] Full test suite passes after all cycles complete (no regressions)
- [ ] Test-to-code ratio is reasonable (not testing implementation details, testing behavior)

## Framework Hardening Addendum

- **Contract versioning:** TDD protocol input/output payloads include `contract_version` and strict compatibility checks.
- **Schema validation:** Validate task acceptance criteria against Build Brief task schema prior to RED/GREEN execution.
- **Budget controls:** Apply token pre-turn checks to any LLM-assisted assertion generation paths.
- **Structured errors:** Emit deterministic failures (`missing_test_command`, `invalid_gwt`, `phase_violation`) with stop reasons.

