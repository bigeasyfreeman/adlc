# Contributing to ADLC

Thank you for helping make evidence-bound agent workflows easier to use and verify. Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Start

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'jsonschema>=4,<5'
bin/adlc health-check --json
bin/adlc ci --json
```

Read [development](docs/contribute/development.md), the current [documentation map](docs/index.md), and `graphify-out/GRAPH_REPORT.md` before source exploration when the graph exists.

## Change contract

### Target Repo Conventions

ADLC treats every target repository as a standards source. Any ADLC change that affects planning, decomposition, codegen, QA, review, or PR closeout must preserve the target repo convention contract:

- carry extracted `repo_conventions` into task context;
- run `convention-scan` against the final change;
- run `pr-hygiene-scan` before publication;
- record explicit waivers instead of silently omitting a rule.

- Keep one PR to one coherent behavior or contract change.
- Capture the expected failing verifier before implementation.
- Preserve target-repository instructions and vocabulary.
- Use one public `adlc` skill; route internal capabilities through bounded references and registers rather than adding default peer skills or agents.
- Update schemas, compatibility evidence, migration guidance, and tests when a public or persisted contract changes.
- Do not use file size or line count as a design or quality criterion.
- Keep ADLC planning, council, audit, prompt, and closeout artifacts out of target-repository diffs.

Authoring guidance is in [skill/reference authoring](docs/contribute/authoring.md) and [behavioral scenarios](docs/contribute/behavioral-scenarios.md).

## Verify

Run the narrow ticket verifier and then:

```bash
bin/adlc ci --json
git diff --check
```

Run `ruff check scripts tests` for Python changes. Run `graphify update .` after code changes. GitHub CI exercises the supported Python matrix. PRs must explain what changed, why, user impact, compatibility and rollback, checks run, and unresolved human decisions.

Do not commit credentials, developer-local paths, `.adlc/` runtime state, generated self-installs, or private traces.

## Security and governance

Report vulnerabilities privately through [SECURITY.md](SECURITY.md), never a public issue. See [GOVERNANCE.md](GOVERNANCE.md) for decision ownership and [CHANGELOG.md](CHANGELOG.md) for release-facing history.
