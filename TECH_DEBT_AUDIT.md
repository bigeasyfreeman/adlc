# Tech Debt Audit - ADLC Cleanup Hardening Closeout

Generated: 2026-06-08
Method: FastRuby tech-debt skill adapted for ADLC's Python/shell/Markdown stack, Graphify orientation, and ADLC's own runtime validation.
Scope: Cleanup hardening slice for execution-backed Loop Contract evidence, deterministic runtime packaging, CLI/MCP metadata, and runtime modularization.

## Executive Summary

- The highest-risk cleanup findings from the prior audit are now materially handled: Loop Contract required tests can be execution-backed, target installs get a deterministic ADLC runtime wrapper, runtime dependencies are declared, the dead `loop-maturity-audit --build-brief` flag is removed, and `scripts/adlc.py` is now a stable entrypoint rather than the runtime body.
- ADLC's truthful operating state remains **assisted loop**. That is still correct. The framework now has stronger evidence gates, but full self-autonomy remains a per-workflow score claim.
- The main remaining risk is depth, not absence: `scripts/adlc_runtime/cli.py` is still large, readiness logic is still dense, and maturity dimensions other than test selection still rely on declaration-shaped evidence.
- The deterministic validation suite passed end to end after this cleanup: CLI 58/58, contract checks 351/351, backtest 126/126, setup 119/119, Python compile, shell syntax, health check, loop artifact validation, and `git diff --check`.

## Adapted Health Score

| Category | Score | Evidence |
| --- | ---: | --- |
| Security hygiene | 18/20 | Secret-like examples remain docs/fixtures oriented; no new credential surface was added. |
| Dependencies | 16/20 | `pyproject.toml:1` declares runtime and optional audit/PDF deps; no lockfile yet. |
| Coverage | 13/20 | Contract/backtest/setup coverage expanded, but no measured Python or shell coverage report exists. |
| Complexity | 14/20 | `scripts/adlc.py:1` is now a thin entrypoint and metadata moved to `scripts/adlc_runtime/metadata.py:1`; `cli.py` remains large. |
| Maintainability | 16/20 | CLI/MCP descriptions share metadata, setup installs a runtime wrapper, and Graphify output is ignored; readiness remains concentrated. |
| Total | 77/100 | Stronger productionization posture, with remaining work around modularity, coverage, and evidence fidelity. |

## Resolved Or Improved

| Prior Finding | Status | Evidence |
| --- | --- | --- |
| TD-001 install/runtime gap | RESOLVED | `setup.sh:50` installs `.adlc/bin/adlc`; `tests/test_setup.sh:101` proves the wrapper exists and runs `health-check`. |
| TD-002 tag-only required tests | RESOLVED | `docs/schemas/loop-test-result.schema.json:1`, `scripts/adlc_runtime/cli.py:1816`, and `tests/test_adlc_cli.sh:76` add execution-backed required-test evidence. |
| TD-003 maturity over-credit | RESOLVED | `scripts/adlc_runtime/cli.py:2091` caps tag-only test selection at score 2; `tests/test_adlc_cli.sh:82` locks the behavior. |
| TD-005 monolithic public CLI | PARTIAL | `scripts/adlc.py:1` is a stable wrapper and `scripts/adlc_runtime/metadata.py:43` centralizes command metadata. `scripts/adlc_runtime/cli.py` still needs deeper module splits. |
| TD-006 dependency hygiene | RESOLVED | `pyproject.toml:1` declares `jsonschema` plus optional PDF/audit extras; `scripts/adlc_runtime/cli.py:737` exposes `health-check`. |
| TD-008 CLI/MCP drift | PARTIAL | `scripts/adlc_runtime/metadata.py:43` drives shared command descriptions and MCP names; argparse/MCP argument schemas are still not fully generated from one spec. |
| TD-009 dead future flag | RESOLVED | `loop-maturity-audit --help` now exposes `--test-results`, not `--build-brief`; `tests/test_adlc_cli.sh:84` verifies it. |
| TD-013 complexity tooling gap | PARTIAL | Optional audit deps are declared in `pyproject.toml:14`; no CI command runs them yet. |
| TD-015 graph output policy | RESOLVED | `.gitignore:30` ignores `graphify-out/` as local analysis cache. |

