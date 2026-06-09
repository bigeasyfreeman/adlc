# ADLC Loop Budget Guard Integration Goal Prompt

Use this with `/goal` from `/Users/eric/adlc`.

```text
You are Codex working in the ADLC repository. Implement the loop budget guard integration end to end.

The execution contract is:

docs/build-briefs/loop-budget-guard-integration.json

Objective:

Make token and cost budget evidence a first-class Loop Contract guard. LLM-backed loops must declare budget refs, action admission must check projected spend before continuing when budget evidence is supplied, maturity reports must show budget_status, and self_autonomous claims must be blocked when budget evidence is missing, stale, warning, alert, or exhausted.

This is framework productionization work. Do not import another orchestration framework, do not add a scheduler, and do not broaden into provider billing APIs. Reuse the existing ADLC primitives:

- Loop Contract / Loop Action / Loop Maturity Report schemas
- token-budget, pre-turn-check, cost-reporting, stop-reason, and session-state specs
- loop-test-selection, loop-action-validate, loop-maturity-audit
- workflow-state progress/control evidence
- planner, codegen-context, Eval Council, LLM security, and compound learning guidance

Required preflight:

1. Run `git status --short` and preserve unrelated user WIP.
2. Read `graphify-out/GRAPH_REPORT.md` before reading source files or broad search.
3. Compare the graph commit to `git rev-parse HEAD`; run `graphify update .` if stale before relying on graph evidence.
4. Query the graph:

```bash
graphify query "How should loop budget guards integrate with Loop Contracts, token budgets, action admission, maturity reports, workflow state, and no-overclaim gates?" --budget 3000
```

5. Read these files before editing:
   - `docs/build-briefs/loop-budget-guard-integration.json`
   - `docs/research/loop-engineering-adlc-strategy-review.md`
   - `docs/specs/loop-system-maturity-audit.md`
   - `docs/specs/token-budgets.md`
   - `docs/specs/pre-turn-check.md`
   - `docs/specs/cost-reporting.md`
   - `docs/schemas/token-budget.schema.json`
   - `docs/schemas/loop-contract.schema.json`
   - `docs/schemas/loop-action.schema.json`
   - `docs/schemas/loop-maturity-report.schema.json`
   - `docs/schemas/workflow-state.schema.json`
   - `scripts/adlc_runtime/cli.py`
   - `scripts/adlc_runtime/metadata.py`
   - `tests/test_adlc_cli.sh`
   - `tests/test_adlc_contracts.sh`

Task order:

1. ADLC-LBG-001: Define Loop Budget Guard semantics.
2. ADLC-LBG-002: Extend loop budget schemas and fixtures.
3. ADLC-LBG-003: Add deterministic loop-budget-check CLI and MCP tool.
4. ADLC-LBG-004: Gate loop action admission and resume state with budget evidence.
5. ADLC-LBG-005: Make budget evidence part of loop maturity and self-autonomy no-overclaim.
6. ADLC-LBG-006: Wire budget guards into agents, skills, docs, and learning.
7. ADLC-LBG-VAL: Validate loop budget guard integration end to end.

Implementation constraints:

- Keep budget fields optional for legacy assisted_loop and deterministic tasks.
- Missing or unhealthy budget evidence must block self_autonomous claims.
- Healthy local budget evidence is necessary but not sufficient for self_autonomous maturity.
- Do not claim provider-billing enforcement, live kill-switch support, or global ADLC self-autonomy.
- Do not duplicate `docs/schemas/token-budget.schema.json` inside Loop Contract.
- Do not store raw prompts, API keys, bearer tokens, billing account IDs, or raw logs in budget evidence.
- Keep `scripts/adlc_runtime/cli.py` changes factored into small helpers; broad runtime modularity cleanup belongs in the follow-on tech-debt pass.

Required validation before final:

```bash
git diff --check
python3 -m py_compile scripts/adlc.py scripts/adlc_runtime/__init__.py scripts/adlc_runtime/metadata.py scripts/adlc_runtime/cli.py scripts/validate_learning_entry.py
bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/loop-budget-guard-integration.json --json
bin/adlc emit-work-items --target linear --build-brief docs/build-briefs/loop-budget-guard-integration.json --dry-run --require-ready --json
bin/adlc validate-artifact --schema token-budget --input tests/fixtures/loop_maturity/token-budget-healthy.json --json
bin/adlc validate-artifact --schema loop-contract --input tests/fixtures/loop_maturity/budgeted-loop-contract.json --json
bin/adlc validate-artifact --schema loop-action --input tests/fixtures/loop_maturity/budgeted-loop-action.json --json
bin/adlc validate-artifact --schema loop-maturity-report --input tests/fixtures/loop_maturity/budgeted-maturity-report.json --json
bin/adlc loop-budget-check --token-budget tests/fixtures/loop_maturity/token-budget-healthy.json --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json
bin/adlc loop-budget-check --token-budget tests/fixtures/loop_maturity/token-budget-exhausted.json --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json
bin/adlc loop-action-validate --loop-contract tests/fixtures/loop_maturity/budgeted-loop-contract.json --action tests/fixtures/loop_maturity/budgeted-loop-action.json --state tests/fixtures/loop_maturity/workflow-state-budget-progress.json --token-budget tests/fixtures/loop_maturity/token-budget-healthy.json --json
bin/adlc loop-maturity-audit --loop-contract tests/fixtures/loop_maturity/budgeted-loop-contract.json --workflow WORKFLOW.dot --state tests/fixtures/loop_maturity/workflow-state-budget-progress.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --test-results tests/fixtures/loop_maturity/test-results-complete-required.json --action tests/fixtures/loop_maturity/budgeted-loop-action.json --token-budget tests/fixtures/loop_maturity/token-budget-healthy.json --json
tests/test_adlc_contracts.sh
tests/test_adlc_cli.sh
tests/backtest/run_backtest.sh
graphify update .
graphify query "How does ADLC bind Loop Contracts to token budget guards, action admission, maturity reports, workflow state, and self-autonomy no-overclaim?" --budget 3000
```

Run smoke only if the local runtime adapter and credentials are available:

```bash
SMOKE=1 tests/smoke/run_smoke.sh
```

If smoke cannot run, report the exact blocker and rerun path. Do not broaden scope to fix unrelated smoke environment issues.

Final response must include:

- changed files grouped by ADLC-LBG task
- exact validation commands and results
- final maturity verdict and budget_status behavior
- Graphify update/query result
- smoke result or exact blocker
- unsupported states that remain
- follow-on tech-debt cleanup targets

Do not mark the goal complete if validation is skipped, if generated files are unintentionally dirty, or if the closeout claims provider billing enforcement, live kill-switch support, or global self-autonomy.
```
