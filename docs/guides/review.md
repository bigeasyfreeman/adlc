# Review guide

Use Review for a concrete diff, commit, PR, or artifact when you need evidence-backed findings without mutation.

## Run

```text
/adlc review the current branch against main
```

Review inspects contracts, code paths, tests, and current evidence; reproduces material concerns with read-only commands or temporary copies; and reports severity-ranked findings, open questions, residual risks, and a verdict.

Review never edits, commits, pushes, comments, labels, resolves threads, or changes approvals. “Review and clean up” still ends after findings; invoke Build or Fix separately for remediation.

Terminal states are `findings_ready`, `no_findings`, `blocked_missing_context`, or `escalated`.

`doc_honesty_section`: No findings means no findings in the inspected scope.

`no_overclaim`: Review cannot prove the absence of defects.

`limitations`: Missing runtime, credential, or deployment evidence remains unverified.
