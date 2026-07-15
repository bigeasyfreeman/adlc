# Build guide

Use Build when approved intent and a schema-valid Build Brief define scope, verifier, compatibility posture, and approval boundaries.

## Run

```text
/adlc build ADLC-MIG-010
```

Build loads the public Build loop, records the expected failing verifier, implements the smallest declared slice, runs affected and canonical gates, obtains independent review, and prepares a PR-ready evidence package.

## Inputs and outputs

Inputs are an approved Build Brief, target repository, task identifier, verifier contract, and authority boundary. Outputs are a scoped diff, verifier evidence, review findings, and one terminal state: `pr_ready`, `blocked_human_approval`, `blocked_credentials`, `failed_verification`, or `escalated`.

Build may mutate authorized local files. It cannot infer permission to publish, merge, release, deploy, delete a remote branch, or spend paid-model budget.

`doc_honesty_section`: PR-ready means the declared gates passed for the scoped commit.

`no_overclaim`: It does not mean merged, deployed, adopted, or generally available.

`limitations`: An incomplete or unapproved brief blocks mutation.
