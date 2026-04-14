# Stage Invocation Notes

Every smoke stage sources `tests/smoke/stages/_invoke.sh` and `tests/smoke/stages/_validate.sh`.

`_invoke.sh` is a runtime dispatcher. It reads `ADLC_RUNTIME` (default `claude`), sources the matching adapter under `tests/smoke/adapters/`, and forwards `preflight` / `invoke_agent` without inlining runtime-specific flags.

Each adapter is responsible for:

- creating a temporary `HOME`
- isolating runtime settings or config state
- reading the checked-in agent markdown and passing it as the system prompt or runtime-equivalent developer instructions
- enforcing the explicit `--tools` grant list
- enabling CLI-side schema enforcement only when the runtime supports it
- capturing raw stdout and stderr separately

`_validate.sh` then enforces the stage output contract with `jq empty` plus JSON Schema validation.

Current stage mapping:

- `run_triage.sh` -> `agents/triage.md` with no tools
- `run_spec_to_tests.sh` -> `agents/test-author.md` with `Read,Write,Bash`
- `run_coder.sh` -> `agents/coder.md` with `Read,Write,Edit,Bash,Glob,Grep`
- `run_test_strength.sh` -> `agents/test-strength-auditor.md` with `Read,Bash`
- `run_council.sh` -> `agents/plan-reviewer.md` with `Read,Glob,Grep`

`tests/smoke/run_smoke.sh` recreates `tests/smoke/artifacts/workspace/` at the start of each stage. It snapshots only the state that the pipeline explicitly passes forward: generated tests from `spec_to_tests`, code edits from `coder`, and the audit report from `test_strength`. Triage and council run against a read-only workspace copy and fail if they mutate it.
