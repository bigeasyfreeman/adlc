# TECH DEBT AUDIT - ADLC Entropy-Control Review

Generated: 2026-06-01
Scope: ADLC repository, with emphasis on whether the new scalable AI/code-quality primitives reduce AI slop without adding fake safety, unnecessary blockers, or hallucinated complexity.

## Executive Summary

- ADLC has the right core primitives: graph-backed context, concise intent contracts, paved-road registry, compatibility contracts, verifiability gates, slop quality gates, and feedback-loop hardening.
- The strongest design choice is that the new specs explicitly reject broad governance and trivial-work ceremony, especially in `docs/specs/scalable-ai-code-primitives.md:108` and `docs/specs/slop-eval-loop.md:157`.
- The main risk is not the primitives themselves. It is drift between conditional intent and universal workflow wiring.
- The current workflow still routes every build through `security`, `test_strength`, and `slop_gate` in the default loop, despite newer applicability rules saying these should be conditional. See `README.md:62`, `WORKFLOW.dot:96`, and `platform/AGENTS.md:26`.
- The slop gate is currently specified as a workflow command, but there is no repo or PATH executable for `stop-slop` or `slop-check`. That makes the gate look real before it is operational. See `WORKFLOW.md:128` and `skills/stop-slop/SKILL.md:430`.
- Readiness documentation promises generated-output slop-gate validation, but `scripts/adlc.py` does not enforce that rule today. This creates false confidence around `ready` status. See `docs/specs/emitter-contract.md:257` versus `scripts/adlc.py:816`.
- The schema still requires many protective fields for every task, which encourages boilerplate compliance and can recreate the old security-analysis overreach pattern. See `docs/schemas/build-brief.schema.json:210`.
- Tests are good at preserving fields and contracts, but several critical tests are string-presence checks rather than behavior checks. See `tests/test_adlc_contracts.sh:266`.
- The best cleanup is a subtraction pass: make overlay gates executable or explicitly no-op, centralize applicability, remove universal slop/security language, and add negative tests proving inactive gates stay inactive.

## Architectural Mental Model

ADLC is a Markdown-first agent lifecycle framework. The core loop is:

1. Research the codebase and constraints.
2. Plan tasks into a build brief.
3. Assemble implementation context.
4. Implement and review.
5. Validate, emit work items, and prepare PR/deployment artifacts.

The recent AI-scaling additions are meant to keep this loop stable as agent output increases:

- `graphify_context` should anchor code understanding in a graph of code relationships instead of free-form ecology narratives.
- `paved_road_refs` should push agents toward known frameworks, entrypoints, and build contracts.
- `intent_contract` and `compatibility_contract` should preserve product and engineering intent before code is generated.
- `verification_spec` and `slop_quality_gate` should keep output quality measurable.
- `feedback-loop` should convert accepted failures into future tests without letting rules accrete unchecked.

That direction is sound. The failure mode to watch is when a conditional primitive becomes mandatory process for every task, or when a documented gate is not actually executable.

## Findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| F001 | High | The default workflow still makes security and slop-like prevention gates structurally universal. This recreates the old "security analysis everywhere" failure pattern under new names. | `README.md:62` always lists `security -> qa -> test_strength -> slop_gate -> pr_prep`. `WORKFLOW.dot:96` routes `code_review -> security -> qa -> test_strength -> slop_gate`. `platform/AGENTS.md:26` says security review runs on every change. | Add explicit skip/no-op edges keyed by `applicability_manifest`. Update docs to say these overlays run only when their surface is active. |
| F002 | High | The slop gate is specified as a workflow command, but the command is not implemented in this repo or available on PATH. This is fake safety if followed literally. | `WORKFLOW.md:128` declares `stop-slop all --commit HEAD`. `skills/stop-slop/SKILL.md:430` documents `stop-slop check ...`. Local command discovery found no `stop-slop` or `slop-check`. | Either implement `bin/adlc slop-gate` and wire the skill to it, or mark the current skill as advisory until an executable exists. Add a CLI smoke test. |
| F003 | High | Readiness docs promise slop-gate enforcement for generated-output changes, but the readiness checker does not implement that rule. | `docs/specs/emitter-contract.md:257` says readiness checks `slop_quality_gate`. `scripts/adlc.py:816` through `scripts/adlc.py:853` checks core task fields but not generated-output slop-gate requirements. `scripts/adlc.py:954` only preserves the field if present. | Add a deterministic generated-output surface flag, then enforce `slop_quality_gate` only for that flag. Add a negative fixture where missing slop gate fails only for generated-output work. |
| F004 | Medium | The build-brief schema requires many protective fields for every task, which encourages invented boilerplate rather than real risk reduction. | `docs/schemas/build-brief.schema.json:210` through `docs/schemas/build-brief.schema.json:234` requires `anti_slop_rules`, `tech_debt_boundaries`, `compatibility_contract`, `verification_spec`, and other fields for all tasks. `docs/schemas/build-brief.schema.json:334` requires at least one `anti_slop_rules` item. | Keep core verifier and acceptance fields required. Move heavier controls behind explicit task classification or allow compact structured `not_applicable` objects. |
| F005 | Medium | The slop-eval spec is broader than the planner implementation, which can lead agents to apply quality gates to ordinary docs, code, and release tasks. | `docs/specs/slop-eval-loop.md:11` says the contract applies to code, prose, product outputs, and agent outputs. `docs/specs/slop-eval-loop.md:76` requires delivery guards before tickets, PRs, documents, and releases. The non-goals later narrow this at `docs/specs/slop-eval-loop.md:157`. | Rewrite the top of the spec around "generated-output surfaces". Keep deterministic code quality checks separate from open-ended AI-output evals. |
| F006 | Medium | The planner says inactive slop gates may be omitted, but its output shape still shows a top-level `slop_quality_gate` object. This nudges agents to fill it anyway. | `agents/planner.md:67` through `agents/planner.md:79` scopes slop gates to generated-output surfaces. `agents/planner.md:162` through `agents/planner.md:179` still includes `"slop_quality_gate": {}` in the output JSON example. | Make the JSON example omit the field by default or use `null` with an explicit "include only when active" note outside the JSON. |
| F007 | Medium | Codegen context always reserves a Slop Quality Gate section in prompts, even when inactive. This adds cognitive load and invites boilerplate. | `skills/codegen-context/SKILL.md:282` through `skills/codegen-context/SKILL.md:297` always includes section 9 for the slop quality gate, with a not-applicable reason when inactive. | Omit the section entirely when inactive. Put inactive overlays in a one-line applicability summary instead. |
| F008 | Medium | `stop-slop` rules are overbroad and stylistic enough to block legitimate work if made executable as-is. | `skills/stop-slop/SKILL.md:5` through `skills/stop-slop/SKILL.md:19` applies broad pre-commit triggers. `skills/stop-slop/SKILL.md:94` through `skills/stop-slop/SKILL.md:104` hard-fails placeholders and TODO/FIXME. `skills/stop-slop/SKILL.md:260` through `skills/stop-slop/SKILL.md:388` bans broad prose patterns. | Split deterministic code checks from stylistic content rubrics. Default to changed generated-output artifacts, not all source and docs. Make TODO/FIXME policy path-aware. |
| F009 | Medium | Slop metrics are strings, not executable validators, so a quality number can be named without being reproducible. | `docs/schemas/build-brief.schema.json:891` through `docs/schemas/build-brief.schema.json:897` defines metrics as free-form strings. `docs/schemas/build-brief.schema.json:1001` through `docs/schemas/build-brief.schema.json:1021` stores result scores, but not validator references. | Require each metric to name `metric_type` plus `validator_ref`, `judge_skill`, or `command`. Allow free-form text only in rationale fields. |
| F010 | Medium | Eval council still requires always-active personas and inactive overlay reasons, which can duplicate applicability work and increase token/process overhead. | `skills/eval-council/SKILL.md:13` through `skills/eval-council/SKILL.md:16` says core lenses always run and inactive overlays require reasons. `skills/eval-council/SKILL.md:38` through `skills/eval-council/SKILL.md:51` repeats that policy. | Make `applicability_manifest` the single suppression artifact. Eval council should consume it instead of asking each persona to restate not-applicable reasoning. |
| F011 | Medium | Tests prove new fields are preserved, but not that the gates make the right runtime decision. | `tests/test_adlc_contracts.sh:26` through `tests/test_adlc_contracts.sh:102` verifies field preservation and omission. `tests/test_adlc_contracts.sh:266` only greps that `WORKFLOW.md` contains the stop-slop command. | Add behavior tests: code-only work with no slop gate passes, generated-output work without a slop gate fails, and the workflow command resolves to an executable or explicit no-op. |
| F012 | Low | `stop-slop` references a brand foundation file that is not part of ADLC. That makes the skill feel project-specific while living in the core framework. | `skills/stop-slop/SKILL.md:398` through `skills/stop-slop/SKILL.md:407` references `charters/magnus-brand-foundation.md`. Repository file discovery found no matching charter file. | Move brand-specific checks to an overlay or mark the path as optional project-local configuration. |

## Top 5 If You Fix Nothing Else

