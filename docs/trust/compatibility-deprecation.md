# Compatibility and deprecation

The canonical public surface is one `adlc` skill with eleven commands and three loops. The low-level `bin/adlc` CLI remains available during the 0.x beta window as an advanced compatibility interface.

Legacy peer skills and agents remain as internal source evidence. Default installation does not expose them. Known generated legacy files migrate only with ownership or exact-byte proof; changed or unknown files are preserved and block destructive migration. `execute-trade` and legacy `ship-content` are explicitly outside the default public product.

Deprecations require an owner, replacement, dated migration guide, evidence that active consumers have moved, and a removal gate. No source deletion is authorized merely because default installation changed. See the [legacy migration guide](https://github.com/bigeasyfreeman/adlc/blob/v0.9.2/docs/migration/legacy-surface-migration.md) and [ledger](https://github.com/bigeasyfreeman/adlc/blob/v0.9.2/docs/migration/legacy-surface-ledger.json).

Schema and public-command compatibility follow semantic versioning once releases begin. Breaking 0.x changes must still carry explicit migration notes and verifier updates.

`doc_honesty_section`: Repository-local evidence cannot enumerate unknown private consumers or forks.

`no_overclaim`: Absence from default installation is not evidence that a legacy source can be deleted.

`limitations`: External consumers must declare themselves before ADLC can test their migration.
