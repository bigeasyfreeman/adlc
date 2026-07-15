# Release and rollback runbook

## Prepare

1. Start from a clean commit whose package and documentation versions equal the intended tag.
2. Verify that GitHub Pages already exists and is configured for Actions
   deployments: `gh api repos/$OWNER/$REPO/pages --jq .build_type` must print
   `workflow`. For a new site, a repository administrator enables it once with
   `gh api --method POST repos/$OWNER/$REPO/pages -f build_type=workflow`.
   Do this before publishing to PyPI so a missing Pages site cannot leave the
   release only partially deployed.
3. Run `bin/adlc ci --json` and the release architecture tests.
4. Run `python3 scripts/release.py prepare --tag fixture-v0.9.2 --repository test --verify-reproducible --rehearse-rollback --json` for the non-publishing rehearsal.
5. Review `release-out/<tag>/release-approval-packet.json`, both artifact digests, every gate record, the evidence-derived support rows, unsigned local provenance, and `rollback-manifest.json`.
6. Independently validate the packet with `bin/adlc validate-artifact --schema release-approval-packet --input <packet> --json`.
7. After the release-contract repair and its hosted checks are merged, create the
   immutable `vX.Y.Z` candidate tag. A tag push runs the read-only docs build; it
   does not dispatch the protected release workflow.
8. From a clean checkout of that exact tag, set specific, distinct executor and
   auditor identity/session values in `ADLC_EXECUTOR_ID`,
   `ADLC_EXECUTOR_SESSION_ID`, `ADLC_AUDITOR_ID`, and
   `ADLC_AUDITOR_SESSION_ID`, then run `python3 scripts/release.py
   validate-go-live --tag "$ADLC_RELEASE_TAG" --clean-checkout
   --independent-auditor --json`. The command rebuilds the ignored candidate,
   installs its exact wheel in clean Python 3.9 and 3.13 environments, exercises
   Codex and Claude installation fixtures, runs three credentialed Codex Fix
   conformance attempts, replays release-critical evidence, and leaves the
   tagged checkout clean. It emits promotable copies of
   `docs/evidence/releases/go-live-validation.json` and
   `docs/evidence/releases/completion-audit.json` below
   `release-out/<tag>/evidence-export/`; promote only the independently reviewed
   pair into the repository.

Preparation is idempotent for the same source commit: it recreates the ignored output directory, fixes build timestamps to the commit epoch, and fails if the two artifact sets differ.

## Approve and publish

After MIG-VAL returns a passing or explicitly scoped-beta recommendation for the
existing immutable tag, dispatch `.github/workflows/release.yml` with
`confirm_publication=false` first. The release owner reviews the resulting
packet and records its exact SHA-256 in a schema-valid `release_publication`
approval record. A second dispatch supplies that record through
`approval_record_json`, supplies the successful preparation-only run ID through
`approval_packet_run_id`, and enables confirmation. The publication run downloads
and reuses those exact packet-approved bytes; it does not regenerate the packet.
Every publishing job calls
`scripts/release.py publish` to validate the record's packet path and digest
before it can reach the protected `pypi`, `github-release`, or `github-pages`
environment action.

The PyPI job uses OIDC trusted publishing and GitHub artifact attestation. The GitHub Release job uploads only the prepared bytes. The Pages job delegates to the existing tagged documentation workflow. Launch communications are outside this workflow and remain separately approval-bound.

## Roll back

If package publication fails before GitHub Release or Pages, leave the successful registry state unchanged, record the partial state, and do not reuse the tag. If a published candidate is defective:

1. identify the last known-good immutable artifact and its approval packet;
2. stop wider launch communication and mark the affected release clearly;
3. reinstall the known-good artifact in a clean environment and rerun its doctor and support gates;
4. redeploy documentation from the matching release tag using the protected Pages workflow;
5. publish corrective notes only after the same human approval boundary.

PyPI files are immutable and cannot be overwritten. A correction therefore uses a new version; rollback means restoring operators to known-good bytes and documentation, not rewriting history. For the first public release, no older public package exists, so rehearsal proves candidate restoration from the local immutable test index and records that limitation.

`doc_honesty_section`: This runbook defines preparation and recovery actions; it is not evidence that external publication or rollback has occurred.

`no_overclaim`: Local reproducibility, installation, and restore checks do not prove registry uptime, signed public provenance, or successful production rollback.

`limitations`: Initial automation covers this GitHub repository, one PyPI project, and one Pages site.
