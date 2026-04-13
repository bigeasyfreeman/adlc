---
name: definition-of-done
description: "Applicability-aware Definition of Done checklist. Core checks apply to every task; overlay checks activate only when the applicability manifest says the surface exists. Binary verification — pass or fail. Triggers at Phase 4 completion and Phase 5 entry."
---

# Definition of Done

## Overview

Every task carries a DoD core baseline. Overlay checks are selected from the applicability manifest and only evaluated when the task actually touches that surface. A task is not complete until every active check is verified. Each check is binary (pass/fail) with a specified verification method. No judgment required — it passes or it doesn't.

## When to Use

- **Phase 4 completion:** Verify all DoD items after execution
- **Phase 5 entry:** DoD verification is the first step of the quality gate for active overlays
- **Manual:** Any time task completion needs verification

## Applicability Model

- Core baseline checks apply to every task.
- Overlay checks activate only when `applicability_manifest` marks the relevant surface as active.
- Any suppressed overlay must include a concrete `not_applicable` reason tied to task class or repo evidence.

### Overlay Activation Trigger Table

This table is the authoritative mapping of `change_surface` flags and task class to DoD overlay check IDs. It is consumed by the deterministic dod_overlays evaluator. Any change here must be mirrored in `tests/backtest/evaluators/dod_overlays.sh`.

| Overlay | Check IDs | Trigger Expression |
|---|---|---|
| Security | `5, 6, 7, 8, 9` | `new_attack_surface OR auth_change OR external_integration` |
| Observability | `10, 11, 12, 13, 14` | `runtime_path_change OR user_facing_operation` |
| Integration | `18, 19, 20` | `service_boundary_change OR external_integration OR api_change OR data_format_change` |
| Content | `21, 22` | `task_classification == "docs"` or human-facing output is in scope |

Overlay checks that are not activated by this table must be reported as `not_applicable` with a concrete reason in the manifest's `section_policy`.

## Mixed Acceptance Criteria Shapes

Acceptance criteria may arrive as strings or structured Given/When/Then objects.

Extraction rules:
- If an item is an object, read its `.then` field as the criterion text and preserve any `id` and `measurable_post_condition` in the verification record.
- If an item is a string, use the string directly.
- Do not mark a task done if the evaluation path drops an upstream `id` or `measurable_post_condition`.

## Core Baseline Checks

### Code Quality

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 1 | All linters pass | core | Automated: LDD gate | Any violation |
| 2 | All tests pass | core | Automated: TDD suite | Any failure |
| 3 | Code complexity within budget | core | Automated: CC < 15, SLOC < 50/fn | Exceeding ceiling |
| 4 | No code slop or stub patterns | core | Automated: anti-slop scanner | `TODO`, `FIXME`, `PLACEHOLDER`, `todo!()`, `unimplemented!()`, `panic!(\"not implemented\")`, `NotImplementedError`, `pass`, empty placeholder bodies, commented-out code, fake/mock placeholder logic in shipped code |

### Reuse & Patterns

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 15 | Reuse analysis confirmed | core | Automated + council | Reimplementation detected |
| 16 | Existing conventions followed | core | Council review | Convention violation |
| 17 | Antipattern checklist cleared | core | Automated + council | Known antipattern used |

## Security Overlay

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 5 | STRIDE threat model complete | overlay | Council: Security Auditor | Missing categories |
| 6 | STRIDE mitigations implemented | overlay | Council + automated | Unimplemented mitigations |
| 7 | OWASP Top 10 scan clean | overlay | Automated: SAST scan | High/Critical findings |
| 8 | No hardcoded secrets | overlay | Automated: pattern scan | Any match |
| 9 | Input validation at trust boundaries | overlay | Council review | Missing validation |

## Observability Overlay

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 10 | Error logging at failure points | overlay | Automated: AST scan | Missing error logs |
| 11 | Audit logging for state changes | overlay | Automated: AST scan | Missing audit logs |
| 12 | Operational logging for health | overlay | Automated: AST scan | Missing general logs |
| 13 | Log format matches convention | overlay | Automated: format check | Format mismatch |
| 14 | Correlation IDs propagate | overlay | Automated: pattern check | Missing correlation |

## Integration Overlay

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 18 | Integration wiring complete | overlay | Automated: registration check | Missing wiring, dead routes, unwired providers, unused flags/config, placeholder entry points |
| 19 | Scalability concerns documented | overlay | Council review | Undocumented |
| 20 | Degradation strategy defined | overlay | Council (if applicable) | Missing strategy |

## Content Overlay (human-facing output only)

| # | Check | Scope | Verification | Blocks On |
|---|-------|-------|-------------|-----------|
| 21 | Stop-slop gate passed | overlay | Automated: 5-dim scoring | Score < 35/50 |
| 22 | Voice/brand compliance | overlay | Automated + council | Voice mismatch |

## Domain Adaptation

**SWElfare:** Core baseline always applies. Security, observability, integration, and content overlays activate only when the applicability manifest says the surface exists.

**Ratatosk:** Core baseline applies to every task. Security overlay → trade execution STRIDE. Observability overlay → trade/risk logging. Integration overlay → exchange API wiring. Content overlay → briefing slop gate.

**Magnus:** Core baseline applies to every task. Security overlay → brand STRIDE. Observability overlay → content performance logging. Integration overlay → platform integration. Content overlay → always active for user-facing copy.

## Verification Schema

```json
{
  "task_id": "TASK-001",
  "task_classification": "build_validation",
  "applicability_manifest": {
    "security_overlay": { "status": "not_applicable", "reason": "No new attack surface or trust boundary changes." },
    "observability_overlay": { "status": "not_applicable", "reason": "No new runtime path or user-facing operation." },
    "integration_overlay": { "status": "active", "reason": "Build wiring changed and must be verified." },
    "content_overlay": { "status": "not_applicable", "reason": "No human-facing output changed." }
  },
  "active_checks": ["1", "2", "3", "4", "15", "16", "17", "18"],
  "dod_checks": {
    "ldd_pass": { "status": true, "evidence": "ruff: 0 violations, mypy: 0 errors" },
    "tdd_pass": { "status": true, "evidence": "42 passed, 0 failed", "coverage": 87 },
    "complexity_ok": { "status": true, "evidence": "max CC: 8, max SLOC: 35" },
    "no_code_slop": { "status": true, "evidence": "0 violations: no TODO/FIXME/PLACEHOLDER, no stub bodies, no NotImplementedError, no commented-out code" },
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

- DoD verification runs automatically at Phase 4 completion for the core baseline and any active overlays
- Any failed active check blocks pipeline progression to Phase 6
- Failed checks produce specific remediation guidance
- No partial passes — ALL active checks must be green
- Scaffolding artifacts are never considered done. Any remaining stub, placeholder, or partial wiring fails DoD.
- Mixed acceptance-criteria handlers that lose an upstream `id` or `measurable_post_condition` fail DoD verification.
