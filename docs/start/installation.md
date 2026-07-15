# Installation

## Requirements

- Git
- Python 3.9 or newer
- `jsonschema>=4,<5`
- a target Git repository

## Source-beta install

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc
python3 -m pip install .
adlc-skill install --provider codex --target /path/to/your-repo
adlc-skill doctor --provider codex --target /path/to/your-repo
```

Replace `codex` with `claude` for Claude Code. Each target receives one public `adlc` skill and no public peer agents.

## Transactional package lifecycle

After the source install above or from an installed wheel:

```bash
adlc-skill install --provider codex --target /path/to/your-repo
adlc-skill doctor --provider codex --target /path/to/your-repo
adlc-skill update --provider codex --target /path/to/your-repo
adlc-skill rollback --provider codex --target /path/to/your-repo
```

Claude Code and Codex installs are manifest-owned, digest-verified, collision-safe, and reversible. `setup.sh` remains a dated 0.x compatibility wrapper, including for Cursor, Antigravity, and Factory; their ownership manifests refuse drift and unmanaged collisions, but they do not claim rollback.

## Existing files and migration

ADLC does not overwrite unknown provider instructions. Known legacy ADLC files are pruned only when ownership or exact bytes prove they are unchanged. Drift blocks migration and leaves the file intact. See the [dated migration guide](../migration/legacy-surface-migration.md).

## Troubleshooting

- Missing `jsonschema`: install `jsonschema>=4,<5` in the Python environment used by the wrapper.
- Collision or drift: keep the reported file, compare it with the generated bundle, then explicitly reconcile before update.
- Wrong provider target: uninstall with the same provider/target pair, then install the intended provider.
- Doctor passes but the skill is not invoked: bundle integrity and provider invocation are separate evidence dimensions; inspect [provider setup](../guides/provider-setup.md).

`doc_honesty_section`: A passing doctor proves installed bytes and runtime preflight, not provider invocation or loop behavior.

`no_overclaim`: Only Claude Code and Codex have transactional lifecycle claims.

`limitations`: The source-beta path depends on the retained checkout because the target wrapper resolves runtime assets there.
