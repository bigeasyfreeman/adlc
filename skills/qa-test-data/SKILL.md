# Skill: QA Test Data Generation

> Generates deterministic verification artifacts from task definitions. It produces behavioral tests when the task warrants tests, and produces command-verifier metadata when the task is maintenance.

---

## Trigger

Activated after the Build Brief and task classification are available. Consumes `task_classification`, `verification_spec`, and task-level acceptance criteria.

---

## Input Contract

```json
{
  "build_brief_id": "string",
  "task_classification": "feature | bugfix | build_validation | lint_cleanup",
  "verification_spec": {
    "primary_verifier": {
      "type": "test | reproducer | command",
      "command": "string",
      "target": "string",
      "expected_pre_change": "fail",
      "expected_post_change": "pass"
    },
    "secondary_verifiers": [],
    "must_fail_before_change": true,
    "must_be_deterministic": true,
    "scope_note": "string"
  },
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "given": "string",
      "when": "string",
      "then": "string"
    }
  ],
  "tasks": [
    {
      "task_id": "string",
      "objective": "string",
      "acceptance_criteria": [],
      "reference_impl": "string",
      "language": "typescript | python | scala | go",
      "test_directory": "string"
    }
  ],
  "repo_path": "string",
  "test_framework": "jest | vitest | pytest | scalatest | go_test"
}
```

---

## Output Contract

```json
{
  "task_id": "string",
  "task_classification": "feature | bugfix | build_validation | lint_cleanup",
  "verification_mode": "behavioral_tests | reproducer | command_check",
  "verification_spec": {},
  "test_suites": [
    {
      "task_id": "string",
      "fixture_file": "path/to/fixtures.json",
      "test_file": "path/to/test_file",
      "scenarios": []
    }
  ],
  "command_checks": [
    {
      "name": "string",
      "command": "string",
      "expected_pre_change": "fail",
      "expected_post_change": "pass",
      "scope_note": "string"
    }
  ],
  "seed_script": "path/to/seed.sql or seed.ts",
  "summary": "string"
}
```

`test_suites` is only populated for `feature` and `bugfix` tasks. `command_checks` is mandatory for `build_validation` and `lint_cleanup`. The output should never invent behavioral suites for maintenance work.

---

## Behavior

### 1. Classify The Verifier First

The task class controls what gets generated:

- `feature`: generate behavioral tests that define success
- `bugfix`: generate a minimal reproducer and a regression guard
- `build_validation`: generate the exact failing build or test command
- `lint_cleanup`: generate the exact failing lint, fmt, or static-analysis command

If the task class does not justify behavioral tests, do not create them.

### 2. Generate Only The Right Artifacts

**Feature tasks**
- Produce test scenarios from acceptance criteria
- Include happy path, edge cases, and failure cases that the task actually touches
- Generate deterministic fixtures and seed data only as needed by the tests

**Bugfix tasks**
- Produce the smallest deterministic reproducer for the observed failure
- Add a regression guard that fails before the fix and passes after it
- Do not broaden into unrelated behaviors

**Build validation tasks**
- Produce command-verifier metadata, not fabricated G/W/T tests
- Capture the exact command that currently fails
- Capture the minimal scope note that explains why the command is sufficient

**Lint cleanup tasks**
- Produce command-verifier metadata, not runtime tests
- Capture the exact lint/fmt/static-analysis command that currently fails
- Keep the scope limited to the hygiene issue

### 3. Make Verifiers Deterministic

Every generated artifact must be replayable:
- no random IDs
- no `Date.now()`
- no live external service calls
- no hidden state in fixtures
- no test order dependence

If a test requires external setup, seed it explicitly and idempotently.

### 4. Generate Fixtures When They Add Signal

Fixtures are required only when the verifier needs them.

Fixture rules:
- deterministic IDs
- fixed timestamps
- mocked external responses
- consistent factory defaults
- architecture-aware boundary mocking

### 5. Preserve The Verifier Contract

Every generated verifier must satisfy:
- task-class match
- falsifiable before the change
- closest useful signal to the defect
- deterministic and low-noise
- minimal sufficient coverage

If the verifier would pass for the wrong reason, it is too weak.

---

## MCP Server Contract

### Tool: `generate_qa_test_data`

```json
{
  "name": "generate_qa_test_data",
  "description": "Generate deterministic behavioral tests or command-verifier metadata from task definitions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief_section": {
        "type": "string",
        "description": "The task breakdown section from the Build Brief as markdown"
      },
      "repo_path": {
        "type": "string",
        "description": "Path to the repository root"
      },
      "output_directory": {
        "type": "string",
        "description": "Where to write generated artifacts"
      }
    },
    "required": ["build_brief_section", "repo_path"]
  }
}
```

### Tool: `validate_test_determinism`

```json
{
  "name": "validate_test_determinism",
  "description": "Run generated artifacts twice and verify identical results to confirm determinism",
  "inputSchema": {
    "type": "object",
    "properties": {
      "test_suite_path": {
        "type": "string",
        "description": "Path to the generated test suite or verifier bundle"
      },
      "runs": {
        "type": "integer",
        "default": 2,
        "description": "Number of times to run for determinism check"
      }
    },
    "required": ["test_suite_path"]
  }
}
```

---

## CLI Interface

```bash
# Generate verification artifacts from a build brief
adlc-qa generate --brief ./build-brief.md --repo ./my-repo --output ./my-repo/tests/generated

# Validate determinism of generated verification artifacts
adlc-qa validate --suite ./my-repo/tests/generated --runs 3

# Generate only fixtures when the task class warrants behavioral tests
adlc-qa fixtures --brief ./build-brief.md --repo ./my-repo --output ./my-repo/tests/fixtures
```

---

## Codebase Research

Before generating, the skill searches the target repo for existing conventions:

```bash
find . -path "*/__tests__/*" -o -path "*/test/*" -name "*.test.*" | head -20
find . -name "*.fixture.*" -o -name "*.factory.*" -o -name "*.seed.*"
find . -path "*/test/helpers/*" -o -path "*/test/utils/*" -o -path "*/__tests__/helpers/*"
find . -name "jest.config.*" -o -name "pytest.ini" -o -name "conftest.py" -o -name "build.sbt" | head -5
```

Use that research only when the task class needs test artifacts. Do not generate behavioral suites for build-validation or lint-cleanup tasks.

---

## Quality Gates

- [ ] The task class matches the artifact type
- [ ] Behavioral tests are generated only for `feature` and `bugfix`
- [ ] Maintenance tasks receive command-verifier metadata instead of fake tests
- [ ] Every generated verifier is deterministic
- [ ] Every generated verifier is falsifiable before the change
- [ ] Fixtures exist only when they increase signal
- [ ] No external service calls appear in generated tests

## Framework Hardening Addendum

- **Contract versioning:** Generated artifacts include `contract_version`
- **Schema validation:** Validate task metadata and verification spec before generation
- **Idempotency:** Regeneration with the same key produces the same artifacts
- **Structured errors:** Return deterministic failures such as `invalid_task_classification`, `invalid_acceptance_criteria`, `schema_mismatch`, and `missing_verifier_target`
