# What did your coding agent actually prove?

Coding agents are good at producing changes. The harder engineering problem is
knowing what happened around the change: whether the failure was reproduced,
which verifier turned red and then green, what the review found, and what still
needs a human decision.

ADLC 0.9.0 beta gives an existing coding agent three repeatable loops—Build,
Fix, and read-only Review—and keeps deterministic truth in schemas, state,
permissions, tests, and evidence records. The product promise is deliberately
narrow: every completion claim should point to evidence, or the loop should say
why it is blocked.

## The five-minute proof

The public Fix demo begins with an invoice-average defect. The verifier fails
for the expected behavior, the agent makes a one-file repair, and the same
verifier passes. The run then survives an interrupt/resume boundary and ends
with distinct read-only review and completion-audit evidence. The published
benchmark preserves three primary Codex runs and three independent replay runs,
including timings, token use, configuration, raw artifacts, and limitations.

That evidence supports one scoped claim: the exact Codex Fix configuration in
the [support matrix](../trust/support-matrix.md) earned a beta label. It does not
upgrade other providers, models, loops, or future runs.

## Why the control plane matters

ADLC does not replace a coding agent. It routes intent into a small public
vocabulary while a deterministic kernel owns admission, persisted state,
verification, human gates, and evidence. Review stays read-only. External
publish, merge, release, deploy, destructive recovery, and paid actions remain
approval-bound.

The resulting terminal state is honest: `pr_ready`, blocked with a named
reason, or awaiting a human. It is never silently “done” because an agent wrote
confident prose.

## Try the beta locally

Follow the [installation guide](../start/installation.md), run `adlc-skill
doctor`, and use the [first Fix guide](../start/first-fix.md). The demo script in
this packet provides a reproducible recording plan. Sanitized feedback belongs
in the beta issue template; vulnerabilities belong in the private security
advisory path.

Beta activation metrics stay local. There is no telemetry endpoint, and the
optional anonymous exporter is only a future proposal requiring explicit
opt-in and a separate security/privacy review.

`doc_honesty_section`: This article describes a final-form beta candidate and
links to repository evidence; it does not prove publication or adoption.

`no_overclaim`: The benchmark does not establish superiority, universal
provider behavior, enterprise readiness, security certification, or GA.

`limitations`: Current live evidence is confined to the exact Codex Fix row,
and future provider/model behavior can differ.
