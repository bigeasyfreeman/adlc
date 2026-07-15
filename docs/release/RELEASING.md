# Release and rollback runbook

## Prepare

1. Start from a clean commit whose package and documentation versions equal the intended tag.
2. Run `bin/adlc ci --json` and the release architecture tests.
3. Run `python3 scripts/release.py prepare --tag fixture-v0.9.0 --repository test --verify-reproducible --rehearse-rollback --json` for the non-publishing rehearsal.
4. Review `release-out/<tag>/release-approval-packet.json`, both artifact digests, every gate record, the evidence-derived support rows, unsigned local provenance, and `rollback-manifest.json`.
5. Independently validate the packet with `bin/adlc validate-artifact --schema release-approval-packet --input <packet> --json`.

Preparation is idempotent for the same source commit: it recreates the ignored output directory, fixes build timestamps to the commit epoch, and fails if the two artifact sets differ.

## Approve and publish

Create an immutable `vX.Y.Z` tag only after MIG-VAL returns a passing or explicitly scoped-beta recommendation. Dispatch `.github/workflows/release.yml` with `confirm_publication=false` first. The release owner must bind a human approval record to the exact packet and digests. A second dispatch with confirmation enabled still stops at the protected `pypi`, `github-release`, and `github-pages` environments until their reviewers approve.

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