1. Make `security`, `test_strength`, and `slop_gate` conditional in the workflow, not just in prose.
2. Implement or remove the literal `stop-slop` command from the workflow contract.
3. Add readiness enforcement for generated-output slop gates, scoped by an explicit surface flag.
4. Remove universal `slop_quality_gate` placeholders from planner and codegen prompts.
5. Add negative tests that prove inactive overlays do not block simple docs, lint, build-validation, and code-only changes.

## Quick Wins

- Change `platform/AGENTS.md:26` from "Security review runs ... on every change" to "Security review runs when the applicability manifest marks a security-relevant surface active."
- In `WORKFLOW.dot`, add conditional skip edges for inactive overlays.
- In `WORKFLOW.md`, replace `stop-slop all --commit HEAD` with either an implemented `bin/adlc slop-gate` command or an explicit "not executable yet" spec note.
- In `agents/planner.md`, remove the empty `slop_quality_gate` object from the base JSON skeleton.
- In `skills/codegen-context/SKILL.md`, render the slop gate section only when the work touches generated-output behavior.
- In `tests/test_adlc_contracts.sh`, add one generated-output negative fixture and one code-only positive fixture.

## Things That Look Bad But Are Actually Fine

- The scalable AI primitives spec itself is well scoped. It explicitly says not to add broad productivity metrics, heavyweight release governance, or paved-road evidence for trivial docs/lint/build validation at `docs/specs/scalable-ai-code-primitives.md:108` through `docs/specs/scalable-ai-code-primitives.md:118`.
- The same spec has removal criteria for prompts that invent graph claims, misuse paved roads, or mandate new governance, which is the right entropy-control mechanism. See `docs/specs/scalable-ai-code-primitives.md:119` through `docs/specs/scalable-ai-code-primitives.md:126`.
- The emitter correctly omits absent `slop_quality_gate` fields. See `scripts/adlc.py:954` through `scripts/adlc.py:955` and the omission test at `tests/test_adlc_contracts.sh:99`.
- The paved-road registry already contains the right anti-overreach language: no invented paved roads, no blocking justified abstractions, and no broad rewrites. See `skills/paved-road-registry/SKILL.md:92` through `skills/paved-road-registry/SKILL.md:99`.
- The feedback-loop skill has useful anti-accretion controls: candidate eval cases require approval, and rule growth is capped. See `skills/feedback-loop/SKILL.md:70` through `skills/feedback-loop/SKILL.md:75` and `skills/feedback-loop/SKILL.md:104` through `skills/feedback-loop/SKILL.md:115`.
- The current validation fixtures already suppress security and observability for build-validation-only work, which is the right pattern to extend to slop and other overlays. See `docs/build-briefs/xia-adlc-remediation.json:38` through `docs/build-briefs/xia-adlc-remediation.json:58`.

## Validation Performed

- `bash tests/test_adlc_contracts.sh` passed, 286/286 checks.
- `bash tests/test_setup.sh` passed, 108/108 checks.
- `bash tests/backtest/run_backtest.sh` passed, 126/126 checks.
- `python3 -m py_compile scripts/adlc.py` passed.
- `bash -n tests/test_adlc_contracts.sh tests/test_setup.sh tests/backtest/run_backtest.sh tests/smoke/run_smoke.sh` passed.
- `bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/xia-adlc-remediation.json --json` returned valid.
- `bin/adlc emit-work-items --target linear --build-brief docs/build-briefs/xia-adlc-remediation.json --dry-run --json` preserved omission of absent `slop_quality_gate`.
- `bash tests/smoke/run_smoke.sh` correctly refused token-spend smoke execution without `SMOKE=1`.
- `git diff --check` passed.
- Optional tools were unavailable in this environment: `ruff`, `pip-audit`, and `vulture`.

## Open Questions

- Should `slop_quality_gate` protect only generated AI/user-facing output, or also agent-authored internal artifacts such as PR descriptions and ticket bodies? The implementation should choose one default and encode it centrally.
- Should ADLC have a single `surface_classification` or `change_surface` field that controls all overlays, including security, observability, slop, release, rollback, and paved-road requirements?
- Should `stop-slop` become a real `bin/adlc` subcommand, or should slop evaluation remain a skill-level protocol until there is an executable benchmark runner?
- How strict should code-output slop rules be for tests, examples, and fixtures? Current broad TODO/FIXME and placeholder checks would likely create false positives.

## Bottom Line

The new primitives are worth keeping, but only if ADLC treats them as conditional engineering contracts instead of universal ritual.

The framework has already added many of the right guardrails in specs and skills. The next improvement should be subtractive: remove universal gate language, make applicability the single source of truth, and test both sides of the decision. That is how ADLC avoids repeating the earlier security-analysis failure under a newer label.
