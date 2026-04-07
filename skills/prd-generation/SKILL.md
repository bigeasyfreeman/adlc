# Skill: PRD Quality Evaluator

> Validates a PRD against the standard template before it's handed to engineering. Catches missing fields, vague specs, orphan screens, undefined interactions, and TBDs without owners. Runs automatically before PRD finalization — the last gate before the ADLC pipeline consumes it.

---

## Trigger

Runs automatically when the PRD Agent completes Phase 7 (Review & Finalize). Also runnable on-demand against any PRD document.

---

## Input

```json
{
  "prd_content": "string (full PRD markdown)",
  "strict_mode": true
}
```

---

## Output

```json
{
  "verdict": "PASS | PASS_WITH_WARNINGS | FAIL",
  "score": {
    "total": "0-100",
    "by_section": {
      "goals_metrics": "0-100",
      "out_of_scope": "0-100",
      "personas": "0-100",
      "screens": "0-100",
      "dependencies": "0-100"
    }
  },
  "findings": [
    {
      "severity": "critical | major | minor",
      "section": "string",
      "finding": "string",
      "recommendation": "string",
      "blocks_handoff": true
    }
  ],
  "engineering_readiness": {
    "screens_ready_for_eng": ["Screen 2", "Screen 3"],
    "screens_not_ready": ["Screen 1: no field-detail table", "Screen 5: OPEN status"],
    "phase_1_candidates": ["screens with IN PROGRESS or FULLY DESIGNED status"],
    "missing_for_codegen": ["items the ADLC system needs but PRD doesn't provide"]
  },
  "summary": "string"
}
```

---

## Evaluation Criteria

### 1. Goals & Metrics (20 points)

| Check | Points | Severity if Missing |
|-------|--------|-------------------|
| ≥ 2 business goals stated | 5 | major |
| ≥ 3 success metrics defined | 5 | critical |
| Every metric has a definition column | 3 | major |
| Every metric has a target (or TBD with owner + deadline) | 5 | critical |
| At least 1 metric measures adoption | 1 | minor |
| At least 1 metric measures value/engagement | 1 | minor |

**Common failures:**
- "TBD" without owner → "Metric 'Share Rate' has target TBD but no owner. Who sets this target and by when?"
- Vanity metrics only → "All metrics measure volume (opens, clicks). Add a quality metric: what tells you users found this valuable?"

### 2. Out of Scope (15 points)

