# ADLC Compound Engineering Workflow Integration Goal Prompt

Use this with `/goal` or a high-reasoning Codex run from `/Users/eric/adlc`.

```text
Integrate compound engineering into ADLC as a workflow-native learning and resume layer. Work in /Users/eric/adlc.

The execution contract is:

docs/build-briefs/compound-engineering-workflow-integration.json

Do not treat compound engineering as a standalone feature or plugin import. The objective is to make ADLC scale upward by making every run cheaper for the next run:

- deterministic compound preflight before research
- durable docs/solutions learning store
- learning refs consumed by research, planning, reuse analysis, and codegen context
- task-level resume fingerprints tied to verifier state
- conditional learning capture at closeout
- scoped learning refresh maintenance, not default workflow ceremony

Follow the Build Brief tasks in dependency order:

1. ADLC-CEI-001: Add ADLC learning store contract.
2. ADLC-CEI-002: Add compound context preflight.
3. ADLC-CEI-003: Consume learning refs in research, planning, reuse, and context assembly.
4. ADLC-CEI-004: Add task-level resume fingerprints.
5. ADLC-CEI-005: Add conditional learning capture closeout.
6. ADLC-CEI-006: Add scoped learning refresh maintenance.
7. ADLC-CEI-VAL: Validate compound workflow integration end to end.

Required preflight:

- Run `git status --short` and preserve user WIP.
- Read `docs/build-briefs/compound-engineering-workflow-integration.json`.
- Read `docs/research/compound-engineering-plugin-adlc-review.md`.
- Use Graphify before broad source search:
  - If `graphify-out/GRAPH_REPORT.md` exists, inspect freshness against `git rev-parse HEAD`.
  - Run `graphify update .` if stale or after code changes.
  - Query workflow/schema/skill relationships relevant to compound preflight, learning capture, refresh, and task fingerprints.

Implementation constraints:

- Reuse existing ADLC primitives before adding new abstractions.
- Keep all new schema fields optional unless the Build Brief explicitly requires otherwise.
- Keep missing `docs/solutions` and missing `graphify-out` as explicit no-op paths.
- Do not add broad automatic refresh.
- Do not paste full solution notes into codegen context.
- Do not treat solution notes as proof of code behavior without direct verification.
- Do not commit generated `graphify-out/` unless explicitly requested.

Validation required before final:

- `bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/compound-engineering-workflow-integration.json --json`
- `bin/adlc emit-work-items --target github --build-brief docs/build-briefs/compound-engineering-workflow-integration.json --dry-run --require-ready --json`
- `bash tests/test_adlc_cli.sh`
- `bash tests/test_adlc_contracts.sh`
- `python3 -m py_compile scripts/adlc.py scripts/validate_learning_entry.py`
- valid learning-entry fixture passes
- invalid learning-entry fixture fails
- `git diff --check`
- `graphify update .`
- `graphify query "How is compound engineering integrated into ADLC workflow and what risks remain?" --budget 2500`

Final response must include:

- changed files grouped by Build Brief task
- validation commands and results
- Graphify freshness/result summary
- any intentionally deferred work
- whether generated `graphify-out/` remains untracked

Do not claim end-to-end integration unless the workflow, CLI, schema, skill, and validation surfaces all changed and passed.
```
