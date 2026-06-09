# Tech Debt Audit - ADLC Loop-Budget Productionization

Generated: 2026-06-09
Mode: repeat-run update of the living ADLC tech-debt audit.
Method: local `tech-debt-audit` skill, plus the FastRuby and ksimback tech-debt skill rubrics applied to ADLC's Python, shell, JSON schema, Markdown, and Graphify workflow.
Scope: current loop-engineering and loop-budget cleanup slice, not a whole-framework rewrite.

## Executive Summary

- RESOLVED: CLI and MCP resume handling no longer duplicate the `next_action` shape; both now call one helper that includes loop progress, control state, escalation context, and `budget_status`.
- RESOLVED: the common loop path where `budget_guard.token_budget_ref` comes from the Loop Contract is now covered for CLI action validation, CLI maturity audit, MCP action validation, and MCP maturity audit.
- ADLC's no-overclaim posture remains correct: default framework maturity is still `assisted_loop`, and `self_autonomous` remains a per-workflow evidence claim.
- FastRuby's Rails-specific tooling does not directly apply, but its useful health dimensions do: security, dependency freshness, coverage, complexity/churn, and maintainability.
- ksimback's audit shape does apply directly: cited findings, churn/largest-file orientation, no rewrite recommendations, and a required "looks bad but fine" section.
- Optional Python audit tools are declared but not installed in this environment, so this pass records the gap rather than installing global tools.
- Graphify was refreshed with `graphify update . --force`, but the local graph cache still contains stale `scripts/adlc.py` function nodes; full extraction is blocked locally by missing LLM API keys.
- The highest remaining debt is still the size and responsibility density of `scripts/adlc_runtime/cli.py`.
- Validation passed after cleanup: Python compile, CLI 81/81, contracts 360/360, backtest 126/126, `health-check --include-optional`, and scoped `git diff --check`.

## Architectural Mental Model

ADLC is a deterministic control layer around LLM-driven development work. The repo's public surface is a small CLI wrapper plus installable agents, skills, schemas, specs, and shell tests. The runtime path is concentrated in `scripts/adlc_runtime/cli.py`, which validates schemas, advances workflow state, emits work items, evaluates Loop Contracts, runs loop budget checks, and exposes the same operations through MCP.

The current loop-engineering strategy is integrated in theory and partially enforced in runtime: Loop Contracts define allowed tools, required tests, progress/control evidence, maturity claims, and optional budget guards. `loop-action-validate`, `loop-budget-check`, and `loop-maturity-audit` turn those concepts into deterministic gates. ADLC should keep this as an assisted-loop framework by default until a specific workflow has healthy budget evidence and robust independent verification.

## Adapted Health Score

| Category | Score | Evidence |
| --- | ---: | --- |
| Security hygiene | 18/20 | The budget path passes aggregate refs and explicitly avoids provider secrets or billing account IDs; no new credential surface was added. |
| Dependencies | 15/20 | Runtime deps and optional audit deps are declared in `pyproject.toml:6` and `pyproject.toml:14`; optional audit tools are not installed locally. |
| Coverage | 15/20 | CLI and MCP loop-budget paths are now covered in `tests/test_adlc_cli.sh:92`, `tests/test_adlc_cli.sh:99`, `tests/test_adlc_cli.sh:179`, and `tests/test_adlc_cli.sh:182`; measured Python coverage is still absent. |
| Complexity | 14/20 | `scripts/adlc_runtime/cli.py:1` remains a large multi-responsibility runtime module, though the resume payload drift point was reduced. |
| Maintainability | 17/20 | Shared helper usage at `scripts/adlc_runtime/cli.py:767` now keeps CLI and MCP resume payloads aligned. |
| Total | 79/100 | Productionization improved for loop-budget guard behavior, with modularity and optional audit execution still open. |

## Findings Table

