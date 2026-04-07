# Deprecation Protocol Spec

## Lifecycle
1. **Announce** deprecation in changelog + schema notes.
2. **Dual-emit** old and new fields for 2 major release windows (default).
3. **Warn** consumers when deprecated fields are read.
4. **Remove** field on next scheduled major release.

## Rules
- No silent removals.
- Every major change requires migration notes and before/after examples.
- Deprecation warnings must include consumer identity and upgrade target.

## Warning Event
```json
{
  "type": "contract.deprecation_warning",
  "field": "tasks[].failure_modes_legacy",
  "replacement": "tasks[].failure_modes",
  "consumer": "codegen-context",
  "remove_in": "3.0.0"
}
```
