# Skill: Gong Customer Evidence

> Searches customer call transcripts in Gong to validate PRD assumptions, surface unmet needs the PM may have missed, and ground feature decisions in actual customer language. Prevents building features nobody asked for and catches gaps in features customers desperately need.

---

## Why This Exists

PRDs are hypotheses. Customer calls are evidence. Without this skill:
- PMs build from internal assumptions, not customer voice
- Features ship without validation that customers actually want them
- Edge cases from customer conversations never make it into specs
- Success metrics have no baseline from customer conversations

This skill searches Gong transcripts for evidence that supports, contradicts, or expands the PRD — before a single line of code is written.

---

## Trigger

| When | What |
|------|------|
| PRD Agent Phase 1 (Feature Understanding) | Search for calls where customers discussed this problem space |
| PRD Agent Phase 2 (Success Metrics) | Find how customers describe success for this type of feature |
| PRD Agent Phase 3 (Scope) | Surface customer requests that are related but out of scope — validates exclusions |
| PRD Agent Phase 6 (Dependencies/Risks) | Find customer-reported pain points with existing related features |
| Eval Council (post-brief) | Validate that the Build Brief addresses customer-reported needs |

---

## Input

```json
{
  "feature_description": "string (what the feature does, in plain language)",
  "keywords": ["string (search terms derived from PRD)"],
  "customer_segment": "string (optional — filter by segment: enterprise, mid-market, SMB)",
  "date_range": {
    "from": "ISO date (default: 6 months ago)",
    "to": "ISO date (default: today)"
  },
  "mode": "validate_prd | discover_needs | find_language | risk_assessment"
}
```

---

## Behavior

### Mode: `validate_prd` — Does Customer Evidence Support This Feature?

Search Gong for conversations related to the PRD's core capabilities. For each PRD capability, look for:

1. **Direct requests:** Customers explicitly asking for this capability
2. **Workarounds:** Customers describing how they work around the lack of this capability
3. **Complaints:** Customers expressing frustration about related limitations
4. **Indifference:** The capability isn't mentioned at all (red flag — nobody asked for it)

**Output:**
```json
{
  "evidence_summary": {
    "total_calls_searched": 247,
    "calls_with_relevant_mentions": 34,
    "strongest_signal": "string (which PRD capability has the most customer evidence)",
    "weakest_signal": "string (which PRD capability has the least — potential deprioritize)"
  },
  "per_capability": [
    {
      "prd_capability": "Share deliverables via email",
      "evidence_strength": "strong | moderate | weak | none",
      "call_count": 18,
      "customer_quotes": [
        {
          "quote_summary": "string (paraphrased — no verbatim to respect privacy)",
          "call_date": "ISO date",
          "customer_segment": "enterprise",
          "sentiment": "positive_request | frustration | workaround | feature_comparison",
          "gong_call_id": "string"
        }
      ],
      "insight": "string (what the evidence tells us about this capability)"
    }
  ],
  "unaddressed_needs": [
    {
      "need": "string (customer need found in calls but NOT in PRD)",
      "evidence_strength": "strong | moderate",
      "call_count": 7,
      "recommendation": "add_to_prd | add_to_v2 | investigate"
    }
  ]
}
```

### Mode: `discover_needs` — What Are Customers Actually Asking For?

Broader search around the problem space. Not validating the PRD — discovering what the PRD might be missing.

- Search by problem keywords, not feature keywords
- Surface themes from call transcripts: what pain points come up repeatedly?
- Cluster by customer segment: do enterprise customers want something different from SMBs?
- Surface competitor mentions: are customers comparing to specific competitor features?

### Mode: `find_language` — How Do Customers Describe This?

Pull the exact language customers use to describe this problem and desired outcome. Feeds into:
- PRD user stories (use customer language, not PM language)
- Success metrics (what customers consider "success" vs what PM assumes)
- Marketing copy and onboarding text (use the words customers actually use)
- CTA labels and UI copy (if customers say "send to my team" instead of "share," the CTA should match)

### Mode: `risk_assessment` — What Could Go Wrong According to Customers?

Search for calls where customers described problems with similar features (in your product or competitors):
- "We tried [competitor's share feature] and it was confusing because..."
- "The problem with sharing is that people don't know what they're looking at..."
- "We stopped using it because the emails went to spam..."

These become failure modes in the Build Brief and test scenarios in the QA spec.

---

## Integration with PRD Agent

The PRD Agent calls this skill during discovery to ground the PRD in evidence:

```
PM: "We want users to share deliverables with colleagues"

PRD Agent → Gong Skill (validate_prd):
  Found 18 calls mentioning sharing/collaboration on AI outputs
  Strongest signal: "I wish I could send this analysis to my VP" (12 mentions)
  Unaddressed need: "I need to know if they actually looked at it" (7 mentions)
    → Recommendation: share analytics is out of scope but should be v2 priority

PRD Agent to PM:
  "Gong data confirms demand — 18 calls in 6 months mention sharing.
   Customers describe it as 'sending to my team' more than 'sharing.'
   One unaddressed need: 7 customers want read receipts / view tracking.
   That's out of scope per your PRD but I'd flag it for v2."
```

---

## MCP Server Contract

### Tool: `gong_search`

```json
{
  "name": "gong_search",
  "description": "Search Gong call transcripts for customer evidence related to a feature",
  "inputSchema": {
    "type": "object",
    "properties": {
      "keywords": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Search keywords (derived from PRD capabilities)"
      },
      "mode": {
        "type": "string",
        "enum": ["validate_prd", "discover_needs", "find_language", "risk_assessment"]
      },
      "customer_segment": {
        "type": "string",
        "description": "Optional segment filter"
      },
      "date_range_days": {
        "type": "integer",
        "default": 180,
        "description": "How far back to search (days)"
      }
    },
    "required": ["keywords", "mode"]
  }
}
```

---

## CLI Interface

```bash
# Validate PRD against Gong evidence
adlc-gong validate --prd ./prd.md --segment enterprise --days 180

# Discover unaddressed needs
adlc-gong discover --keywords "share,collaborate,send,team" --days 180

# Find customer language
adlc-gong language --keywords "share deliverable" --output ./customer-language.md

# Risk assessment from customer calls
adlc-gong risks --keywords "share,email,collaboration" --output ./customer-risks.md
```

---

## Privacy & Compliance

- **Never output verbatim call transcripts.** Always paraphrase.
- **Never include customer names, company names, or PII** in outputs unless the PM's org has explicit Gong permissions.
- **Outputs are summaries and aggregated insights**, not raw data.
- **Respect Gong's API access scoping** — only search calls the authenticated user has access to.

---

## Quality Gates

- [ ] Search covers at least 6 months of calls (unless date_range specified)
- [ ] Every PRD capability gets an evidence strength rating
- [ ] Unaddressed needs are surfaced with call count and recommendation
- [ ] No verbatim quotes — all paraphrased
- [ ] Customer language findings are specific enough to inform UI copy
- [ ] Risk assessment references actual customer-described failure scenarios

## Framework Hardening Addendum

- **Contract versioning:** Evidence query input/output must include `contract_version` and version compatibility checks.
- **Schema validation:** Validate evidence summaries before handoff to PRD generation to prevent malformed customer-signal payloads.
- **Budget controls:** Apply pre-turn token checks for any LLM summarization paths using `docs/specs/pre-turn-check.md`.
- **Structured stop reasons:** Emit typed reasons (`no_data`, `permission_denied`, `budget_exhausted`) for workflow routing.

