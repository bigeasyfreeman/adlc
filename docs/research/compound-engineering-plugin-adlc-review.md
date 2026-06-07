# Compound Engineering Plugin Review For ADLC

Date: 2026-06-06
External repo: `https://github.com/EveryInc/compound-engineering-plugin`
Reviewed commit: `966e32f5b5efec4830b347fff420482e05c90d4e`
Local checkout: `/tmp/adlc-compound-research/compound-engineering-plugin`

## Research Basis

- Ran `graphify update .` in ADLC. Refreshed ADLC graph at current checkout.
- Cloned `EveryInc/compound-engineering-plugin` locally and ran `graphify update .`.
- External Graphify output: `8136` nodes, `8893` edges, `666` communities. HTML visualization skipped because the graph exceeded the default 5000-node limit; `graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.json` were generated.
- Reviewed the external plugin docs and source skill contracts, especially:
  - `README.md`
  - `CONCEPTS.md`
  - `docs/skills/ce-plan.md`
  - `docs/skills/ce-work.md`
  - `docs/skills/ce-compound.md`
  - `docs/skills/ce-compound-refresh.md`
  - `docs/skills/ce-code-review.md`
  - `docs/skills/ce-sessions.md`
  - `plugins/compound-engineering/skills/ce-compound/SKILL.md`
  - `plugins/compound-engineering/skills/ce-compound-refresh/SKILL.md`
  - `plugins/compound-engineering/skills/ce-sessions/SKILL.md`
  - `docs/solutions/skill-design/script-first-skill-architecture.md`
  - `docs/solutions/skill-design/pass-paths-not-content-to-subagents.md`
  - `docs/solutions/skill-design/research-agent-pipeline-separation.md`
  - `docs/solutions/skill-design/confidence-anchored-scoring.md`

## Executive Recommendation

ADLC should not import the Compound Engineering plugin wholesale. ADLC already has the stronger lifecycle shape for its purpose: graph-backed research, Build Briefs, applicability overlays, zero-read codegen context, bounded DAG routing, verifier-first execution, Eval Council, comprehension gates, idempotent emitters, and workflow state.

The useful additions are narrow:

1. Add a concrete learning-store contract that backs ADLC's existing reuse-analysis and feedback-loop language.
2. Add a learning refresh workflow so the store stays accurate instead of accumulating stale advice.
3. Make task identity stability explicit across brief revisions and execution resumes.
4. Strengthen code-task resumability with per-task completion fingerprints and verifier status, not just phase-level workflow state.
5. Adopt script-first preprocessing for large deterministic scans.
6. Optionally add cross-harness session-history extraction as an input to learning capture, not as a general planning dependency.

These additions make ADLC more performant because they reduce repeated research, prevent duplicated fixes, make resume cheaper, and keep the context fed to agents smaller and more current. They do not require adding a second planner, review framework, or plugin distribution layer.

## Already Covered In ADLC

| Compound plugin pattern | ADLC equivalent | Recommendation |
|---|---|---|
| Plan as guardrails, not implementation choreography | BLE/BPE philosophy; Build Brief; planner constraints; codegen context | Keep ADLC wording. Do not import CE plan format. |
| Multi-agent research before planning | `research` node, Graphify, `graph-research`, `codebase-research`, `paved-road-registry` | Already covered. Add learning-store input only. |
| Reuse before building | `reuse-analysis`, `paved-road-registry`, scalable code primitives | Already covered. Learning store should feed these. |
| Parallel execution | ADLC fan-out, max fan-out, workspace isolation spec | Covered conceptually. Improve task-level state and worktree contract. |
| Multi-persona review | Eval Council, code-reviewer, security-reviewer, comprehension gate | Already stronger. Do not duplicate CE review stack. |
| Fix/debug loop | `fix-loop`, `systematic-debugging`, verifier-first coder | Already covered. Add learning capture at successful closeout. |
| Cross-platform plugin installer | `setup.sh`, platform targets, ADLC adapters | Do not import CE converter architecture. |

