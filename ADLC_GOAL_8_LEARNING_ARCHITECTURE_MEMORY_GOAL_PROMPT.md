# ADLC Goal 8: Learning And Architecture Memory

You are Codex working in the ADLC repository. This is Goal 8 of the ADLC loop-system maturity productionization sequence.

This prompt is a local execution artifact. Do not include this prompt file in the production commit unless the user explicitly asks. Commit only production runtime, schema, tests, and docs needed by the shipped tool.

Remote sync boundary: the remote branch should contain only the productionized working ADLC. Keep `graphify-out/` and local prompt artifacts local, even when they are useful for the run. Do not push Graphify output, one-off audits, or local execution prompts as part of Goal 8 closeout.

## Current Shipped Baseline

Treat these as already shipped and do not redo them unless a regression requires a small compatibility fix.

- Goal 1: control-plane verification and canonical `bin/adlc ci --json`.
- Goal 2: action admission, permission audit trails, and MCP exposure.
- Goal 3: durable run identity and resumable workflow state.
- Goal 4: tracker state synchronization through stable work-item IDs.
- Goal 5: queue and worktree substrate for safe parallel execution.
- Goal 6: executable deterministic tool nodes with schema-backed phase artifacts.
- Goal 7: first ADLC dogfood loop for bounded control-plane drift repair.

## Objective

Make ADLC compound from verified outcomes without damaging architecture. Goal 8 turns learning and architecture memory into harness-consumable control-plane surfaces, not chat notes.

The end state is:

- reusable learning remains tied to source evidence, verifier evidence, redaction status, and stale conditions
- architecture decisions are captured as explicit memory with boundaries, affected paths, evidence, and stale conditions
- stale learning and stale architecture decisions are detectable before reuse
- overclaimed memory is blocked when evidence, verifier, redaction, or boundary data is missing
- duplicate primitive proposals are detected before ADLC adds another command, schema, skill, loop, or spec that already exists
- prompt and skill evolution can use a champion/holdout gate that never promotes on the working set alone
- every new surface is exposed through CLI and MCP so an agent harness can consume it
- `bin/adlc ci --json` passes

## Design Boundary

This goal is not the packaged loop library and not the full self-actioning meta-harness.

In scope:

- architecture memory reports and entries
- memory health auditing for learning refs, architecture refs, stale signals, no-overclaim, and duplicate primitive proposals
- champion/holdout evaluation for prompt or skill changes
- schema aliases, CLI/MCP metadata, docs, fixtures, and tests

Out of scope:

- auto-merging prompt or skill changes
- broad semantic retrieval or provider-specific embedding search
- new LLM provider dependencies
- scheduled loops, daemons, deploys, or irreversible provider actions
- rewriting the existing `docs/solutions` learning store

## Required Preflight

1. Inspect branch and worktree.

```bash
git status --short --branch
git log --oneline -12
```

2. Read Graphify before source search.

```bash
sed -n '1,220p' graphify-out/GRAPH_REPORT.md
graphify query "ADLC learning capture architecture memory stale learning no-overclaim duplicate primitive champion holdout prompt skill promotion" --budget 4000
```

3. Inspect current learning, architecture, primitive, loop, and CLI/MCP surfaces.

```bash
rg -n "learning|architecture|stale|no_overclaim|duplicate|primitive|champion|holdout|mcp-tools|COMMAND_METADATA" scripts docs tests agents skills README.md WORKFLOW.md
```

4. Run the canonical gate before closeout.

```bash
bin/adlc ci --json
```

## Implementation Order

1. Add architecture memory as a schema-backed command.
   - Accept architecture decision candidates with decision ID, title, status, context, decision, boundary, affected paths, source evidence, verifier evidence, stale conditions, and no-overclaim notes.
   - Dry-run should validate and plan writes.
   - Mutating writes must require action admission and write only repo-local architecture decision entries.

2. Add memory health auditing.
   - Scan `docs/solutions` learning entries and architecture memory entries.
   - Report stale candidates from changed paths, missing source refs, missing verifier refs, or matched stale conditions.
   - Block overclaimed memory when evidence, verifier, redaction, or architecture-boundary data is missing.
   - Detect duplicate primitive proposals from a proposal artifact before adding new skills, commands, schemas, loops, or specs.

3. Add champion/holdout evaluation.
   - Compare champion and challenger scores on working and holdout sets.
   - Promote only when the challenger beats the champion on holdout by the configured margin and passes all must-pass rules.
   - Reject working-set-only improvements, holdout regressions, and must-pass failures.
   - Emit machine-readable evidence for future prompt or skill loops.

4. Wire harness consumption.
   - Add schema aliases.
   - Add CLI commands and MCP tool declarations.
   - Document the commands in README and the agent-native interface.
   - Add focused CLI and contract tests.

## Exit Gate

Goal 8 is complete when:

- ADLC can validate and write architecture memory only from evidence-backed candidates
- ADLC can audit learning and architecture memory for stale, overclaim, and duplicate primitive risks
- ADLC can evaluate prompt/skill champion challengers against holdout data
- all outputs are machine-readable and schema-valid
- all new commands are available through MCP
- `bin/adlc ci --json` passes

