# Release process

MIG013 owns the automated release implementation. Until it lands, do not tag or publish from an ad hoc local build.

The release contract requires a clean checkout, canonical CI on supported Python versions, strict documentation build, replayable demo/benchmark evidence, reproducible source and wheel artifacts, dependency and secret scans, signed provenance where configured, staged publication, rollback rehearsal, release notes, and an explicit human approval before external publication.

Release claims must name the tag and artifact digest. A source-branch pass is candidate evidence, not released-artifact support. See [CHANGELOG.md](../../CHANGELOG.md) for user-facing changes and [SECURITY.md](../../SECURITY.md) for coordinated fixes.
