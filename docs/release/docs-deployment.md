# Documentation deployment and rollback

The site is a generated artifact of repository Markdown. Do not commit `site/`.

## Local preview

```bash
python3 -m pip install '.[docs]'
mkdocs serve --strict
```

Because `site_url` includes `/adlc/`, MkDocs serves that subpath and redirects `/` to it. Open the URL reported by the server (`http://127.0.0.1:8000/adlc/`) and review a narrow and wide viewport. Before publication, run:

```bash
mkdocs build --strict
python3 tests/check_built_docs.py site
python3 -m playwright install chromium
python3 tests/check_docs_viewports.py site docs-preview
RELEASE_TAG=vX.Y.Z
python3 scripts/check_docs_release.py --tag "$RELEASE_TAG" --json
```

## Deployment

Pull requests and `v*` tag pushes build and validate without deployment. Publication requires a manually dispatched workflow naming an existing GitHub Release and setting `confirm_publication`; the workflow refuses a ref that is not the exact tag commit or a tag that differs from `project.version` in `pyproject.toml` or `extra.adlc_version` in `mkdocs.yml`. It then uploads the generated Pages artifact and deploys through the `github-pages` environment. Configure required reviewers on that environment as a second approval boundary.

## Rollback

1. Identify the last known-good Pages deployment and matching release tag.
2. Re-run the Docs workflow with that exact tag from its source commit.
3. Approve the `github-pages` environment deployment.
4. Verify the canonical URL, version banner, search index, and first-Fix page.
5. Preserve the failed deployment and reason; do not rewrite its tag.

GitHub retains deployment history, so the prior Pages artifact remains the rollback source. If Pages itself is unavailable, repository Markdown at the matching tag remains the authoritative documentation.

`doc_honesty_section`: A successful static deployment proves site publication, not ADLC runtime availability.

`no_overclaim`: The workflow cannot prove external caches have refreshed or that every assistive technology behaves identically.

`limitations`: Initial documentation is English-only, statically hosted, and analytics-free.
