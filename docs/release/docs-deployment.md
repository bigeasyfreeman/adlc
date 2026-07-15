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

GitHub Pages must be enabled once for the repository before a release begins,
with Actions as its build source:

```bash
gh api repos/$OWNER/$REPO/pages --jq .build_type
# Expected: workflow

# Repository-admin recovery when the site does not exist yet:
gh api --method POST repos/$OWNER/$REPO/pages -f build_type=workflow
```

The release workflow checks this prerequisite before it prepares or reuses a
candidate. This check must happen before PyPI publication because successful
registry uploads are immutable even if a later Pages deployment fails.

The v0.9.2 release includes a one-time `docs_only` recovery path for the
post-publication truth correction captured in its release evidence. The job
requires the original packet and approval record, verifies an exact hard-coded
digest of the corrected docs source, and cannot write to PyPI or recreate the
GitHub Release. Any later docs change requires a new reviewed change and human
deployment approval rather than reusing this recovery digest.

Pull requests and `v*` tag pushes run `.github/workflows/docs.yml` for build and validation only; that workflow has no manual dispatch or Pages write permission. Publication is available only through `.github/workflows/release.yml` after the immutable tag prepares a release packet. A human `release_publication` approval record must name the exact packet path and SHA-256, `approval_packet_run_id` must identify the reviewed preparation-only run, `confirm_publication` must be set, and the protected `github-pages` environment must approve. The Pages job reuses the exact approved candidate, revalidates the packet-bound record and artifact digests, checks tag/version agreement, builds the exact tagged sources, runs the rendered and viewport contracts, and deploys that artifact directly.

## Rollback

1. Identify the last known-good Pages deployment and matching release tag.
2. Prepare a new release packet from that exact immutable source and record the recovery rationale; never reuse or move a release tag.
3. Bind a fresh human approval record to the exact recovery packet and approve the `github-pages` environment deployment through the release workflow.
4. Verify the canonical URL, version banner, search index, and first-Fix page.
5. Preserve the failed deployment and reason; do not rewrite its tag.

GitHub retains deployment history, so the prior Pages artifact remains the rollback source. If Pages itself is unavailable, repository Markdown at the matching tag remains the authoritative documentation.

`doc_honesty_section`: A successful static deployment proves site publication, not ADLC runtime availability.

`no_overclaim`: The workflow cannot prove external caches have refreshed or that every assistive technology behaves identically.

`limitations`: Initial documentation is English-only, statically hosted, and analytics-free.
