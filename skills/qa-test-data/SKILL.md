# Skill: QA Test Data Generation

> Generates deterministic test scenarios, seed data, and fixture files from Build Brief task breakdowns. Produces data that autonomous testing agents can replay without human intervention.

---

## Trigger

Activated after JIRA tickets are created from the Build Brief. Consumes Section 1 (Given/When/Then acceptance criteria) and Section 8 (Task Breakdown with per-task G/W/T) from the brief.

## Input Contract

```json
{
  "build_brief_id": "string",
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "given": "string (precondition)",
      "when": "string (action)",
      "then": "string (expected outcome)"
    }
  ],
  "tasks": [
    {
      "task_id": "string",
      "task_description": "string",
      "acceptance_criteria_gwt": [
        {
          "given": "string",
          "when": "string",
          "then": "string"
        }
      ],
      "architecture_pattern": "string",
      "reference_implementation": "string (file path)",
      "language": "typescript | python | scala | go",
      "test_directory": "string"
    }
  ],
  "repo_url": "string",
  "test_framework": "jest | vitest | pytest | scalatest | go_test"
}
```

## Output Contract

```json
{
  "test_suites": [
    {
      "task_id": "string",
      "fixture_file": "path/to/fixtures.json",
      "test_file": "path/to/test_file",
      "scenarios": [
        {
          "name": "string",
          "type": "happy_path | error_case | edge_case | regression",
          "input": {},
          "expected_output": {},
          "deterministic": true,
          "setup": "string (seed script or fixture load)",
          "teardown": "string"
        }
      ]
    }
  ],
  "seed_script": "path/to/seed.sql or seed.ts",
  "summary": "string"
}
```

## Behavior

### 1. Parse Given/When/Then into Test Scenarios

The Build Brief provides acceptance criteria in two places:
- **Section 1 (Functional Spec):** Feature-level G/W/T criteria (e.g., "Given a new user, When they create a widget, Then...")
- **Section 8 (Task Breakdown):** Task-level G/W/T criteria (e.g., "Given a POST to /api/v1/widgets with empty name, When processed, Then 400")

Each G/W/T triple maps directly to a test case:
- **Given** → test setup / precondition (seed data, mock state, fixture load)
- **When** → test action (API call, function invocation, event trigger)
- **Then** → test assertion (status code, state change, side effect verification)

```
// G/W/T → Test mapping example
// Given: a user with an existing account
// When: they create a widget with a duplicate name
// Then: the system returns 409 with the existing widget's ID

it('should return 409 when creating widget with duplicate name', async () => {
  // Given
  const user = await createTestUser();
  const existing = await createTestWidget({ name: 'My Widget', userId: user.id });

  // When
  const response = await request(app)
    .post('/api/v1/widgets')
    .set('Authorization', `Bearer ${user.token}`)
    .send({ name: 'My Widget' });

  // Then
  expect(response.status).toBe(409);
  expect(response.body.existingId).toBe(existing.id);
});
```

### 2. Generate Deterministic Scenarios

For each task, produce:

**Happy Path (always 1)**
- The primary success scenario described in the QA data story
- Uses realistic but deterministic seed data (no randomness, no `Date.now()`, no UUIDs unless seeded)
- Must be idempotent -- running twice produces the same result

**Error Cases (minimum 3 per task)**
- Invalid input (malformed, missing required fields, wrong types)
- Authorization failure (wrong role, expired token, missing permissions)
- Conflict / duplicate (if applicable to the domain)
- External dependency failure (timeout, 5xx, malformed response)

**Edge Cases (from QA data story)**
- Each edge case listed in the brief becomes a named scenario
- Boundary values (empty strings, zero, max int, null vs undefined)
- Concurrency scenarios if the task involves shared state

**Regression Guards**
- If the brief identifies a failure mode for this task, generate a test that would catch that failure
- Name it explicitly: `test_regression_FM001_description`

### 3. Generate Fixtures

Produce fixture files that contain:
- Seed data for the database (SQL, JSON, or language-specific fixtures)
- Mock responses for external services (deterministic, versioned)
- Factory functions for creating test entities with sensible defaults

**Fixture rules:**
- All IDs are deterministic (e.g., `test-user-001`, `test-widget-abc`)
- All timestamps are fixed (e.g., `2025-01-01T00:00:00Z`)
- All external service responses are recorded/mocked, never live
- Fixtures reference the architecture pattern -- if ports-and-adapters, fixtures mock at the port boundary, not the adapter

### 4. Generate Test Files

Produce test files that follow the repo's existing test conventions:
- Match the directory structure found in codebase research
- Use the test framework already in use
- Follow the naming convention already in use
- Import from existing test helpers/utilities found in the repo

### 5. Generate Seed Script

Produce a single seed script that:
- Sets up the database to a known state for all test scenarios
- Is idempotent (can run multiple times safely)
- Can be run in CI or locally
- Has a corresponding teardown/reset

## MCP Server Contract

### Tool: `generate_qa_test_data`

```json
{
  "name": "generate_qa_test_data",
  "description": "Generate deterministic test scenarios, fixtures, and seed data from Build Brief QA data stories",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief_section": {
        "type": "string",
        "description": "The Task Breakdown section (Section 8) of the Build Brief as markdown"
      },
      "repo_path": {
        "type": "string",
        "description": "Path to the repository root"
      },
      "output_directory": {
        "type": "string",
        "description": "Where to write generated test files"
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
  "description": "Run generated tests twice and verify identical results to confirm determinism",
  "inputSchema": {
    "type": "object",
    "properties": {
      "test_suite_path": {
        "type": "string",
        "description": "Path to the generated test suite"
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

## CLI Interface

```bash
# Generate test data from a build brief
adlc-qa generate --brief ./build-brief.md --repo ./my-repo --output ./my-repo/tests/generated

# Validate determinism of generated tests
adlc-qa validate --suite ./my-repo/tests/generated --runs 3

# Generate only fixtures (no test files)
adlc-qa fixtures --brief ./build-brief.md --repo ./my-repo --output ./my-repo/tests/fixtures
```

## Codebase Research (performed by skill)

Before generating, the skill searches the target repo:

```bash
# Find existing test conventions
find . -path "*/__tests__/*" -o -path "*/test/*" -name "*.test.*" | head -20

# Find existing fixtures
find . -name "*.fixture.*" -o -name "*.factory.*" -o -name "*.seed.*"

# Find test helpers
find . -path "*/test/helpers/*" -o -path "*/test/utils/*" -o -path "*/__tests__/helpers/*"

# Find test framework config
find . -name "jest.config.*" -o -name "pytest.ini" -o -name "conftest.py" -o -name "build.sbt" | head -5
```

## Quality Gates

- [ ] Every acceptance criterion has at least one test scenario
- [ ] Every failure mode from the brief has a regression test
- [ ] All fixtures use deterministic data (no randomness)
- [ ] Tests pass on first run after seed script
- [ ] Tests pass on second run without re-seeding (idempotent)
- [ ] Test files follow existing repo conventions
- [ ] No external service calls in tests (all mocked)

## Framework Hardening Addendum

- **Contract versioning:** Generated fixtures and scenario payloads must include `contract_version` metadata.
- **Schema validation:** Validate incoming acceptance criteria and task metadata against Build Brief task schema prior to fixture generation.
- **Idempotency:** Regeneration with same idempotency key must produce deterministic outputs without duplicate artifacts.
- **Structured errors:** Return deterministic failure reasons (`invalid_acceptance_criteria`, `schema_mismatch`, `missing_dependency`).

