# Skill Contract Versioning Spec

## Scope
Applies to every MCP skill input/output contract in ADLC.

## Required Fields
- `contract_version` in input payload
- `contract_version` in output payload

## SemVer Rules
- **Patch**: additive optional fields, no behavior change.
- **Minor**: additive required fields only if defaultable by callee.
- **Major**: breaking changes (removed fields, changed types/semantics).

## Compatibility Negotiation
Caller sends an expected range, e.g. `1.x`.
Skill behavior:
1. resolve supported version,
2. reject incompatible major versions,
3. return structured compatibility error.

## Error Shape
```json
{
  "error": "contract_version_incompatible",
  "expected": "1.x",
  "received": "2.0.0",
  "skill": "jira-ticket-creation"
}
```
