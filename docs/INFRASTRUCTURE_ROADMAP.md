# ADLC Infrastructure Roadmap

> Prioritized implementation plan for closing infrastructure gaps identified in the Infrastructure Primitives Audit and Backwards/Forwards Compatibility Analysis.

**Created:** 2026-04-06
**Source:** Infrastructure Primitives Audit + Compatibility Analysis

---

## Roadmap Overview

```
Phase 1 (Sprint)     Phase 2 (Sprint)         Phase 3 (Sprint)         Phase 4 (Ongoing)
─────────────────    ─────────────────────    ─────────────────────    ─────────────────
Workflow State &     Token Budget &           Contract Schemas &       Week One Gaps &
Idempotency          Circuit Breakers         Boundary Validation      Maintenance
                     +                        +
                     Verification Harness     Skill Manifest &
                                              Deprecation Protocol
```

---

## Phase 1: Workflow State & Idempotency (Sprint — 2 weeks)

**Why first:** Without this, the autonomous pipeline is fragile. Any failure requires manual cleanup across JIRA, Confluence, Git, and Grafana, then a full restart. This is the gap between demo and production.

| Task ID | Task | Document | Status |
|---------|------|----------|--------|
| P1-WF-001 | Define workflow state schema | `docs/schemas/workflow-state.schema.json` | ☐ |
| P1-WF-002 | Define idempotency key generation spec | `docs/specs/idempotency-keys.md` | ☐ |
| P1-WF-003 | Define checkpoint spec for each pipeline phase | `docs/specs/workflow-checkpoints.md` | ☐ |
| P1-WF-004 | Define partial failure recovery spec | `docs/specs/workflow-checkpoints.md` | ☐ |
| P1-WF-005 | Add workflow state requirements to Build Brief Agent | `agents/ADLC-BUILD-BRIEF-AGENT.md` | ☐ |
| P1-WF-006 | Add idempotency to each side-effecting skill (7 skills) | `skills/*/SKILL.md` | ☐ |
| P1-WF-007 | Add workflow state to Eval Council loop | `skills/eval-council/SKILL.md` | ☐ |
| P1-WF-008 | Update README with workflow state architecture | `README.md` | ☐ |

**Acceptance:** Pipeline can be killed at any step and resumed without duplicate artifacts.

---

## Phase 2: Token Budget & Verification Harness (Sprint — 2 weeks)

**Why second:** Token budget prevents unbounded cost. Verification harness prevents guardrail regressions.

| Task ID | Task | Document | Status |
|---------|------|----------|--------|
| P2-TB-001 | Define token budget schema | `docs/schemas/token-budget.schema.json` | ☐ |
| P2-TB-002 | Define per-phase and per-skill budgets | `docs/specs/token-budgets.md` | ☐ |
| P2-TB-003 | Define pre-turn budget check spec | `docs/specs/pre-turn-check.md` | ☐ |
| P2-TB-004 | Define Eval Council circuit breaker spec | `docs/specs/pre-turn-check.md` | ☐ |
| P2-TB-005 | Add token budget to Build Brief Agent | `agents/ADLC-BUILD-BRIEF-AGENT.md` | ☐ |
| P2-TB-006 | Add token budget to Eval Council | `skills/eval-council/SKILL.md` | ☐ |
| P2-TB-007 | Add token budget to Codegen Context | `skills/codegen-context/SKILL.md` | ☐ |
| P2-TB-008 | Define cost reporting format | `docs/specs/cost-reporting.md` | ☐ |
| P3-VH-001 | Define verification harness architecture | `docs/specs/verification-harness.md` | ☐ |
| P3-VH-002 | Define scope immutability test specs | `docs/tests/scope-immutability-tests.md` | ☐ |
| P3-VH-003 | Define idempotency test specs | `docs/tests/idempotency-tests.md` | ☐ |
| P3-VH-004 | Define gate enforcement test specs | `docs/tests/gate-enforcement-tests.md` | ☐ |
| P3-VH-005 | Define budget enforcement test specs | `docs/tests/budget-enforcement-tests.md` | ☐ |
| P3-VH-006 | Define phase boundary enforcement test specs | `docs/tests/phase-boundary-tests.md` | ☐ |
| P3-VH-007 | Define crash recovery test specs | `docs/tests/crash-recovery-tests.md` | ☐ |
| P3-VH-008 | Add verification harness to README | `README.md` | ☐ |

**Acceptance:** Token budget prevents runaway costs. Invariant tests catch guardrail regressions on prompt/model changes.

---

## Phase 3: Contract Schemas & Compatibility (Sprint — 2 weeks)

**Why third:** Every skill addition or modification risks silent pipeline breakage without versioned contracts.

