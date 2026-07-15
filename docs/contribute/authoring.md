# Skill and reference authoring

ADLC has one public skill: `skill/SKILL.src.md`. Add public behavior by extending its bounded router, an existing command reference, or a new applicability-loaded internal register. Do not create a new default-installed peer skill or agent without changing the product contract and migration ledger.

Every public command reference includes purpose, preconditions, example, procedure, outputs, stop states, side effects, approval points, compatibility map, troubleshooting, and honesty fields. Internal source skills under `skills/` remain implementation evidence selected through bounded registers; update `skills/manifest.json` when their ownership or mapping changes.

Compile and validate changes with the skill compiler and provider conformance tests. A compiled file match proves packaging, not provider behavior.
