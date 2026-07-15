# Release process

ADLC separates reversible preparation from external publication. From a clean candidate checkout, run:

```bash
python3 scripts/release.py prepare --tag fixture-v0.9.0 --repository test --verify-reproducible --rehearse-rollback --json
```

Preparation builds the source archive and wheel twice, compares their SHA-256 digests, installs from a local test index, runs release-critical gates, derives provider claims from checked-in conformance evidence, and rehearses restoration from immutable candidate bytes. It emits a schema-valid packet under ignored `release-out/`; every PyPI, GitHub Release, Pages, and launch action remains `pending_human_approval`.

For a real release, create the immutable `vX.Y.Z` tag only after go-live validation. Dispatch the release workflow first with publication confirmation off. A human release owner reviews the packet, artifact digests, provenance, scans, and rollback record, then binds a `release_publication` approval record to the exact packet SHA-256. Publication requires that record through `approval_record_json`, explicit workflow confirmation, and approval in each protected GitHub environment. Each publishing job revalidates the digest-bound record before any write. Long-lived PyPI credentials are not stored; the protected job uses trusted publishing.

Release claims must name the tag and artifact digest. A source-branch or fixture pass is candidate evidence, not released-artifact support. See the full [release and rollback runbook](../release/RELEASING.md), [CHANGELOG.md](https://github.com/bigeasyfreeman/adlc/blob/v0.9.0/CHANGELOG.md), and [SECURITY.md](https://github.com/bigeasyfreeman/adlc/blob/v0.9.0/SECURITY.md).

`doc_honesty_section`: This page documents an approval-bound release mechanism; it does not claim that a public release exists.

`no_overclaim`: A green preparation packet does not mean PyPI, GitHub, Pages, or launch publication succeeded.

`limitations`: The first release has no prior public package version to downgrade to, so local rehearsal restores the immutable candidate; protected workflow provenance replaces unsigned local provenance only during approved publication.
