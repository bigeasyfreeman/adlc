# ADLC

[![CI](https://github.com/bigeasyfreeman/adlc/actions/workflows/ci.yml/badge.svg)](https://github.com/bigeasyfreeman/adlc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Run repeatable Build, Fix, and Review loops with your coding agent, with every completion claim tied to evidence.

ADLC gives an existing coding agent one public skill and a deterministic control plane for state, permissions, verification, approvals, recovery, and evidence. It does not replace the agent or silently merge, deploy, publish, or spend money.

## Install in 30 seconds

ADLC is currently an unreleased source beta. Clone the repository, install its package, then use the transactional lifecycle to install and diagnose one canonical skill:

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc
python3 -m pip install .
adlc-skill install --provider codex --target /path/to/your-repo
adlc-skill doctor --provider codex --target /path/to/your-repo
```

Use `claude` instead of `codex` for Claude Code. The package lifecycle (`install`, `doctor`, `update`, `rollback`, and `uninstall`) is the transactional path for those two providers. Cursor, Antigravity, and Factory are experimental compatibility targets without rollback claims. See [installation](docs/start/installation.md) for exact ownership and migration behavior.

## Run a five-minute Fix

In the target repository, ask the installed coding agent:

```text
/adlc fix the failing average calculation. Reproduce it first, make the smallest repair, run the affected tests, and stop with PR-ready evidence.
```

The expected sequence is red verifier → bounded repair → green verifier → independent review → `pr_ready`. To replay the repository’s deterministic version of that first success in an isolated temporary repository:

```bash
bash tests/acceptance/run_readme_quickstart.sh
```

That replay routes Fix through the installed public facade, then proves the deterministic kernel path. It does not invoke Codex or make a live-provider claim. The [First Fix guide](docs/start/first-fix.md) explains every stop state and artifact.

## Three evidence-bound loops

| Loop | Use it when | Honest terminal outcome |
|---|---|---|
| Build | Approved intent needs to become a bounded change. | A scoped diff and declared evidence are `pr_ready`, or the run names what blocked. |
| Fix | A defect can be reproduced. | Red-to-green defect proof and affected-suite evidence are `pr_ready`, or reproduction/verification remains blocked. |
| Review | A concrete change needs independent scrutiny. | Read-only findings and a verdict; remediation requires a separate Build or Fix invocation. |

Start with the [Build](docs/guides/build.md), [Fix](docs/guides/fix.md), or [Review](docs/guides/review.md) guide. Resume interrupted work without replaying completed effects with the [Resume guide](docs/guides/resume.md).

## Current provider evidence

<!-- BEGIN GENERATED SUPPORT MATRIX -->
| Provider | Provider version | Harness | Loop | Label | Dimensions | Runs | Evidence commit |
|---|---:|---|---|---|---|---:|---|
| Codex | 0.137.0 | codex-cli-installed-skill | Fix | beta | installation, invocation, behavior, end-to-end: pass | 3 | `4a629f313ee4` |
| Claude Code | 2.1.210 | claude-code-credential-preflight | Fix | — | invocation: blocked (`credentials_missing`); remaining dimensions: not run | 1 failed preflight | `ea1f2d193bc2` |
<!-- END GENERATED SUPPORT MATRIX -->

This block is checked against [`support-matrix.json`](docs/evidence/provider-conformance/support-matrix.json); edit the evidence, then run `python3 scripts/render_support_matrix.py`, rather than hand-editing claims. Labels apply only to the named provider, version, harness, model, loop, fixture, commit, and dimensions. See the [generated support matrix](docs/trust/support-matrix.md) for raw evidence links and limitations.

## How it works

```text
your intent
    │
    ▼
one `adlc` skill ──► Build / Fix / Review loop contract
    │                              │
    ▼                              ▼
coding-agent judgment       deterministic ADLC kernel
                             state · admission · tests
                             approvals · recovery · evidence
                                      │
                                      ▼
                         proved / blocked / awaiting human
```

The skill routes only the context needed for the selected command. The kernel owns deterministic truth and fails closed when approval, credentials, evidence, or compatibility proof is missing. Read [skills, loops, and kernel](docs/concepts/skills-loops-kernel.md) for the boundary.

## Safety and human approval

- Review, status, and doctor are read-only.
- Local mutation starts only inside an authorized Build or Fix boundary.
- External writes, publish, merge, release, deploy, destructive recovery, privileged access, and paid execution require explicit approval.
- Persisted effects carry idempotency evidence so resume does not intentionally replay completed work.
- Telemetry is off by default. Provider credentials and target-repository content stay under the operator’s provider and repository controls.
- `pr_ready` does not mean merged, deployed, adopted, secure, or generally available.

Read the [security and privacy boundary](docs/trust/security-privacy.md), [security policy](SECURITY.md), and [compatibility/deprecation policy](docs/trust/compatibility-deprecation.md).

## Proof, not promises

- [Provider conformance evidence](docs/evidence/provider-conformance/README.md)
- [Deterministic public Fix replay](tests/acceptance/run_public_fix_loop.sh)
- [Replayable invoice Fix demo and public benchmark](docs/trust/benchmark.md)
- [Legacy-surface migration ledger](docs/migration/legacy-surface-migration.md)
- [Canonical local verification](docs/contribute/development.md)

The public benchmark preserves three complete deterministic runs with red-before-green, interrupt/resume, one-file scope, and independent completion-audit evidence. It installs Codex but invokes no provider or model, so its token and provider-cost range is exactly zero and it does not change the live-provider support matrix. These proofs are scoped evidence, not proof of future behavior, market traction, compliance certification, GA readiness, or universal provider support.

## Documentation and community

- [Documentation home](docs/index.md)
- [Public command reference](docs/reference/public-commands.md)
- [Configuration](docs/reference/configuration.md)
- [Artifacts and schemas](docs/reference/artifacts-and-schemas.md)
- [Stop reasons](docs/reference/stop-reasons.md)
- [Contributing](CONTRIBUTING.md) and [governance](GOVERNANCE.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Changelog](CHANGELOG.md)
- [Migration guide](docs/migration/legacy-surface-migration.md) and [historical archive](docs/archive/README.md)

## Status and limitations

ADLC is an unreleased beta candidate. The source checkout, deterministic tests, exact Codex Fix configuration shown above, documentation-site build, and deterministic public benchmark have evidence; package publication, production docs deployment, secure release automation, and public launch remain gated work. Only released and tested configurations may graduate support labels.

`doc_honesty_section`: This page describes the current source product and links to its evidence; it is not a release artifact or adoption proof.

`no_overclaim`: ADLC does not claim GA, autonomous delivery, universal provider behavior, benchmark superiority, compliance certification, or production support.

`limitations`: Current live-provider evidence covers only the exact Codex Fix row above. Claude Code invocation is credential-blocked in the recorded run, and compatibility targets are not live-provider claims.

## License

MIT. See [LICENSE](LICENSE).
