# Provider Conformance Evidence

ADLC currently publishes one evidence-bounded live result: the Codex CLI
`0.137.0` with GPT-5.4 and the installed-skill Fix fixture is `beta` at source
commit `ea1f2d193bc2a7a64961ae3298ff7e12f9ae8165`. This is not a Build, Review,
Claude, cross-model, GA, or universal provider claim.

A provider becomes eligible for a public support claim only after the live
smoke harness produces a schema-valid
`provider-conformance-report` with:

- `overall: pass` and every stage passing;
- `evidence_status: current_conformance`;
- a clean source tree at the recorded commit;
- runtime, model, adapter path and digest, fixture digest, auth path, and run
  timestamps recorded; and
- the canonical `bin/adlc ci --json` gate passing at the same commit.

Smoke output under `tests/smoke/artifacts/` is ephemeral. After reviewing a
successful clean-tree report for secrets and local data, copy it here using a
name such as `YYYY-MM-DD-claude.json`, validate it again, and commit it with the
adapter claim it supports:

```bash
bin/adlc validate-artifact \
  --schema provider-conformance-report \
  --input tests/smoke/artifacts/smoke_report.json \
  --json
```

Candidate reports from dirty trees and failed reports are useful diagnostics,
but they do not establish provider support.

## Dimension and label policy

Provider evidence is never inherited across providers, models, harnesses,
versions, loops, source commits, or fixture digests. Each report records four
separate dimensions:

- `installation`: the canonical generated skill is present and digest-valid;
- `invocation`: the named provider actually launched and emitted a structured tool trace;
- `behavior`: trace, diff, verifier, state, and forbidden-mutation assertions passed;
- `end_to_end`: the named loop reached its honest terminal state.

The public table is generated from `*.report.json` files; labels are not authored in configuration:

```bash
python3 tests/provider_conformance/matrix.py --json
```

One clean passing run across all four dimensions is `experimental`. Three or
more clean passing runs within the exact source-and-fixture cohort, with no
failed run in that cohort, are `beta`. A missing credential, failed run, or
incomplete dimension is listed under `excluded` with its evidence and never
appears as a passing configuration. The initial `4739d5d` cohort is retained
as a 1/3 diagnostic result with two trace-grading failures; the fixed
`ea1f2d1` cohort is 3/3. Claude remains visibly blocked on missing explicit
credentials. This task does not issue a GA or universal provider claim.

## Proof lanes

The credential-free PR lane is deterministic:

```bash
python3 -m pytest tests/skill_behavior tests/provider_conformance -q
bash tests/acceptance/run_public_fix_loop.sh
```

It includes at least twelve pressure traces plus a disposable real product-code Fix with red-before-green, interrupt/resume idempotency, an independent completion audit, and a schema-valid report. Its provider-invocation dimension remains `not_run`.

The live Codex lane is explicit and bounded. Planning makes no provider call:

```bash
python3 tests/provider_conformance/run_live.py --plan --model gpt-5.4 --repetitions 3 --json
```

Execution requires the authenticated Codex CLI session and the literal `--execute` flag. Each repetition creates a disposable repo, installs the canonical skill, invokes the named provider/model for a Fix, and independently grades the JSONL tool trace, changed paths, product code, and red/green verifier. Raw evidence is path- and secret-redacted before it reaches a publication directory.

Claude Code's isolated smoke lane still requires `ANTHROPIC_API_KEY` or `ADLC_SMOKE_SETTINGS`. Missing credentials are a blocked lane, not an unsupported test pass.
