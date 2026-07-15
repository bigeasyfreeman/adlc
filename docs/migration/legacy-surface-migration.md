# Legacy Surface Migration

Effective 2026-07-14, the default ADLC installation exposes one public skill, `adlc`, and no peer agents. The old `setup.sh` path remains a supported 0.x compatibility entrypoint. It removes byte-identical files only from known legacy ADLC paths, refuses locally changed legacy content, and records compatibility ownership manifests for canonical Cursor, Antigravity, and Factory outputs so reruns cannot silently overwrite drift or unmanaged collisions.

For new Claude Code or Codex installs, use:

```bash
adlc-skill install --provider <claude|codex> --target <repository>
```

Existing `setup.sh` callers may continue using `./setup.sh <platform> <repository>`. Then replace peer-skill invocation with `/adlc <command>`:

- PRD and goal-prompt entrypoints → `/adlc shape`
- build-feature → `/adlc build`
- systematic-debugging, fix-loop, and fix-bug → `/adlc fix`
- definition-of-done → `/adlc review` or the deterministic `bin/adlc completion-audit`
- security and quality peers → `/adlc harden`
- ship-content → `/adlc ship`; the old domain peer is not installed
- feedback and learning peers → `/adlc learn`

Specialized knowledge is applicability-loaded from the security, release, integration, or engineering registers under `skill/reference/`. Internal DAG agents remain runtime roles in `skills/manifest.json`; they are not installed as public provider agents.

Repository instruction files such as Codex `AGENTS.md` are not peer agents. A multi-provider install preserves that file only when the Codex transactional manifest and canonical Codex skill prove the coexisting installation; a standalone unknown `agents.md` blocks Antigravity migration.

`execute-trade` is outside the ADLC product and has no ADLC replacement. Its source is retained during 0.x because unknown external forks and private consumers cannot be proven from repository-local evidence.

Claude Code and Codex retain the transactional `adlc-skill` update and rollback lifecycle. Cursor, Antigravity, and Factory are experimental compatibility targets: ownership and drift are verified, but transactional rollback is not claimed for them.

No legacy source is authorized for deletion by MIG009. Removal still requires consumer evidence, a validated replacement, dated notice, rollback evidence, and maintainer approval.
