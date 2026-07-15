# Provider setup

ADLC compiles one canonical skill into provider-specific discovery layouts.

| Provider target | Install surface | Lifecycle claim |
|---|---|---|
| Claude Code | `.claude/skills/adlc/` plus instructions | transactional install, update, rollback, uninstall |
| Codex | `.agents/skills/adlc/` plus instructions | transactional install, update, rollback, uninstall |
| Cursor | one `adlc.mdc` rule plus bounded references | compatibility ownership and drift refusal |
| Antigravity | one `adlc` skill | compatibility ownership and drift refusal |
| Factory | one canonical ADLC instruction document | compatibility ownership and drift refusal |

Use `adlc-skill` for Claude Code and Codex. Use `setup.sh` only for the dated 0.x compatibility path. An existing unmanaged canonical path or changed managed path blocks update and remains intact.

Provider discovery, invocation, behavior, hooks, and end-to-end loop execution are separate evidence dimensions. A successful install cannot upgrade another dimension. See the [generated support matrix](../trust/support-matrix.md).

`doc_honesty_section`: This page describes emitted layouts and lifecycle boundaries.

`no_overclaim`: It does not claim every provider discovers or follows the skill.

`limitations`: Exact provider behavior is version-specific and may change outside ADLC.
