# Public commands

Every command routes through the canonical `adlc` skill. The provider-facing form is `/adlc command`; `bin/adlc` remains an advanced compatibility interface.

Low-level contributor and compatibility commands are documented in [Advanced kernel and contributor CLI](advanced-kernel.md).

## `/adlc init`

- **Purpose:** discover repository instructions and establish bounded project context.
- **Preconditions:** a target repository and permission to write reviewed `.adlc` configuration.
- **Example:** `/adlc init this repository`.
- **Procedure:** discover target instructions, resolve precedence, report conflicts, then write only reviewed ADLC context.
- **Outputs:** source-aware project context, conflicts, and missing decisions.
- **Stop states:** initialized, blocked conflict, or missing decision.
- **Side effects:** reviewed `.adlc` configuration only.
- **Approval points:** configuration write.
- **Troubleshooting:** resolve instruction precedence instead of overwriting repository policy.
- **Compatibility:** wraps health preflight and bounded context discovery; low-level repository-convention commands remain available.
- **Honesty:** initialization proves context capture, not that later work follows it correctly.

## `/adlc shape`

- **Purpose:** turn ambiguous intent into a bounded, decision-ready brief.
- **Preconditions:** a stated outcome and target.
- **Example:** `/adlc shape add resumable imports`.
- **Procedure:** load bounded context, classify unknowns, ask or delegate decisions, and validate the resulting brief.
- **Outputs:** brief, questions, assumptions, and verifier contract.
- **Stop states:** decision-ready, awaiting human, or blocked evidence.
- **Side effects:** local planning artifacts only.
- **Approval points:** ratify intent and volatile decisions.
- **Troubleshooting:** answer named unknowns; do not let the pipeline self-answer.
- **Compatibility:** wraps goal-prompt and Build Brief contracts.
- **Honesty:** a decision-ready brief is approved intent, not implementation proof.

## `/adlc build`

- **Purpose:** run approved intent to PR-ready evidence.
- **Preconditions:** approved schema-valid Build Brief.
- **Example:** `/adlc build ADLC-MIG-010`.
- **Procedure:** admit the task, record its failing verifier, implement the declared slice, run gates, and obtain independent review.
- **Outputs:** scoped diff, tests, independent findings, and evidence package.
- **Stop states:** `pr_ready`, approval/credential block, failed verification, or escalation.
- **Side effects:** gated local mutation.
- **Approval points:** intent, external writes, publish, merge, release, and deploy.
- **Troubleshooting:** preserve a failed verifier and route diagnosis through Fix.
- **Compatibility:** delegates to the public Build loop and retained workflow/action-admission kernel commands.
- **Honesty:** PR-ready does not mean merged, deployed, adopted, or generally available.

## `/adlc fix`

- **Purpose:** reproduce and repair a defect.
- **Preconditions:** observable failure, affected target, and authority boundary.
- **Example:** `/adlc fix duplicate notification after resume`.
- **Procedure:** reproduce, record the expected red verifier, diagnose, repair narrowly, prove green, and review independently.
- **Outputs:** reproduction, diagnosis, repair, and red-to-green evidence.
- **Stop states:** `pr_ready`, `not_reproduced`, missing evidence, failed verification, or escalation.
- **Side effects:** local mutation only after reproduction.
- **Approval points:** destructive recovery, privileged access, and all external effects.
- **Troubleshooting:** never skip reproduction or substitute confidence for a verifier.
- **Compatibility:** delegates to the public Fix loop and retained action-admission/run-phase kernel commands.
- **Honesty:** green evidence covers the named defect and affected gates only.

## `/adlc review`

- **Purpose:** return evidence-backed findings without mutation.
- **Preconditions:** concrete diff, commit, PR, or artifact.
- **Example:** `/adlc review the current branch against main`.
- **Procedure:** inspect scope and contracts, reproduce concerns read-only, rank findings, and return a verdict.
- **Outputs:** severity-ranked findings, residual risks, and verdict.
- **Stop states:** findings, no findings, missing context, or escalation.
- **Side effects:** none in the target.
- **Approval points:** invoke separate Build or Fix before remediation.
- **Troubleshooting:** use temporary copies for destructive reproductions.
- **Compatibility:** delegates to the public Review loop and completion-audit kernel path.
- **Honesty:** no findings does not prove absence of defects.

## `/adlc harden`