| ID | Category | File:Line | Severity | Effort | Description | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| TD-101 | Consistency rot | `scripts/adlc_runtime/cli.py:559` | Medium | S | CLI resume had a hand-built `next_action` payload that could drift from MCP resume. | RESOLVED: call `resume_next_action_payload` from the CLI path. |
| TD-102 | Consistency rot | `scripts/adlc_runtime/cli.py:2781` | Medium | S | MCP resume had the same hand-built `next_action` payload, creating a second place to remember `budget_status`. | RESOLVED: call `resume_next_action_payload` from the MCP path. |
| TD-103 | Contract coverage | `scripts/adlc_runtime/cli.py:2067` | Medium | S | Contract-declared `budget_guard.token_budget_ref` was implemented but under-tested compared with explicit `--token-budget`. | RESOLVED: add CLI and MCP regression coverage for implicit contract budget refs. |
| TD-104 | Runtime modularity | `scripts/adlc_runtime/cli.py:1` | Medium | L | One file still owns workflow parsing, schema validation, readiness, compound context, emitters, loop maturity, MCP dispatch, and CLI parsing. | Split by behavior-preserving slices after this commit: loop contracts, emitters, readiness, MCP, and schema helpers. |
| TD-105 | Evidence fidelity | `scripts/adlc_runtime/cli.py:2385` | Medium | M | `self_grading_risk` can still score robustly from declaration-shaped independent-truth evidence rather than a validated evidence artifact. | Require typed evidence refs before score 3 in non-test maturity dimensions. |
| TD-106 | Coverage measurement | `tests/test_adlc_cli.sh:1` | Medium | M | Shell tests cover behavior broadly, but there is no measured Python branch coverage for the runtime module. | Add `coverage.py` around Python runtime paths or document why shell-contract coverage is the accepted measure. |
| TD-107 | Optional audit tooling | `pyproject.toml:14` | Low | S | Optional audit dependencies are declared but local health reports them missing, so FastRuby-style complexity/security/dead-code tools cannot run yet. | Add a non-global `python3 -m pip install -e '.[audit]'` setup path or `bin/adlc audit-runtime` command. |
| TD-108 | Packaging completeness | `README.md:58` | Low | M | Target repos use a source-checkout wrapper, which is deterministic but still tied to the checkout path. | Decide whether production install means source-wrapper, console script package, or vendored runtime. |
| TD-109 | Graph cache freshness | `scripts/adlc.py:1` | Low | S | Local Graphify query output still shows old `scripts/adlc.py` function symbols even though the file is now a thin wrapper. | Run a full Graphify extraction with an API key or purge/rebuild the analysis cache outside the product diff. |

## Top 5 If Nothing Else

1. TD-104: split `scripts/adlc_runtime/cli.py` only after this loop-budget slice lands, using behavior-preserving module moves and the current CLI/MCP tests as the safety net.
2. TD-105: require validated evidence artifacts for `self_grading_risk`, `feedback_fidelity`, and failure/control dimensions before allowing score 3.
3. TD-106: add measured Python runtime coverage so future loop-engineering changes can use coverage/churn/complexity signals instead of shell pass counts alone.
4. TD-107: make optional audit execution reproducible through a repo-local command, not global tool installation.
5. TD-108: clarify the production install target before advertising standalone production readiness.

## Quick Wins

- [x] Centralize resume `next_action` construction for CLI and MCP.
- [x] Add explicit tests for contract-level `budget_guard.token_budget_ref` resolution.
- [ ] Add a repo-local optional audit command that runs `ruff`, `pip-audit`, `vulture`, `mypy`, and `radon` when installed.
- [ ] Add one runtime coverage command for the Python CLI paths.
- [ ] Rebuild Graphify from scratch once an LLM-backed full extraction is available.

## Resolved In This Pass

- `command_resume_workflow` now delegates `next_action` construction to `resume_next_action_payload` at `scripts/adlc_runtime/cli.py:566`.
- MCP `adlc_resume_workflow` now delegates to the same helper at `scripts/adlc_runtime/cli.py:2787`.
- The shared helper carries `budget_status` in one place at `scripts/adlc_runtime/cli.py:780`.
- CLI action validation proves implicit contract budget refs at `tests/test_adlc_cli.sh:92`.
- CLI maturity audit proves implicit contract budget refs at `tests/test_adlc_cli.sh:99`.
- MCP action validation proves implicit contract budget refs at `tests/test_adlc_cli.sh:179`.
- MCP maturity audit proves implicit contract budget refs at `tests/test_adlc_cli.sh:182`.

## Validation Performed

- `graphify update . --force` - passed, but `graphify query` still reports stale old `scripts/adlc.py` symbols.
- `graphify extract . --no-cluster --out .` - blocked locally because no LLM API key is configured.
- `python3 -m py_compile scripts/adlc.py scripts/adlc_runtime/__init__.py scripts/adlc_runtime/metadata.py scripts/adlc_runtime/cli.py scripts/validate_learning_entry.py` - passed.
- `bash tests/test_adlc_cli.sh` - passed, 81/81.
- `bash tests/test_adlc_contracts.sh` - passed, 360/360.
- `bash tests/backtest/run_backtest.sh` - passed, 126/126.
- `bin/adlc health-check --include-optional --json` - required checks passed, optional audit/PDF checks warned because local tools are missing.
- `git diff --check -- scripts/adlc_runtime/cli.py tests/test_adlc_cli.sh` - passed.

## Things That Look Bad But Are Actually Fine

- ADLC still reports `assisted_loop` by default. That is correct until a concrete workflow earns self-autonomous status with healthy budget evidence and robust verification.
- `loop-action-validate` accepts a contract-level token budget ref without `--token-budget`. That is intentional because loops should carry compact refs instead of repeated prompt/runtime arguments.
- `graphify-out/` changed during local graph refresh but remains analysis cache, not a product artifact to commit.
- The FastRuby skill names Rails tools that do not fit ADLC. The useful part is its health scoring model, not its Ruby-specific commands.

## Open Questions

- Should ADLC add `bin/adlc audit-runtime` now, or keep optional audit execution as a documented local setup step until after runtime modularization?
- Should `budget_guard.token_budget_ref` resolution prefer contract-relative paths before repo-root paths for reusable contracts copied across repos?
