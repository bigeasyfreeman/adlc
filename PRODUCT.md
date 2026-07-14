# ADLC Product Contract

Status: approved implementation contract, not shipped-product evidence  
Contract version: 1.0.0  
Product owner: ADLC maintainer  
Approval source: `docs/build-briefs/adlc-skill-loop-productization.json`, `docs/research/adlc-skill-loop-productization-strategy.md`, and the structured product-owner record in `docs/evidence/skill-loop-productization/adlc-run-09d1561af2e2/ADLC-MIG-002.json`

## Public promise

> Run repeatable build, fix, and review loops with your coding agent, with every completion claim tied to evidence.

ADLC is an evidence-bound control plane for AI-assisted software delivery. It gives an existing coding agent a small, teachable workflow while the deterministic ADLC kernel owns state, permissions, verification, approvals, recovery, and evidence.

## Initial user

The first user is a senior engineer or hands-on engineering lead already using Claude Code or Codex. They want interruptible, auditable engineering execution without inventing a new orchestration prompt for every task. The initial team is a small engineering organization that needs to know what changed, what actually ran, what remains unproven, and where a human must decide.

## Problem

Coding agents can produce plausible work while skipping reproduction, weakening tests, replaying side effects, or overstating completion. ADLC already contains controls for those failure modes, but its current front door exposes internal machinery before a user reaches an outcome. The product contract replaces that machinery-first interface with one skill, eleven outcome commands, and three explicit loops over the existing kernel.

## First wedge

The first wedge is the Fix loop: capture a real defect, reproduce it, create or select a verifier that fails for the expected reason, apply the smallest repair, prove the verifier and affected suite pass, obtain independent review, and produce a PR-ready evidence package. A canonical proof includes one interruption and resume without duplicated effects.

Build and read-only Review use the same product vocabulary, but Fix is the first public demonstration and the first provider-behavior credibility gate.

## Public commands

| Command | Outcome | Mutation posture |
|---|---|---|
| `/adlc init` | Discover repository instructions and establish bounded ADLC project context. | Writes only reviewed `.adlc` project configuration. |
| `/adlc shape` | Turn ambiguous intent into a bounded, decision-ready brief. | Local artifacts only. |
| `/adlc build` | Run the Build loop from approved intent to PR-ready evidence. | Gated local mutation. |
| `/adlc fix` | Run the Fix loop from reproduction to PR-ready evidence. | Gated local mutation. |
| `/adlc review` | Return evidence-backed findings for a specific change. | Read-only unless the user separately invokes Build or Fix. |
| `/adlc harden` | Run applicable security, reliability, compatibility, and quality gates. | Read-only by default; repair requires explicit authorization. |
| `/adlc ship` | Prepare a PR or release package and stop at external approval. | External mutation requires human approval. |
| `/adlc status` | Explain current state, blockers, evidence, and next action. | Read-only. |
| `/adlc resume` | Continue persisted work without replaying completed effects. | Uses the persisted approval and mutation posture. |
| `/adlc doctor` | Verify installation, provider bundle, kernel, schemas, and credential posture. | Read-only. |
| `/adlc learn` | Propose a reusable learning from verified evidence. | Local proposal; promotion is gated. |

The compatibility CLI remains available during the 0.x beta window. Low-level commands are advanced kernel interfaces, not the onboarding path.

## Support labels

| Label | Meaning |
|---|---|
| `unsupported` | The combination is absent, intentionally refused, or known not to work. |
| `experimental` | An implementation exists, but clean installation or behavioral proof is incomplete. |
| `beta` | The named provider, version, dimension, and loop have current evidence, with published limitations. |
| `supported` | The exact release artifact passes the complete declared conformance and recovery matrix. |

Labels apply independently to installation, native discovery, invocation, Build, Fix, Review, hooks, and release-artifact behavior. Passing one cell never upgrades another cell or an entire provider.

## Context ownership

ADLC reads target-repository `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, nested instructions, package metadata, and test commands without overwriting them. ADLC-owned project context is limited to:

- `.adlc/PROJECT.md` for users, product intent, vocabulary, and non-goals;
- `.adlc/ENGINEERING.md` for architecture, conventions, verification, and release posture;
- `.adlc/config.json` for provider, loop, approval, privacy, and compatibility settings.

The context loader must return source paths, hashes, relevant excerpts, precedence, conflicts, warnings, and missing decisions. It must be bounded to the selected command and affected paths.

## Success metrics

The activation funnel is README visit, install, doctor pass, first loop started, honest terminal state reached, then a second loop within fourteen days. Locally computable metrics include install success by provider, time to doctor, time to first Fix, terminal-state distribution, resume success, duplicate-side-effect rate, gate catches, human decision load, and provider-specific failures.

Telemetry is off by default. Public benchmark results report at least three runs per claimed configuration, failures, spread, versions, redacted traces, and replay instructions.

## Brand voice

Lead with the engineering outcome, then explain the control that makes it trustworthy. Be direct, calm, concrete, and technically precise. Say what stopped and why. Prefer “the verifier passed at commit X” to “the agent succeeded.” Make limitations easy to find.

## Claim rules

Every public capability claim names the ADLC version, release artifact, provider and model version when applicable, loop or command, environment, evidence reference, and evidence time. Installation, discovery, invocation, loop behavior, hooks, and end-to-end conformance are separate claims. Fixture results are labeled fixture results. A dirty-tree result is candidate evidence, not current conformance.

“Production-ready,” “supported,” and “GA” are forbidden until the corresponding release gates have current evidence. Universal superiority, guaranteed traction, and compliance-certification language are never inferred from the control-plane tests.

## Non-goals

ADLC is not a replacement coding agent, a general multi-agent chat framework, a hosted control plane, a compliance certification, or a promise that every provider behaves identically. The initial release does not make GA claims for providers beyond evidence-backed Claude Code or Codex cells. It does not automatically merge, publish, deploy, delete remote branches, spend paid-model budget, or send launch communications.

## Honest status

`doc_honesty_section`: This document freezes the intended public interface and claim policy. It is not evidence that the interface, installer, provider behavior, documentation site, benchmark, or release exists.

`no_overclaim`: Current provider implementations and deterministic tests do not establish a supported provider or successful public loop. Those claims remain owned by ADLC-MIG-003 through ADLC-MIG-VAL.

`limitations`: Positioning and activation assumptions remain hypotheses until external beta use is measured. The compatibility window and support scope may narrow in response to evidence, but kernel safety controls cannot be weakened to improve a claim.