- **Purpose:** run applicable security, reliability, compatibility, and quality gates.
- **Preconditions:** bounded target and applicability evidence.
- **Example:** `/adlc harden the authentication change`.
- **Procedure:** derive applicable overlays, run their gates, preserve failures, and report unresolved risks.
- **Outputs:** gate results, findings, and unresolved risks.
- **Stop states:** findings ready, blocked evidence, or escalation.
- **Side effects:** read-only by default.
- **Approval points:** separate repair authorization.
- **Troubleshooting:** do not activate irrelevant overlays or suppress applicable ones.
- **Compatibility:** wraps action admission and the applicable security/quality kernel phases.
- **Honesty:** passing selected gates is not a security certification.

## `/adlc ship`

- **Purpose:** prepare a PR or release package and stop at external approval.
- **Preconditions:** complete scoped evidence and clean compatibility posture.
- **Example:** `/adlc ship this PR-ready change`.
- **Procedure:** recheck scoped evidence, assemble the package, identify each external action, and stop for approval.
- **Outputs:** publication package, checks, and approval request.
- **Stop states:** awaiting human, blocked gate, or package ready.
- **Side effects:** preparation is local; external mutation is separate.
- **Approval points:** push, PR, merge, tag, publish, deploy, and communication.
- **Troubleshooting:** a green package is not permission to publish.
- **Compatibility:** wraps completion audit while retaining low-level publication tooling behind approval.
- **Honesty:** package-ready does not mean pushed, merged, tagged, published, or deployed.

## `/adlc status`

- **Purpose:** explain current state, blockers, evidence, and next action.
- **Preconditions:** optional persisted state.
- **Example:** `/adlc status`.
- **Procedure:** load persisted state without mutation and summarize phase, evidence, blockers, and next action.
- **Outputs:** read-only state summary.
- **Stop states:** current terminal, blocked, waiting, or runnable state.
- **Side effects:** none.
- **Approval points:** none.
- **Troubleshooting:** use Resume, not Status, to change state.
- **Compatibility:** wraps the retained read-only workflow-status path.
- **Honesty:** reported state is only as current as its persisted evidence and external checks.

## `/adlc resume`

- **Purpose:** continue persisted work without replaying completed effects.
- **Preconditions:** compatible state and authority boundary.
- **Example:** `/adlc resume`.
- **Procedure:** validate state compatibility, inspect completed effects, admit the next action, and continue from the checkpoint.
- **Outputs:** next action, approval need, and preserved effect evidence.
- **Stop states:** resumed, awaiting approval, conflict, or escalation.
- **Side effects:** inherits the persisted mutation posture.
- **Approval points:** any unresolved gate and any expanded authority.
- **Troubleshooting:** stop on state/commit mismatch or duplicate proposed effect.
- **Compatibility:** wraps resume-workflow and action admission without removing low-level recovery commands.
- **Honesty:** persisted idempotency evidence does not guarantee an external service honors it.

## `/adlc doctor`

- **Purpose:** verify bundle, kernel, schema, and credential posture.
- **Preconditions:** installed ADLC target.
- **Example:** `/adlc doctor`.
- **Procedure:** inspect installed bytes, runtime dependencies, schemas, provider layout, and credential posture.
- **Outputs:** named checks, warnings, and failures.
- **Stop states:** pass, warning, or failed required check.
- **Side effects:** none.
- **Approval points:** none.
- **Troubleshooting:** a pass proves preflight only, not provider behavior.
- **Compatibility:** wraps health-check and install-manifest verification.
- **Honesty:** doctor proves named preflight checks only.

## `/adlc learn`

- **Purpose:** propose reusable learning from verified evidence.
- **Preconditions:** versioned evidence and bounded lesson.
- **Example:** `/adlc learn from the verified retry fix`.
- **Procedure:** verify source evidence, check freshness and duplication, then emit a bounded local learning proposal.
- **Outputs:** a local learning candidate with sources and limitations.
- **Stop states:** proposed, rejected evidence, duplicate, or escalation.
- **Side effects:** local proposal only.
- **Approval points:** promotion into shared memory or skills.
- **Troubleshooting:** expire stale evidence and reject anecdote-only rules.
- **Compatibility:** wraps memory-health and the gated learning store.
- **Honesty:** a proposed learning is not promoted shared policy until separately approved.

`doc_honesty_section`: Command contracts describe required behavior and stop states.

`no_overclaim`: Availability in the public facade does not prove provider-native invocation.

`limitations`: Provider UI syntax and discovery behavior remain provider/version specific.
