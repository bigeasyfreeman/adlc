# Socraticode Indexing Contract

## Purpose

Define the deterministic indexing contract ADLC expects from Socraticode before agents use indexed codebase context for planning, reconciliation, or validation work.

## Contract Scope

Socraticode indexing is an evidence source, not a source-of-truth store. ADLC source files, schemas, specs, skills, agents, tests, and workflow definitions remain authoritative in git. The Socraticode index is valid only when it can be rebuilt from the workspace and can resolve public ADLC symbols back to repo files.

Generated or local diagnostic artifacts are outside the coverage denominator unless they are tracked and named by an ADLC contract. Local snapshots such as `codedb.snapshot` must not be edited, normalized, or committed as part of indexing validation.

## Required Operations

Run indexing from the repo root:

```text
codebase_index(projectPath)
codebase_status(projectPath)
codebase_search(projectPath, query)
codebase_symbols(projectPath, query)
codebase_symbol(projectPath, name, file)
codebase_graph_stats(projectPath)
```

`codebase_status` must report indexing complete before any indexed result is used as evidence. `codebase_graph_stats` may lag indexing briefly, but the final evidence bundle must include graph status or graph stats once graph construction is available.

## Coverage Definition

Index coverage is measured against the ADLC contract source set:

```text
coverage = indexed_contract_files / eligible_contract_files
```

Eligible contract files are tracked files under:

- `agents/`
- `skills/`
- `docs/`
- `scripts/`
- `bin/`
- `tests/`
- `WORKFLOW.md`
- `WORKFLOW.dot`
- `README.md`

Files excluded by git ignore rules, local snapshots, generated smoke outputs, and transient `.adlc/` runtime state are not eligible contract files.

The minimum acceptable coverage is `>= 95%`. A lower percentage blocks ADLC reconciliation work until the missing file classes are either indexed or explicitly documented as excluded.

## Symbol Resolution Proof

A valid index must resolve these public ADLC symbols or files:

| Probe | Expected resolution |
|---|---|
| `compute_readiness_report` | `scripts/adlc.py` |
| `normalized_work_item_payload` | `scripts/adlc.py` |
| `emit_work_items_payload` | `scripts/adlc.py` |
| `linear-ticket-creation` | `skills/linear-ticket-creation/SKILL.md` |
| `emitter-contract` | `docs/specs/emitter-contract.md` |
| `agent-native-interface` | `docs/specs/agent-native-interface.md` |

Each probe must return a concrete file path. Symbol lookups must not pass by returning only prose summaries, stale paths, or generated snapshots.

## Evidence Bundle

For ADLC validation work, capture:

1. `codebase_status` after completion, including indexed chunk count.
2. `codebase_graph_stats` or graph status after graph construction.
3. Search or symbol output for every probe in the symbol-resolution table.
4. The relevant ADLC readiness dry run when the work touches emitter payloads.

## Failure Modes

| Failure | Blocking condition | Required response |
|---|---|---|
| Incomplete index | Coverage `< 95%` or indexing still in progress | Re-run `codebase_index` or `codebase_update`; do not use results as evidence |
| Stale index | Changed tracked files are not reflected in search results | Run `codebase_update` before planning or reconciliation |
| Missing public symbol | Any required probe fails to resolve to a concrete file | Investigate indexing exclusions or symbol extraction gaps |
| Snapshot contamination | Results resolve primarily to `codedb.snapshot` or transient runtime output | Exclude local/generated artifacts from evidence and re-run validation |

## Reconciliation Dependency

Reconciliation work may use Socraticode findings only after the evidence bundle passes this contract. If indexing is unavailable, reconciliation can continue from git-backed ADLC files and dry-run payloads, but the missing Socraticode proof must be recorded as residual validation risk.
