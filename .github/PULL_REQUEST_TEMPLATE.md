## Summary

Describe the bounded behavior or contract change.

## Why

Explain the evidence-backed problem and why this is the smallest coherent fix.

## Verification

- [ ] `bin/adlc ci --json`
- [ ] `git diff --check`
- [ ] Graphify refreshed after code changes
- [ ] No credentials, local paths, generated state, or process-only artifacts

List any additional targeted checks and their results.

## Compatibility and rollback

Describe affected schemas, commands, adapters, or persisted state and how to
reverse the change safely.

## Human decisions

Record any approval, waiver, or unresolved decision. Write `None` when there
is no human decision surface.
