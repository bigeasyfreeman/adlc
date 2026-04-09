---
name: definition-of-done
description: "Universal Definition of Done checklist. Every task must satisfy all items before pipeline marks it complete. Binary verification — pass or fail. Triggers at Phase 4 completion and Phase 5 entry."
---

# Definition of Done

## Overview

Every task carries a DoD checklist. A task is not complete until every item is verified. Each check is binary (pass/fail) with a specified verification method. No judgment required — it passes or it doesn't.

## When to Use

- **Phase 4 completion:** Verify all DoD items after execution
- **Phase 5 entry:** DoD verification is the first step of the quality gate
- **Manual:** Any time task completion needs verification

## The Universal DoD Checklist

### Code Quality

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 1 | All linters pass | Automated: LDD gate | Any violation |
| 2 | All tests pass | Automated: TDD suite | Any failure |
| 3 | Code complexity within budget | Automated: CC < 15, SLOC < 50/fn | Exceeding ceiling |
| 4 | No code slop | Automated: anti-slop scanner | Placeholders, TODOs, god functions, duplicates, hardcoded values |

### Security

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 5 | STRIDE threat model complete | Council: Security Auditor | Missing categories |
| 6 | STRIDE mitigations implemented | Council + automated | Unimplemented mitigations |
| 7 | OWASP Top 10 scan clean | Automated: SAST scan | High/Critical findings |
| 8 | No hardcoded secrets | Automated: pattern scan | Any match |
| 9 | Input validation at trust boundaries | Council review | Missing validation |

### Observability

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 10 | Error logging at failure points | Automated: AST scan | Missing error logs |
| 11 | Audit logging for state changes | Automated: AST scan | Missing audit logs |
| 12 | Operational logging for health | Automated: AST scan | Missing general logs |
| 13 | Log format matches convention | Automated: format check | Format mismatch |
| 14 | Correlation IDs propagate | Automated: pattern check | Missing correlation |

### Reuse & Patterns

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 15 | Reuse analysis confirmed | Automated + council | Reimplementation detected |
| 16 | Existing conventions followed | Council review | Convention violation |
| 17 | Antipattern checklist cleared | Automated + council | Known antipattern used |

### Integration

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 18 | Integration wiring complete | Automated: registration check | Missing wiring |
| 19 | Scalability concerns documented | Council review | Undocumented |
| 20 | Degradation strategy defined | Council (if applicable) | Missing strategy |

### Content (human-facing output only)

| # | Check | Verification | Blocks On |
|---|-------|-------------|-----------|
| 21 | Stop-slop gate passed | Automated: 5-dim scoring | Score < 35/50 |
| 22 | Voice/brand compliance | Automated + council | Voice mismatch |

## Domain Adaptation

**SWElfare:** All 22 checks apply. Full DoD on every task.

**Ratatosk:** Checks 1-4 → parameter validation. 5-9 → trade execution STRIDE. 10-14 → trade/risk logging. 15-17 → strategy pattern reuse. 18-20 → exchange API wiring. 21-22 → briefing slop gate.

**Magnus:** Checks 1-4 → format validation. 5-9 → brand STRIDE. 10-14 → content performance logging. 15-17 → voice/format reuse. 18-20 → platform integration. 21-22 → ALWAYS applies (primary product).

## Verification Schema

```json
{
  "task_id": "TASK-001",
  "dod_checks": {
    "ldd_pass": { "status": true, "evidence": "ruff: 0 violations, mypy: 0 errors" },
    "tdd_pass": { "status": true, "evidence": "42 passed, 0 failed", "coverage": 87 },
    "complexity_ok": { "status": true, "evidence": "max CC: 8, max SLOC: 35" },
    "no_code_slop": { "status": true, "evidence": "0 violations" },
    "stride_complete": { "status": true, "threats": 6, "mitigations": 4 },
    "stride_implemented": { "status": true, "evidence": "4/4 mitigations present" },
    "owasp_clean": { "status": true, "findings": 0 },
    "no_secrets": { "status": true, "evidence": "0 matches" },
    "input_validation": { "status": true, "evidence": "council approved" },
    "error_logging": { "status": true, "error_points": 3 },
    "audit_logging": { "status": true, "audit_points": 2 },
    "general_logging": { "status": true, "general_points": 5 },
    "log_format": { "status": true, "evidence": "structured JSON" },
    "correlation_ids": { "status": true, "evidence": "propagated" },
    "reuse_confirmed": { "status": true, "reimplementations": 0 },
    "conventions_followed": { "status": true, "evidence": "council approved" },
    "antipatterns_cleared": { "status": true, "violations": 0 },
    "wiring_complete": { "status": true, "upstream": 2, "downstream": 1 },
    "scalability_documented": { "status": true },
    "degradation_defined": { "status": true },
    "slop_gate": { "status": true, "score": 42 },
    "voice_compliance": { "status": true }
  },
  "all_passed": true,
  "timestamp": "2026-04-05T12:00:00Z"
}
```

## Enforcement

- DoD verification runs automatically at Phase 4 completion
- Any failed check blocks pipeline progression to Phase 6
- Failed checks produce specific remediation guidance
- No partial passes — ALL checks must be green