| Task ID | Task | Document | Status |
|---------|------|----------|--------|
| COMPAT-001 | Define PRD template contract schema | `docs/schemas/prd-template.schema.json` | ☐ |
| COMPAT-002 | Define repo map contract schema | `docs/schemas/repo-map.schema.json` | ☐ |
| COMPAT-003 | Define Build Brief contract schema | `docs/schemas/build-brief.schema.json` | ☐ |
| COMPAT-004 | Define Eval Council verdict schema | `docs/schemas/eval-council-verdict.schema.json` | ☐ |
| COMPAT-005 | Define security assessment contract schema | `docs/schemas/security-assessment.schema.json` | ☐ |
| COMPAT-006 | Define skill contract versioning standard | `docs/specs/skill-contract-versioning.md` | ☐ |
| COMPAT-007 | Add validation to Build Brief Phase 0 | `agents/ADLC-BUILD-BRIEF-AGENT.md` | ☐ |
| COMPAT-008 | Add validation to Codebase Research output | `skills/codebase-research/SKILL.md` | ☐ |
| COMPAT-009 | Add validation to Build Brief output | `agents/ADLC-BUILD-BRIEF-AGENT.md` | ☐ |
| COMPAT-010 | Add validation to Eval Council I/O | `skills/eval-council/SKILL.md` | ☐ |
| COMPAT-011 | Add validation to downstream skills (5 skills) | `skills/*/SKILL.md` | ☐ |
| COMPAT-012 | Define deprecation protocol | `docs/specs/deprecation-protocol.md` | ☐ |
| COMPAT-013 | Define migration guide template | `docs/templates/migration-guide-template.md` | ☐ |
| COMPAT-014 | Create skill manifest | `skills/manifest.json` | ☐ |
| COMPAT-015 | Update contributing guide with compatibility checklist | `README.md` | ☐ |
| COMPAT-016 | Define contract chain smoke test specs | `docs/tests/contract-chain-tests.md` | ☐ |
| COMPAT-017 | Define version compatibility matrix | `docs/specs/version-compatibility-matrix.md` | ☐ |

**Acceptance:** Every contract surface has a versioned schema. Boundary validation catches missing/malformed data. New skill additions follow a structured compatibility checklist.

---

## Phase 4: Remaining Day One + Week One Gaps (Ongoing)

| Task ID | Task | Document | Status |
|---------|------|----------|--------|
| P4-TR-001 | Define tool registry schema | `docs/schemas/tool-registry.schema.json` | ☐ |
| P4-TR-002 | Create tool registry manifest | `skills/registry.json` | ☐ |
| P4-TR-003 | Add runtime filtering to agent/skill specs | `agents/ADLC-BUILD-BRIEF-AGENT.md` | ☐ |
| P4-PS-001 | Define permission tier classification | `docs/specs/permission-tiers.md` | ☐ |
| P4-PS-002 | Define permission decision logging | `docs/specs/permission-logging.md` | ☐ |
| P4-SP-001 | Define session state schema | `docs/schemas/session-state.schema.json` | ☐ |
| P4-SP-002 | Define persistence trigger spec | `docs/specs/session-persistence.md` | ☐ |
| P4-SE-001 | Define streaming event schema | `docs/schemas/streaming-events.schema.json` | ☐ |
| P4-SE-002 | Define stop reason taxonomy | `docs/specs/stop-reasons.md` | ☐ |
| P4-SL-001 | Define system log schema | `docs/schemas/system-log.schema.json` | ☐ |
| P4-SL-002 | Add system logging to agent/skill specs | Agent + skill files | ☐ |
| P5-TP-001 | Define phase-specific tool pools | `docs/specs/tool-pools.md` | ☐ |
| P5-TC-001 | Define transcript compaction strategy | `docs/specs/transcript-compaction.md` | ☐ |
| P5-PA-001 | Define permission audit trail schema | `docs/schemas/permission-audit-trail.schema.json` | ☐ |
| P5-HC-001 | Define health check spec | `docs/specs/health-check.md` | ☐ |

**Acceptance:** All 12 infrastructure primitives have specification documents. All Week One gaps have implementation specs.

---

## Task Summary

| Phase | Task Count | Scope Signal |
|-------|-----------|-------------|
| Phase 1: Workflow State | 8 tasks | Sprint (2 weeks) |
| Phase 2: Budget + Verification | 16 tasks | Sprint (2 weeks) |
| Phase 3: Contracts + Compatibility | 17 tasks | Sprint (2 weeks) |
| Phase 4: Remaining Gaps | 15 tasks | Ongoing |
| **Total** | **56 tasks** | **~6 weeks + ongoing** |

---

## Cross-References

- [Infrastructure Primitives Audit](./INFRASTRUCTURE_PRIMITIVES_AUDIT.md) — full audit findings and risk assessment
- [Backwards/Forwards Compatibility Analysis](./COMPATIBILITY_ANALYSIS.md) — contract surface analysis and versioning gaps