## Remaining Findings

| ID | Category | Severity | Effort | Description | Recommendation |
| --- | --- | --- | --- | --- | --- |
| TD-R1 | Runtime modularity | Medium | L | `scripts/adlc_runtime/cli.py` still owns workflow parsing, schema validation, readiness, compound context, emitters, loop maturity, MCP dispatch, and CLI parsing. | Split next into `schemas.py`, `workflow.py`, `readiness.py`, `compound.py`, `loop_contracts.py`, `emitters.py`, and `mcp.py` with behavior-preserving tests. |
| TD-R2 | Evidence fidelity | Medium | M | Test selection now uses execution evidence, but `self_grading_risk`, `feedback_fidelity`, and some control/failure scores still trust declaration-shaped state more than validated evidence artifacts. | Require existing evidence refs and typed evidence classes before allowing score 3 in those dimensions. |
| TD-R3 | Readiness rule concentration | Medium | M | Readiness checks remain concentrated in one runtime path with repeated policy knowledge also present in schema/docs/tests. | Introduce a readiness rule registry returning normalized issue objects and use it from emitters and tests. |
| TD-R4 | Coverage measurement | Medium | M | Shell contract tests are broad, but there is no measured coverage report for Python runtime branches or shell setup paths. | Add `coverage.py` for Python and a documented shell coverage posture or bats/shellspec equivalent. |
| TD-R5 | Packaging completeness | Low | M | Target repos get an `ADLC_ROOT` wrapper, not a vendored or packaged standalone CLI. That is deterministic but still coupled to the source checkout path. | Decide between source-checkout wrapper, console-script package, or vendored runtime mode before advertising ADLC as independently installable. |
| TD-R6 | Optional audit execution | Low | S | Optional tools are declared but not wired into a single non-blocking local audit command. | Extend `bin/adlc health-check --include-optional` or add `bin/adlc audit-runtime` to run configured tools when installed. |

## Validation Performed

- `python3 -m py_compile scripts/adlc.py scripts/adlc_runtime/__init__.py scripts/adlc_runtime/metadata.py scripts/adlc_runtime/cli.py scripts/md2pdf.py scripts/validate_learning_entry.py` - passed.
- `bash -n setup.sh tests/test_adlc_cli.sh tests/test_adlc_contracts.sh tests/test_setup.sh tests/backtest/run_backtest.sh tests/smoke/run_smoke.sh tests/artifact_contract/evaluate.sh` - passed.
- `jq empty docs/schemas/loop-test-result.schema.json docs/schemas/test-author-output.schema.json tests/fixtures/loop_maturity/*.json` - passed.
- `bin/adlc health-check --json` - passed with `status=pass`.
- `bin/adlc validate-artifact --schema loop-test-result --input tests/fixtures/loop_maturity/test-results-complete-required.json --json` - valid.
- `bin/adlc loop-test-selection --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --require-test-results tests/fixtures/loop_maturity/test-results-complete-required.json --json` - passed with all required tests executed.
- `bash tests/test_adlc_cli.sh` - passed, 58/58.
- `bash tests/test_adlc_contracts.sh` - passed, 351/351.
- `bash tests/backtest/run_backtest.sh` - passed, 126/126.
- `bash tests/test_setup.sh` - passed, 119/119.
- `git diff --check` - passed.

## Things That Look Bad But Are Actually Fine

- ADLC still reports `assisted_loop` by default. That is the correct no-overclaim posture until a specific workflow earns robust scores with objective evidence.
- `.adlc/bin/adlc` points to the source checkout through `ADLC_ROOT`. That is acceptable for this slice because setup tests prove it works and it avoids copying runtime source into target repos.
- `graphify-out/` is ignored. Graphify is analysis cache here, not committed product evidence.
- The CLI runtime still being large is residual debt, not a regression. The public entrypoint and metadata split create the safe boundary for the next modularization pass.

## Bottom Line

The cleanup slice moved ADLC from prompt-heavy framework wiring toward a more productionized deterministic runtime. The biggest gaming path, tag-only Loop Contract required-test coverage, now has a strict execution-backed mode and maturity cap. The next high-leverage cleanup is deeper runtime modularity plus evidence validation for the remaining maturity dimensions.
