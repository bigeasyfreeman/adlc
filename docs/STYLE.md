# ADLC Editorial Style

Status: public product-language contract  
Contract version: 1.0.0

## Outcome before machinery

Start with what the engineer can accomplish: reproduce and fix a defect, build a bounded change, review without mutation, resume safely, or prepare a release package. Introduce schemas, gates, queues, worktrees, and manifests only when they explain why the outcome is repeatable or trustworthy.

Bad: “ADLC is a schema-backed multi-agent DAG.”  
Good: “Run an evidence-bound Fix loop that reproduces the defect before changing code and stops if proof is missing.”

## Voice

Use direct, calm, specific language. Prefer short active sentences. State the observable result first, then the evidence and limitation. Never personify a verifier or imply that confidence is proof. Avoid hype, competitive chest-thumping, and vague category language such as “AI engineering platform.”

## Terminology

- **evidence-bound**: a completion or support claim points to versioned, replayable evidence;
- **loop**: Build, Fix, or read-only Review, with explicit states and terminal outcomes;
- **kernel**: deterministic state, permission, action-admission, verification, recovery, and evidence machinery;
- **skill**: the canonical public `adlc` router and its bounded references;
- **provider**: a named coding-agent harness and version, not a universal capability;
- **read-only**: no file, index, branch, tracker, approval, or provider mutation;
- **blocked**: progress stopped on a named missing condition with a recovery action;
- **PR-ready**: a scoped local change and evidence package; it does not mean merged or published.

Use Build, Fix, and Review as proper loop names. Use “human approval,” not “human in the loop,” when a specific decision is required.

## Claims and evidence

Write claims as: capability, exact scope, version/environment, observed result, evidence reference, and limitation. Distinguish deterministic fixture evidence from provider-native behavior and clean release-artifact behavior. Do not turn “file exists,” “schema validates,” “dry run passes,” or “agent said success” into a behavioral claim.

Every completion summary separates proved, contradicted, incomplete, and unverified requirements. Preserve failures and variance instead of selecting the best run.

## Provider support language

Use only `unsupported`, `experimental`, `beta`, or `supported`, and always attach the label to a provider/version plus a dimension or loop. For example: “Codex X invocation: beta” is valid only with current native invocation evidence. “Works with Codex” is too broad.

Installation, discovery, invocation, Build, Fix, Review, hooks, and release artifact are independent cells. Missing credentials produce a blocked or untested cell, never a silent fallback. A fixture-only pass cannot exceed experimental behavioral status.

## Commands

Write public commands as `/adlc command`. Start each command page with purpose, preconditions, example, outputs, stop states, side effects, approval points, and troubleshooting. Low-level `bin/adlc` commands belong in advanced kernel reference and should not lead onboarding copy.

Review is read-only by default. A request to “review and clean up” must report findings without editing and direct the user to invoke Build or Fix separately.

## Accessibility and examples

Examples must work when copied, use placeholders for credentials, avoid developer-local paths, and identify expected output or stop status. Diagrams require adjacent prose. Links use descriptive labels. Tables must not be the only place a safety boundary is explained.

Use one substantive example rather than several toy successes. Include negative and recovery examples for credentials, approval, stale bundles, dirty worktrees, and rollback.

## No-overclaim boundary

Do not say production-ready, GA, autonomous, secure, supported, reproducible, transactional, or read-only unless the exact named behavior has current evidence at the released version. Never claim universal superiority, guaranteed traction, or compliance certification.

`doc_honesty_section`: Editorial consistency does not prove product behavior.  
`no_overclaim`: Prose must be generated from or linked to the current evidence matrix wherever practical.  
`limitations`: Beta language may describe measured behavior only; untested cells remain explicit.
