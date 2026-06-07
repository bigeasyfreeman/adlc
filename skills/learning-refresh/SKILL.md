---
name: learning-refresh
description: "Scoped maintenance for docs/solutions entries when stale signals, refactors, or explicit user scope require refresh."
contract_version: 1.0.0
side_effect_profile: mutating
activation:
  mode: scoped_maintenance
  consumes_manifest: true
  trigger_fields:
    - stale_conditions
    - module
    - adlc_domain
  produces:
    - learning_refresh_report
---

# Learning Refresh

## Purpose

Keep `docs/solutions` useful without turning every ADLC run into a documentation sweep.

## Trigger

Run only with a concrete scope:

- a stale condition from a learning entry fired
- a user requested refresh for a module, domain, or tag
- a significant refactor touched cited source evidence
- learning capture detected overlap with an older entry

## Outcomes

Use one outcome per reviewed entry:

- `Keep`: still accurate and useful
- `Update`: same learning, refreshed evidence or verifier
- `Consolidate`: merge overlapping entries and delete duplicates
- `Replace`: supersede misleading guidance with a new entry
- `Delete`: remove obsolete or unsupported entries; git history is the archive

Ambiguous headless cases should be marked stale rather than rewritten.

## Process

1. Inventory only the scoped entries.
2. Read cited source evidence and run the verifier when practical.
3. Update frontmatter and body only when the evidence supports it.
4. Validate every changed entry with `python3 scripts/validate_learning_entry.py`.
5. Emit a refresh report with unchanged, changed, stale-marked, and deleted paths.

## Rules

- No broad refresh by default.
- No archive directory; delete obsolete files.
- No unsupported rewrites when evidence is missing.
- No full solution-store dump into model context.