| Check | Points | Severity if Missing |
|-------|--------|-------------------|
| ≥ 3 out-of-scope items | 5 | major |
| Each item has rationale (why it's out) | 5 | major |
| Each item notes where it's covered (other PRD, v2, deliberate exclusion) | 3 | minor |
| No ambiguous items ("maybe in v1") | 2 | critical |

**Common failures:**
- Empty out-of-scope → "Nothing is out of scope? That usually means scope isn't defined. What are you NOT building?"
- Vague items → "'Advanced features' is not specific enough. Which advanced features? An engineer will ask."

### 3. Personas (15 points)

| Check | Points | Severity if Missing |
|-------|--------|-------------------|
| ≥ 2 distinct personas | 4 | major |
| Each persona has a name and description | 3 | minor |
| Each persona has ≥ 2 user stories (As/I want/So that) | 5 | critical |
| User stories are specific, not generic | 3 | major |

**Common failures:**
- Generic stories → "'As a user, I want to use the feature' is not a user story. What specific capability? What specific outcome?"
- Missing personas → "You describe a sender and a recipient flow, but only define one persona. The recipient is a separate persona with different needs."

### 4. Screen Specifications (35 points — most important section)

| Check | Points | Severity if Missing |
|-------|--------|-------------------|
| Every screen has a name | 2 | critical |
| Every screen has a status badge | 3 | critical |
| Every screen has a trigger (what causes it to appear) | 3 | major |
| Every screen has a 1-2 sentence description | 2 | minor |
| Every screen has a field-detail table | 8 | critical |
| Field-detail table has ≥ 5 fields | 3 | major |
| Every CTA specifies what it opens/triggers | 5 | critical |
| Sub-variants are specified for multi-state screens | 3 | major |
| Design reference (Figma link/frame name) | 2 | minor |
| No orphan screens (every screen reachable from a flow) | 2 | major |
| Error states / empty states addressed | 2 | minor |

**Common failures:**
- Missing field-detail table → "Screen 4 describes 'a transactional email' but doesn't specify the fields (sender name format, subject line, body structure, CTA text). Engineers will guess."
- Undefined CTA → "'Share' button — what does it open? A modal? A new page? A browser native share sheet?"
- No error states → "What happens if the email fails to send? What does the user see?"
- Orphan screen → "Screen 5 (Replay) is described but no other screen links to it. How does the user get here? Only via email?"

### 5. Dependencies & Risks (15 points)

| Check | Points | Severity if Missing |
|-------|--------|-------------------|
| ≥ 1 dependency listed | 3 | major |
| Each dependency names what's needed | 3 | critical |
| Each dependency names which screens it affects | 3 | major |
| ≥ 1 risk identified | 3 | major |
| Risks have likelihood and impact | 3 | minor |

**Common failures:**
- Missing dependency → "Screen 4 requires sending emails, but no email infrastructure is listed as a dependency."
- Vague dependency → "'Backend support needed' is not specific. What API? What data? What service?"

---

## Engineering Readiness Assessment

Beyond quality, this evaluator assesses whether the PRD is ready for the ADLC pipeline specifically. It checks what the Build Brief Agent, Codebase Research, QA Skill, and Codegen Assembly need:

| ADLC Consumer | What It Needs from PRD | How Evaluator Checks |
|--------------|----------------------|---------------------|
| Build Brief Agent | Capabilities, out of scope, personas, screen specs | Sections 1-5 present and filled |
| Codebase Research | Dependencies, integration points | Section 5 has specific dependencies |
| QA Skill | Testable behaviors per screen | Field-detail tables have specific values (not "TBD") |
| Codegen Assembly | Precise field specs | Every CTA, input, and display element has defined behavior |
| Phase planning | Screen status badges | Every screen has a status badge |

**Output: `engineering_readiness`** — lists which screens are ready for engineering (status IN PROGRESS or FULLY DESIGNED + complete field-detail table) and which are not. This directly feeds the Build Brief's Phase 1/2/3 scoping.

---

## MCP Server Contract

### Tool: `evaluate_prd`

```json
{
  "name": "evaluate_prd",
  "description": "Evaluate a PRD against the standard template for completeness, specificity, and engineering readiness",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prd_content": {
        "type": "string",
        "description": "Full PRD markdown"
      },
      "strict_mode": {
        "type": "boolean",
        "default": true,
        "description": "If true, TBDs without owners are critical findings"
      }
    },
    "required": ["prd_content"]
  }
}
```

---

## CLI Interface

```bash
# Evaluate a PRD
adlc-prd evaluate --input ./prd.md --output ./eval-report.md

# Evaluate in strict mode (blocks on any TBD without owner)
adlc-prd evaluate --input ./prd.md --strict

# Check engineering readiness only
adlc-prd ready --input ./prd.md
```

---

## Quality Gates

- [ ] Every evaluation cites specific sections and fields, not generic advice
- [ ] Score breakdown is per-section, not just a total
- [ ] Engineering readiness lists specific screens with specific missing items
- [ ] Findings include actionable recommendations, not just "this is missing"
- [ ] Critical findings block handoff to engineering
- [ ] The evaluator catches every pattern the ADLC Build Brief Agent would fail on

## Framework Hardening Addendum

- **Contract versioning:** PRD evaluation input/output includes `contract_version` and follows `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate PRD payloads against `docs/schemas/prd-template.schema.json` before scoring readiness.
- **Structured errors:** Return typed diagnostics for missing sections or malformed tables; do not silently skip required fields.
- **Workflow metadata:** Emit `session_id`, `brief_id`, `phase`, and `stop_reason` for downstream orchestration.

