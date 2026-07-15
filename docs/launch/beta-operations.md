# Public beta operations

## Ownership and intake

The weekly `beta-duty-owner` triages sanitized beta issues. The
`security-response-owner` owns private vulnerability reports, and the
`human-release-owner` owns package, GitHub Release, Pages, and communication
approval. If no named human is on a role, cohort expansion stops.

Use `.github/ISSUE_TEMPLATE/beta_feedback.yml` for outcomes, friction, and
feature evidence. Bugs use the bug template. Vulnerabilities never use public
issues; use the private Security Advisory link. Triage may propose
`beta-feedback`, `needs-reproduction`, `provider-specific`, `docs`, or
`release-blocker` labels; repository label creation remains an owner action.

## Response expectations

| Class | Example | Acknowledge | Next update |
| --- | --- | --- | --- |
| Severity 1 | credential exposure, approval bypass, corrupt release evidence | 4 hours | every 8 hours while active |
| Severity 2 | reproducible install failure or evidence-integrity regression | 1 business day | within 2 business days |
| General beta feedback | workflow friction, request, interview offer | 3 business days | at weekly review |

These are beta response targets, not a paid support SLA. Public replies contain
no private repository data, credentials, or unredacted run artifacts.

## Weekly evidence review

The beta-duty-owner records local funnel aggregates, issue counts by class,
response misses, supported-provider evidence changes, and each gate's eligible
run/finding counts. A gate may enter keep/adjust/retire review after ten eligible
zero-finding runs, but security, privacy, destructive-action, and human-approval
gates are exempt from automatic retirement proposals. No gate is silently
disabled.

Roadmap candidates require repeated user evidence, an owner, a bounded outcome,
and a verifier. One request does not create a roadmap promise. Dates and
enterprise packaging remain out of the public beta roadmap.

## Interview narrative

Ask the operator to replay one recent loop: what they expected, where they lost
trust, which evidence they checked, what they did manually, and whether they
returned to the same project. Avoid a feature tour. End by reading back the
observed outcome and asking permission before retaining only sanitized notes.

## Stop and rollback

Stop launch communication immediately for secret/private-data exposure, an
approval bypass, mismatched release bytes, or a reproducible severity-1 install
or evidence defect. Hold cohort expansion after two severity-2 acknowledgement
misses in one review week. Follow `docs/release/RELEASING.md`, preserve the
failed evidence, do not move or reuse a tag, and publish corrective guidance
only after human approval.

`doc_honesty_section`: This operating model names roles and targets; it does not
claim a staffed commercial support organization.

`no_overclaim`: Beta feedback does not prove demand, retention, enterprise fit,
or a committed roadmap.

`limitations`: Initial operations use GitHub issues, private advisories, direct
interviews, and manual local aggregates rather than a hosted support system.