## Worth Adding

### 1. Learning Store Contract

ADLC already mentions a learning store in `reuse-analysis`, `adlc-v2-specification`, and `adlc-v2-tickets`, but there is no concrete checked-in store contract. Borrow the CE concept, not its whole workflow:

- directory: `docs/solutions/`
- frontmatter: compact fields only
- two tracks:
  - bug/fix learning: symptom, root cause, failed attempts, fix, prevention
  - knowledge learning: context, guidance, applicability, examples
- categories mapped to ADLC's existing domains rather than Rails-specific enums
- discoverability: surface `docs/solutions/` in `AGENTS.md`/`CLAUDE.md` or ADLC platform templates

Minimum ADLC-specific schema:

```yaml
title: string
date: YYYY-MM-DD
adlc_domain: build_loop | fix_loop | feedback_loop | integration | security | observability | testing | workflow | other
problem_type: bugfix | build_validation | lint_cleanup | runtime_failure | performance | security | workflow | architecture | convention | tooling
module: string
severity: critical | high | medium | low
tags: [string]
related_tasks: [brief_id/task_id/work_item_id]
source_evidence: [path:line | command | graph query | PR | issue]
```

Why this matters: the planner already requires reuse and prior-art evidence, but without a durable searchable store the evidence source is underspecified.

### 2. Learning Capture Skill

Add an ADLC-native skill, likely `skills/learning-capture/SKILL.md`, triggered after:

- successful `fix-loop` delivery
- successful `pr_prep`
- code-review or Eval Council identifies a reusable pattern
- human says the fix worked and the solution is verified

Keep the first version lightweight:

- no required subagents
- no auto-invoke unless the host platform supports it cleanly
- write one doc or update one high-overlap doc
- validate frontmatter with a small script
- optionally add instruction-file discoverability if missing

Do not start with CE's full parallel Context Analyzer / Solution Extractor / Related Docs Finder flow. ADLC can add deeper overlap detection after the basic store is useful.

### 3. Learning Refresh Skill

Add `skills/learning-refresh/SKILL.md` or fold into `feedback-loop` as a maintenance mode. Borrow CE's five outcomes:

- Keep
- Update
- Consolidate
- Replace
- Delete

ADLC-specific constraints:

- delete, do not archive; git history is the archive
- broad refresh must start with triage, not full-file reads
- ambiguous headless cases get marked stale rather than rewritten
- refresh only on a scope hint, significant refactor, or capture-triggered stale signal

This prevents the learning store from becoming a second source of stale context.

### 4. Stable Task Identity Rule

CE's U-ID rule is one of the highest-value low-complexity additions. ADLC already has `task_id`, structured AC IDs, dependencies, work-item emitters, and idempotency keys. It should explicitly require:

- task IDs are stable after first emission
- no renumbering or semantic reuse of a deleted task ID
- splits keep the original ID on the original concept; new work gets new IDs
- acceptance criteria IDs remain stable across brief revisions
- dependency references and PR summaries cite task IDs

This should be added to:

- `agents/planner.md`
- `docs/schemas/build-brief.schema.json` descriptions where useful
- `skills/codegen-context/SKILL.md`
- `docs/specs/workflow-checkpoints.md`
- contract tests that mutate a brief and verify IDs are preserved

### 5. Task-Level Resume Fingerprints

ADLC workflow state currently captures phase, history, and external side effects. CE's idempotent execution idea should be adapted to ADLC's verifier-first execution:

For each executable task, persist:

```json
{
  "task_id": "string",
  "input_hash": "hash of task contract + verifier",
  "status": "pending | in_progress | completed | failed | skipped_already_satisfied",
  "primary_verifier": "command or test ref",
  "pre_change_status": "failed_expected | missing | wrong_failure | not_applicable",
  "post_change_status": "passed | failed | not_run",
  "changed_files": [],
  "commit": "sha or null",
  "evidence": []
}
```

