# ADLC Skill-and-Loop Product Surface Decisions

Status: accepted for implementation  
Decision source: resolved `ADLC-MIG-002` decision contract and companion strategy  
Revalidation point: before any public beta support graduation

## ADR-ADLC-001 — One canonical public skill

**Decision:** Expose one public `adlc` skill with eleven command references. Existing skills remain internal capability packs, deterministic kernel interfaces, compatibility surfaces, or explicitly gated deprecation candidates.

**Why:** Users should reach Build, Fix, or Review outcomes before learning internal machinery. One source also enables deterministic provider compilation.

**Reversal path:** Version the product contract, prove a concrete user need that cannot be routed by bounded references, add behavioral holdouts, and obtain product-owner approval before exposing another public skill.

## ADR-ADLC-002 — ADLC owns only bounded `.adlc` context

**Decision:** Target-repository instructions remain authoritative. ADLC-owned context is limited to `.adlc/PROJECT.md`, `.adlc/ENGINEERING.md`, and `.adlc/config.json`.

**Why:** Overwriting root instructions would violate repository ownership and make precedence ambiguous.

**Reversal path:** Introduce a versioned context contract, migration tooling, collision and rollback tests, and explicit target-repository consent.

## ADR-ADLC-003 — Python is the distribution path

**Decision:** Package the CLI and bundled assets as a Python distribution installable with pipx or uv tool. Preserve `setup.sh` during the compatibility window.

**Why:** The deterministic runtime is Python and package metadata already exists; a second runtime would create release and rollback divergence.

**Reversal path:** Demonstrate an unsupported deployment requirement, reproduce the lifecycle matrix in the replacement distribution, and publish a tested migration and rollback path.

## ADR-ADLC-004 — Provider claims are multidimensional

**Decision:** Record `unsupported`, `experimental`, `beta`, or `supported` independently for installation, discovery, invocation, Build, Fix, Review, hooks, and release-artifact behavior.

**Why:** Generated files and fixture success do not prove native selection, safe tool behavior, recovery, or released-artifact conformance.

**Reversal path:** Only a stronger evidence taxonomy may replace these states; migration must preserve every existing evidence reference and limitation.

## ADR-ADLC-005 — Telemetry is off by default

**Decision:** Evidence and metrics remain local unless the operator separately opts in. Credentials and sensitive repository content never enter public traces.

**Why:** Product validation does not justify surveillance or widening the credential boundary.

**Reversal path:** Add a privacy-reviewed, versioned consent contract, data minimization and deletion controls, local preview, opt-out verification, and explicit human approval.

## ADR-ADLC-006 — Preserve a compatibility window

**Decision:** Existing low-level commands, manifest skills, installed agents, schema aliases, and stored workflow state remain supported through the 0.x beta window. No surface is removed before ADLC-MIG-008 behavioral proof and ADLC-MIG-009 consumer/replacement evidence.

**Why:** A facade migration must not silently break existing users or erase internal capabilities before the replacement is proved.

**Reversal path:** Record consumers, replacement, migration guidance, validation evidence, dated notice, rollback, and maintainer approval for each surface.

## Approval and honesty

These decisions were selected by the resolved product-owner contract in the Build Brief and are implementation inputs, not behavioral evidence.

`doc_honesty_section`: The ADRs authorize architecture direction only.  
`no_overclaim`: They do not prove that packaging, provider conformance, compatibility, or telemetry controls have shipped.  
`limitations`: Any reversal must preserve deterministic safety and truthful migration evidence.
