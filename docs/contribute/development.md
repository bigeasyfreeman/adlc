# Development

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'jsonschema>=4,<5'
bin/adlc health-check --json
bin/adlc ci --json
```

Read `graphify-out/GRAPH_REPORT.md` before source exploration when the graph is present. After code changes, run `graphify update .`. Keep each PR to one coherent contract, capture its expected failing verifier, run the targeted gate and canonical CI, run `git diff --check`, and keep credentials, local paths, generated installs, `.adlc/` state, and process-only artifacts out of the diff.

Python changes should pass `ruff check scripts tests` and the supported Python 3.9/3.13 hosted matrix. Documentation changes should pass public hygiene, link, docs-contract, and applicable acceptance gates.

See [CONTRIBUTING.md](https://github.com/bigeasyfreeman/adlc/blob/v0.1.0/CONTRIBUTING.md) for the complete repository contract at this documentation version.
