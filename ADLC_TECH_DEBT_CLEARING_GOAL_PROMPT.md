# ADLC Tech Debt Clearing Goal Prompt

Use this with `/goal`:

```text
Clear the ADLC entropy-control tech debt identified in TECH_DEBT_AUDIT.md. Work in /Users/eric/adlc. The objective is subtractive: keep the scalable AI primitives, but remove fake safety, universal ceremony, and non-executable gates.

Start by reading graphify-out/GRAPH_REPORT.md, then TECH_DEBT_AUDIT.md. Use Graphify for code relationship discovery where helpful. Do not broaden scope beyond the audit findings.

Implement the following in order:

1. Make applicability the single source of truth for overlay gates. Security, observability, test-strength, release/rollback, paved-road, and slop gates must run only when the task/change surface activates them. Inactive overlays should be omitted or explicit no-ops, not boilerplate obligations.

2. Fix workflow/docs drift. Update README.md, WORKFLOW.md, WORKFLOW.dot, platform/AGENTS.md, and related agent/skill docs so they no longer say security or slop gates run on every change. The workflow should show conditional skip/no-op paths driven by applicability.

3. Resolve the stop-slop fake executable problem. Either implement a real repo-owned command such as bin/adlc slop-gate, or mark the current stop-slop skill as advisory/spec-only and remove it from executable workflow paths. Prefer the smallest implementation that can be tested. Do not add a complex evaluator if a no-op/spec split is the safer interim fix.

4. Align readiness with documented behavior. scripts/adlc.py should enforce slop_quality_gate only for explicit generated-output surfaces. Code-only, docs-only, lint-only, and build-validation-only tasks must pass without slop gate boilerplate. Generated-output work missing a required gate must fail readiness with a clear reason.

5. Reduce schema and prompt boilerplate. Remove unconditional slop_quality_gate placeholders from planner/codegen prompts. If schema requirements force anti-slop or compatibility boilerplate onto trivial tasks, make the fields conditional or allow compact structured not_applicable entries. Preserve backward compatibility for existing build briefs.

6. Tighten slop gate semantics. Separate deterministic code checks from open-ended AI-output/content evals. Avoid broad stylistic bans, TODO/FIXME hard-fails, or project-specific brand checks in ADLC core unless scoped by path/config.

7. Add tests that prove both sides of the gate: generated-output work without slop gate fails; generated-output work with a valid gate passes; code-only/build-validation-only/docs-only work without slop gate passes; workflow command references are executable or explicitly spec-only; existing fixtures remain compatible.

8. Keep the fix small. Do not introduce new councils, new large schemas, new dashboards, or new agent roles unless directly required by the audit. Prefer deleting universal language and adding deterministic guards over adding process.

Validation required before final:
- bash tests/test_adlc_contracts.sh
- bash tests/test_setup.sh
- bash tests/backtest/run_backtest.sh
- python3 -m py_compile scripts/adlc.py
- bash -n tests/test_adlc_contracts.sh tests/test_setup.sh tests/backtest/run_backtest.sh tests/smoke/run_smoke.sh
- bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/xia-adlc-remediation.json --json
- bin/adlc emit-work-items --target linear --build-brief docs/build-briefs/xia-adlc-remediation.json --dry-run --json
- git diff --check
- graphify update .

Final response must summarize changed files, which audit findings were closed, validation results, and any intentionally deferred items. Do not claim full safety coverage unless tests prove it.
```
