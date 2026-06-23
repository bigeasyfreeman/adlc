# Learning And Architecture Memory

## Purpose

This contract makes ADLC memory useful to loops without letting memory become an unchecked architecture override. Learning and architecture memory are prior-art signals. They can make a future run cheaper and safer, but they do not prove current behavior by themselves.

## Runtime Surfaces

ADLC exposes three deterministic commands for harnesses and agents:

| Command | Contract |
|---|---|
| `bin/adlc architecture-memory` | Validates architecture decision candidates and, with action admission, writes entries under `docs/architecture/decisions/`. |
| `bin/adlc memory-health` | Audits `docs/solutions` and architecture memory for stale refs, overclaim, and duplicate primitive proposals. |
| `bin/adlc champion-holdout` | Evaluates prompt or skill challengers against champion, working set, holdout set, and must-pass rules. |

All three commands emit schema-backed JSON and are exposed through MCP as `adlc_architecture_memory`, `adlc_memory_health`, and `adlc_champion_holdout`.

## Architecture Memory

Architecture memory records decisions that should constrain later runs. A valid architecture decision candidate includes:

- stable `decision_id`
- title and status
- context and decision text
- `architecture_boundary`
- `affected_paths`
- `source_evidence`
- `verifier_evidence`
- `stale_conditions`
- `no_overclaim`

Dry-run mode validates and plans writes. Write mode requires `--allow-mutation` plus action admission for tool `adlc-memory` and action `write_architecture_memory`. This keeps architecture memory writable by a harness, but not silently writable by an LLM loop.

## Memory Health

`memory-health` checks two memory stores:

- `docs/solutions` learning entries
- `docs/architecture/decisions` architecture memory entries

It reports:

- stale learning when changed paths intersect modules, source evidence, verifier commands, or stale conditions
- stale architecture memory when changed paths intersect affected paths, source evidence, architecture boundary, or stale conditions
- overclaimed learning when a learning entry fails validation or redaction is not passed
- overclaimed architecture memory when an accepted decision lacks boundary, evidence, stale conditions, affected paths, or no-overclaim notes
- duplicate primitive proposals when a proposed command, skill, schema, spec, or loop already exists and the proposal lacks `reuse_refs`

Stale refs are warnings. Overclaim and duplicate primitive issues are blocking.

## Champion And Holdout Gate

`champion-holdout` prevents prompt and skill changes from being promoted on the same examples used for editing.

Promotion requires:

- at least one holdout case
- challenger holdout average beats champion holdout average by `promotion_margin`
- all `must_pass_rules` pass

Working-set improvement alone is rejected with `working_set_only_improvement`. This lets ADLC improve prompts and skills from evidence while avoiding overfit prompt tweaks and silent regressions.

## Non-Goals

Learning and architecture memory does not auto-merge prompt or skill changes, choose architecture direction, run provider-specific embedding search, or claim self-autonomy. It provides the memory, health, and promotion gates needed before broader loop-library and meta-harness work.
