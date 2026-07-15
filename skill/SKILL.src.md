---
name: adlc
description: Run the provider-neutral ADLC skill loop for shaping, building, fixing, reviewing, hardening, shipping, inspecting, resuming, diagnosing, and learning from software work.
---

# ADLC

Use ADLC as an evidence-driven engineering loop. Read the target repository's instructions, load bounded project context once, and execute only the selected command contract.

## Start every command

1. Run `python3 skill/scripts/context.py --workspace <repo> --target <path> --command <command>`.
2. Inspect warnings, conflicts, missing decisions, hashes, and excerpt limits before acting.
3. Load exactly one command reference: the manifest's `selected_reference`.
4. Refuse execution if its `reference_status` is not `available`.
5. For Build, Fix, or Review, load the loop contract named by that command reference.
6. Load an optional internal pack register only when the selected command reference declares it applicable: `reference/register-security.md`, `reference/register-release.md`, `reference/register-integrations.md`, or `reference/register-engineering.md`.
7. Treat the register entry as the migrated contract. Legacy `skills/` and `agents/` files are source evidence, not peer public skills and not default context.

The bounded manifest and one command reference are the default context. Do not preload every command, provider adapter, or legacy document.

## Route commands

Prefer an explicit command. Route an ambiguous request, including “Make this repository better,” to Shape without mutation.

| Command | Reference |
| --- | --- |
| `/adlc init` | `skill/reference/command-init.md` |
| `/adlc shape` | `skill/reference/command-shape.md` |
| `/adlc build` | `skill/reference/command-build.md` |
| `/adlc fix` | `skill/reference/command-fix.md` |
| `/adlc review` | `skill/reference/command-review.md` |
| `/adlc harden` | `skill/reference/command-harden.md` |
| `/adlc ship` | `skill/reference/command-ship.md` |
| `/adlc status` | `skill/reference/command-status.md` |
| `/adlc resume` | `skill/reference/command-resume.md` |
| `/adlc doctor` | `skill/reference/command-doctor.md` |
| `/adlc learn` | `skill/reference/command-learn.md` |

## Apply universal rules

- Follow the target repository's highest-precedence applicable instructions. Surface conflicts instead of silently choosing.
- Keep the core contract provider-neutral. Provider adapters may translate it but may not redefine command semantics.
- Never overwrite target instruction files or unmanaged ADLC files. Initialization creates only absent ADLC-owned files and refuses collisions atomically.
- Require human approval before irreversible, privileged, destructive, publishing, merge, release, or external communication actions.
- Separate observation from mutation. Review, Status, and Doctor are read-only unless the user explicitly selects a later mutation command.
- Preserve user work, declared scope, and phase boundaries. Do not broaden authority from a terminal condition such as “finish.”
- Tie completion claims to evidence: changed paths, commands run, verifier results, and unresolved blockers.
- Prefer deterministic scripts for mechanical discovery and validation. Keep judgment and tradeoffs explicit.
- Treat missing context as a recorded missing decision, not permission to invent policy.
- Never route to the retained `execute-trade` domain skill or expose the legacy `ship-content` skill. Trading is outside the ADLC product; shipping uses the bounded `command-ship.md` contract.

## Report honestly

State what the evidence establishes and what it does not. A passing local contract does not prove live provider invocation. It does not prove a complete ADLC loop. It does not establish general availability, cross-provider parity, or production fitness unless the corresponding downstream gates have passed.

For this migration, the production claim is limited to: ready for downstream provider compilation.
