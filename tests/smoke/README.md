# Layer 2 Smoke Harness

Layer 2 is the opt-in ADLC smoke suite. Unlike `tests/backtest/`, it uses the real agent configs and a live runtime CLI session against a tiny toy repo. This suite is for nightly or manual verification of prompt behavior, schema interpretation, and end-to-end routing. It is not part of the per-commit contract suite.

## Prerequisites

- a supported runtime selected with `ADLC_RUNTIME` (`claude`, `codex`, `cursor`, `antigravity`, or `factory`)
- a model exported through `MODEL`
- `SMOKE=1` in the environment to authorize token spend
- runtime-specific auth:
  - `claude`: `ANTHROPIC_API_KEY` or `ADLC_SMOKE_SETTINGS`
  - `codex`: `OPENAI_API_KEY` or `ADLC_SMOKE_SETTINGS_CODEX`
  - `cursor`: `CURSOR_API_KEY`
  - `antigravity`: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
  - `factory`: `FACTORY_API_KEY`
- local Python 3 with `unittest`
- a supported mutation tool if you want the full `test_strength` stage to pass:
  - Python: `mutmut`
  - JavaScript / TypeScript: `stryker`
  - Rust: `cargo-mutants`

`claude` bare mode does not use OAuth or keychain auth. The Claude adapter only supports `ANTHROPIC_API_KEY` or an explicit `ADLC_SMOKE_SETTINGS` file with `apiKeyHelper`.

## Run

```bash
ADLC_RUNTIME=claude       ANTHROPIC_API_KEY=sk-... SMOKE=1 MODEL=claude-sonnet-4-6 bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=claude       ADLC_SMOKE_SETTINGS=~/path/to/settings.json SMOKE=1 MODEL=claude-sonnet-4-6 bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=codex        OPENAI_API_KEY=sk-... SMOKE=1 MODEL=gpt-5-codex bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=codex        ADLC_SMOKE_SETTINGS_CODEX=~/path/to/config.toml SMOKE=1 MODEL=gpt-5-codex bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=antigravity  GOOGLE_API_KEY=... SMOKE=1 MODEL=gemini-2.5-pro bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=cursor       CURSOR_API_KEY=... SMOKE=1 MODEL=cursor-default bash tests/smoke/run_smoke.sh
ADLC_RUNTIME=factory      FACTORY_API_KEY=... SMOKE=1 MODEL=factory-default bash tests/smoke/run_smoke.sh
```

The harness recreates `tests/smoke/artifacts/workspace/` at the start of every stage. Each stage invokes the checked-in agent markdown through `tests/smoke/stages/_invoke.sh`, which dispatches to a runtime adapter under `tests/smoke/adapters/`. Adapters isolate config state, enforce explicit tool grants, and enable CLI-side schema enforcement only when the selected runtime supports it. Triage and council receive a read-only workspace copy.

## Runtime Availability

Checked on April 13, 2026 in this workspace:

- `claude`: CLI installed; adapter has a live invocation path once `ANTHROPIC_API_KEY` or `ADLC_SMOKE_SETTINGS` is supplied
- `codex`: CLI installed; adapter has a live invocation path once `OPENAI_API_KEY` or `ADLC_SMOKE_SETTINGS_CODEX` is supplied
- `cursor`: CLI not installed here; adapter exits `77`
- `antigravity`: no `gemini` or `antigravity` CLI installed here; adapter exits `77`
- `factory`: CLI not installed here; adapter exits `77`

The stages run in this order:

1. `triage`
2. `spec_to_tests`
3. `coder`
4. `test_strength`
5. `council`

Each stage writes a log to `tests/smoke/artifacts/<stage>.log`. The final machine-readable summary is `tests/smoke/artifacts/smoke_report.json`.

## Cost

Budget for roughly `50000` tokens per full run. The real cost depends on how much the agents rewrite inside the toy repo and whether retries are needed.

## Interpreting `smoke_report.json`

- `overall: "pass"` means every stage executed, its assertion passed, and the harness completed end to end.
- `overall: "fail"` means a stage or its paired assertion failed. Check the matching `artifacts/<stage>.log` first.
- `overall: "skipped"` is used only when the harness is explicitly authorized with `SMOKE=1` but the selected runtime CLI is not installed, in which case the runner exits `77`.

Each stage entry records:

- `name`
- `ok`
- `artifact`
- `duration_ms`

## Cleanup

To clear prior run outputs without deleting the tracked `.gitkeep` file:

```bash
find tests/smoke/artifacts -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
```
