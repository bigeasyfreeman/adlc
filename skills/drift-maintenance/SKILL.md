# Skill: Drift Maintenance

> Refreshes ADLC `source_context` and file path references on existing tickets when ADLC re-runs against them. Prevents the slow drift that makes ticket scope references fictional over time.

---

## Trigger

Activated as a sub-step of any work-item emitter (`linear-ticket-creation`, `jira-ticket-creation`, `github-issue-creation`) when the emitter discovers an existing artifact via idempotency key. Drift refresh runs BEFORE the emitter completes its update mutation.

This skill is required by [docs/specs/emitter-contract.md](/Users/eric/adlc/docs/specs/emitter-contract.md) under the "Source Context Refresh" section.

## Why This Exists

ADLC-generated tickets reference specific paths, PRD sections, and commits at generation time. As the codebase evolves, those references drift:

- Files move during refactors.
- PRD sections get renumbered or renamed.
- Old commit hashes become irrelevant as `HEAD` advances.

Without refresh, every codebase change orphans the tickets that reference the old state. The audit on the interralis board found 40% of 461 tickets referenced paths that no longer existed. Drift Maintenance is the systemic fix.

## Input

```json
{
  "ticket_id": "string",
  "ticket_description": "string — the current full description of the existing artifact",
  "workspace_repo_path": "string — absolute path to the workspace repo (e.g., /Users/eric/interralis)",
  "build_brief_id": "string",
  "current_adlc_source_context": "string — parsed from ticket description if present"
}
```

## Procedure

1. **Parse `adlc:source_context`** from the ticket description. If the field is absent, log a warning and skip refresh (legacy ticket, no source context to refresh).

2. **Resolve current workspace state:**
   - `current_head = git -C <workspace_repo_path> rev-parse HEAD`
   - `current_prd_version = parse from <workspace_repo_path>/docs/PRD.md header (or equivalent canonical product doc)`
   - `current_file_tree = git -C <workspace_repo_path> ls-files`

3. **For each path reference in the ticket description** (regex-extract file paths matching `(src|tests|docs|bin|scripts|charts|packaging)/...`):
   - If path exists in `current_file_tree`: status = `current`.
   - If path moved (heuristic: file basename exists elsewhere in tree): status = `moved_to:<new_path>`. Update the reference in the description.
   - If path deleted with no clear successor: status = `deleted_no_replacement`. Add to drift_set for human triage.

4. **For each PRD section reference** (regex-extract `§X.Y` or `section X.Y` patterns):
   - Verify the section still exists at the current PRD version.
   - If section numbering changed: locate the successor section by heading text. Update the reference.
   - If section was deleted: add to drift_set with `deleted_no_replacement`.

5. **Compute refreshed `adlc:source_context`** with:
   - Updated commit SHA (`current_head`)
   - Updated PRD version
   - Updated section references (where renumbered)
   - Path references updated to current locations where moved

6. **Update the ticket description:**
   - Replace the old `adlc:source_context` line with the refreshed version
   - Update `adlc:last_refreshed_at` to current ISO8601 timestamp
   - For each `deleted_no_replacement` item in drift_set: post a `drift_comment` on the ticket describing the missing reference and a `needs_human_decision` marker

7. **Preserve the idempotency key unchanged.** Drift refresh is content-only.

## Output

```json
{
  "ticket_id": "string",
  "drift_items_found": [
    {"path": "src/old/path.rs", "status": "moved_to", "new_path": "src/new/path.rs"},
    {"path": "docs/DELETED.md", "status": "deleted_no_replacement"},
    {"section": "§3.4", "status": "moved_to", "new_section": "§3.5"}
  ],
  "refreshed_source_context": "string — the new adlc:source_context line",
  "refreshed_at": "ISO8601 timestamp",
  "needs_human_decisions": ["src/old/path.rs deleted with no replacement", "docs/DELETED.md no longer exists"],
  "idempotency_key_preserved": true
}
```

## Failure Modes

| Failure | Response |
|---|---|
| `adlc:source_context` missing from ticket | Skip refresh, log warning, return `skipped: missing_source_context` |
| Workspace repo path invalid | Fail loudly, return `error: invalid_workspace_path`. Do not silently skip. |
| PRD version cannot be determined | Skip PRD section verification, log warning, continue with path refresh only |
| `git ls-files` fails | Fail loudly, return `error: git_operation_failed` |
| MCP cannot fetch ticket | Fail loudly, return `error: ticket_fetch_failed`. Do not silently skip. |
| Drift set exceeds 20 items | Refresh the first 20, mark remaining as `needs_human_decision: drift_set_too_large`, return partial success |

## Relationship to Other Skills

- **`linear-ticket-creation` / `jira-ticket-creation` / `github-issue-creation`:** These emitters invoke drift-maintenance as a sub-step before completing update mutations. Drift refresh is mandatory for re-runs against existing artifacts.
- **`audit-tickets` (interralis-specific, not in ADLC):** The board-level drift audit script at `/Users/eric/interralis/.tmp/board-reform/audit-tickets.py` becomes obsolete once drift-maintenance is wired into the emitters — refresh happens at emission time, not as a separate post-hoc audit.

## Verification

A skill-conformance test for drift-maintenance should:

1. Construct a fixture ticket description with known `adlc:source_context`, file paths, and PRD section references.
2. Run drift-maintenance against a workspace where some paths have moved, some have been deleted, and the PRD section has been renumbered.
3. Verify the output reports:
   - `moved_to` updates for the moved paths
   - `deleted_no_replacement` entries for deleted paths
   - `moved_to` for the renumbered section
4. Verify the refreshed ticket description contains updated references.
5. Verify the idempotency key is byte-for-byte preserved.

## Backward Compatibility

Existing tickets without `adlc:source_context` are skipped gracefully. Existing tickets with stale references but no re-run trigger are not auto-refreshed — drift refresh is a per-emission action, not a background sweep.

For bulk drift cleanup of an existing ticket estate (like the interralis 461-ticket board), a one-time manual sweep using the audit script + targeted re-runs of relevant Build Briefs is the path. After that, drift-maintenance keeps the estate clean by construction.