This lets `resume-workflow` rerun only incomplete tasks and lets `coder` skip already-satisfied units with evidence. ADLC has the phase-level pieces; the missing part is task-level completion state tied to verifiers.

### 6. Worktree Isolation Contract

ADLC already says each task gets its own workspace branch and each run gets a clone or worktree. CE's `ce-worktree` adds practical setup details worth borrowing:

- canonical location such as `.adlc/worktrees/<brief-id>/<task-id-or-branch>`
- copy `.env*` except `.env.example` when policy allows
- never auto-trust modified `.envrc` or unreviewed dev-tool config from PR/review branches
- add worktree directory to gitignore or local exclude
- subagents do not stage/commit/run full suite in shared-directory fallback
- merge worktree branches sequentially and rerun relevant verifiers after each merge

This is performance work because safe parallelism only pays off when the worktrees are actually runnable.

### 7. Script-First Mechanical Processing

Borrow CE's script-first principle for deterministic or high-volume ADLC scans:

- learning-store inventory and overlap prefilter
- session-history extraction
- frontmatter validation
- task completion fingerprinting
- Graphify freshness checks
- idempotency side-effect reconciliation

Model responsibilities should be judgment and synthesis. Scripts should parse, count, filter, and classify whenever rules are deterministic.

### 8. Optional Session History Research

CE's `ce-sessions` is useful, but should not become required ADLC planning context. ADLC should add it only as:

- optional enrichment for `learning-capture`
- optional resume/debug helper when a user asks what was tried before
- bounded time window and max-session cap
- extraction scripts first; never model-read raw session JSONL

This avoids repeated investigation without making every run depend on historical transcripts.

## Avoid Importing

Do not add these to ADLC now:

- CE's cross-platform plugin converter and marketplace machinery. ADLC already has `setup.sh`, platform targets, runtime adapters, and MCP wrapper work.
- CE's full 37-skill/50-agent surface. ADLC should stay DAG plus thick skills, not a large slash-command bundle.
- CE's `ce-plan` as a replacement planner. ADLC's Build Brief is stricter and schema-backed.
- CE's `ce-code-review` review stack. ADLC's Eval Council, code-reviewer, security-reviewer, test-strength, slop-gate, and comprehension-gate already cover the core.
- CE's Proof integration unless ADLC explicitly needs collaborative markdown review. It is a product integration, not a core lifecycle primitive.
- Auto-invoke UX as a core dependency. Useful where supported, but ADLC should remain runnable through deterministic CLI/MCP phases.
- Broad learning refresh by default. It will create churn. Refresh needs scope hints or concrete drift evidence.

## Suggested First Implementation Slice

1. Add `docs/specs/learning-store.md`.
2. Add `docs/schemas/learning-entry.schema.json`.
3. Add `skills/learning-capture/SKILL.md` with a lightweight headless path.
4. Add `scripts/validate_learning_entry.py`.
5. Update `skills/reuse-analysis/SKILL.md` and `agents/planner.md` to treat `docs/solutions/` as a first-class prior-art source when present.
6. Update `platform/AGENTS.md` and `platform/CLAUDE.md` templates to mention `docs/solutions/` if adopted.
7. Add tests:
   - schema validates a sample bug-track learning
   - schema validates a sample knowledge-track learning
   - validator rejects malformed frontmatter or missing evidence
   - planner/reuse-analysis contracts mention learning store

Second slice:

1. Add stable task identity wording and tests.
2. Extend workflow state with task-level execution fingerprints.
3. Add `resume-workflow` reporting for completed/skipped/incomplete tasks.

Third slice:

1. Add scoped `learning-refresh`.
2. Add deterministic inventory/overlap prefilter script.
3. Add optional session-history extractor integration for learning capture.

## Bottom Line

Compound engineering is already aligned with ADLC's theory: every run should leave the next run with better verified context. ADLC does not need another orchestration framework to get that. It needs a durable, maintained learning layer and stronger task-level resumability so graph research, reuse analysis, verification, and fan-out keep getting cheaper over time.
