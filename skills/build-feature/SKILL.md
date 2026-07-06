---
name: build-feature
description: "Orchestration skill: chains the full ADLC Build Loop. PRD → Brief → Council → Scaffold → Codegen → LDD → TDD → Council → PR. Use when implementing a new feature end-to-end."
---

# Build Feature (Orchestration)

## Overview

This orchestration skill chains core ADLC skills into the complete Build Loop sequence. It teaches the agent WHEN to use each skill and HOW they connect.

## When to Use

- User wants to implement a new feature end-to-end
- A structured PRD or issue needs to become shipped code
- Any work that goes through the full ADLC pipeline

## The Sequence

```
Step 1: PRD (fork — interactive)
Step 2: Build Brief + repo conventions + product vocabulary + scalable-code primitives
Step 2a: Operator divergence gate when manifest/task evidence activates it
Step 3: Volatility-first review packet + Eval Council (HEAVY, convention-aware decomposition check)  ←── revision loop (max 3)
Step 4: Scaffold (if needed)
Step 5: Codegen Context Assembly (repo conventions become hard constraints)
Step 6: Per-task execution (parallel where independent):
  6a: LDD gate + structural convention scan
  6b: Verifier-led TDD mode by task class
  6c: Implementation
Step 7: Definition of Done verification, including repo-convention items
Step 8: Eval Council (HEAVY — post-execution, includes Convention Auditor)  ←── revision loop (max 3)
Step 8a: Teach-first gate for active taste/operator-judgment dimensions
Step 9: Stop Slop + PR hygiene scan
Step 9a: Operator comprehension gate before engineer review for medium+ blast radius
Step 10: Create PR from default branch unless a dependency is documented
```

Convention flow map:

| Step | Convention Contract |
|------|---------------------|
| 2 | Ingest target repo `repo_conventions` and `product_vocabulary` before decomposition. |
| 2a | `operator-divergence-gate` requires options/prototypes/reaction only when `applicability_manifest.operator_surface` or task evidence activates divergence; otherwise it records `not_applicable`. |
| 3 | `volatility-review` renders volatile decisions first, then council allocates proportional depth and records which volatile decisions were examined. |
| 5 | Context assembly inlines conventions as hard constraints for each task package. |
| 6a | LDD runs structural convention scans; file size and line count are not split criteria. |
| 7 | Definition of Done includes active repo-convention checks and explicit waivers. |
| 8 | Post-execution council audits implementation against the same convention evidence. |
| 8a | `teach-first-gate` requires ratified criteria for taste or operator-judgment dimensions, citing the versioned criteria store when available. |
| 9 | PR hygiene scans for ADLC artifacts, banned vocabulary, local paths, removed gates, and undocumented stacked bases. |
| 9a | `operator-comprehension-gate` requires a passed quiz or recorded delegation for medium+ blast-radius changes before engineer review. |
| 10 | PR creation uses the default branch unless a real code dependency is documented. |

### Step 1: PRD Agent
- **Skill:** `prd-generation`
- **Mode:** Interactive (fork — user participates)
- **Input:** Raw feature request, issue, or idea
- **Output:** Structured PRD with: problem statement, success metrics, out of scope, constraints/antipatterns, dependencies, personas
- **Gate:** PRD must have no ambiguous language. All sections populated.

### Step 2: Build Brief
- **Skill:** `build-brief` (ADLC Build Brief Agent)
- **Input:** Structured PRD + codebase context
- **Output:** Technical design with top-level `repo_conventions`, top-level `product_vocabulary`, and per-task: acceptance criteria (G/W/T), `task_classification`, `change_surface`, `verification_spec`, `applicability_manifest`, construct-map refs, paved-road refs, intent refs, production invariant coverage, reuse analysis, antipatterns, Definition of Done
- **Storage:** Write the canonical Build Brief outside the target repo at the path returned by `bin/adlc process-artifact-path --target-repo <target-repo> --task <brief-or-task-id> --artifact-type build-brief --filename build-brief.json --json`.
- **Includes:** `paved-road-registry`, `reuse-analysis`, `security-review` only when the security overlay is active, and `observability-contract` only when the observability overlay is active
- **Repo conventions:** Run `bin/adlc repo-conventions --workspace <target-repo> --json` against the target repo. If CLAUDE.md, AGENTS.md, or CONTRIBUTING.md exists, the Build Brief `repo_conventions.rules[]` MUST list every extracted rule with a verification predicate. If those files exist but contain no normative rules, the brief MUST carry `status: files_present_but_no_normative_rules` and record the files read in `sources[]`. If no convention files exist, the brief MUST carry `status: none_found` and `explicit_empty_marker: no_conventions_found`; absence is invalid.
- **Vocabulary firewall:** The brief MUST carry `product_vocabulary.mappings[]` and one shared `product_vocabulary.banned_tokens[]` list for internal ticket IDs, codenames, stack labels, and phase names that must not reach public identifiers, schemas, filenames, tests, comments, CLI output, PR titles, or PR bodies.
- **Clarity gate:** The brief MUST carry an epistemic ledger of KNOWN, ASSUMED, and UNKNOWN claims. Run a blindspot pass covering prior art, removals and potholes, conventions docs, missing domain vocabulary, adjacent systems, and contract-surface inventory. Every blindspot item maps to a ledger entry.
- **Interview loop:** Run `bin/adlc clarity-gate --build-brief <brief> --json` before finalization. If any architecture-affecting UNKNOWN remains or an `ask-user` ledger entry exists, interactive harnesses ask pending questions; headless harnesses emit pending questions and block instead of inventing defaults.
- **Operator divergence:** Run `bin/adlc operator-divergence-gate --build-brief <brief> --json` before finalization. If divergence is active, store the options ladder, prototype refs, and operator reaction in ADLC process-artifact storage. Rejected-option reasons become user-ratified KNOWN ledger entries.
- **Compatibility evidence:** When a task touches a published or versioned surface, run `bin/adlc contract-surface-inventory` and `bin/adlc compatibility-evidence`. The `compatibility_contract` must name the surface and verification predicate, and validation tasks must cite `compatibility_evidence_refs`.

### Step 3: Eval Council — Post-Brief
- **Skill:** `eval-council` (HEAVY — manifest-aware core personas + active overlays, 3 rounds)
- **Personas:** Core = Skeptic, Executioner, First Principles; overlays = Architect, Operator, Security Auditor when active
- **Pre-check:** Static checks must pass before council tokens are spent; active personas come from the applicability manifest
- **Volatility packet:** Render `bin/adlc volatility-review --build-brief <brief> --json` before council review. The canonical Build Brief section order stays unchanged; the packet orders likely-to-change tasks and decisions first for operator/council attention.
- **Storage:** Store the council report in ADLC process artifact storage with `artifact-type eval`; reference it from the brief and work items instead of adding it to the target repo.
- **Verdicts:** APPROVED → Step 4. REVISION REQUIRED → back to Step 2 (max 3 loops). BLOCKED → escalate.

### Step 4: Architecture Scaffolding
- **Skill:** `architecture-pattern` (only when new modules/interfaces needed)
- **Output:** Port interfaces, implementation targets, domain types, wiring/registration, directory structure, implementation guide

### Step 5: Codegen Context Assembly
- **Skill:** `codegen-context`
- **Output:** Per-task self-contained prompt with: mission, G/W/T, verification_spec, tests, files (inlined), repo_conventions rules, product_vocabulary banned tokens, construct-map refs, paved-road refs, intent contract, production invariant coverage, reference implementations, reusable functions, schema, "What NOT to Do", security contract, observability contract, lint config, scale considerations, integration wiring, anti-slop rules, verification commands, DoD checklist, applicability_manifest
- **Parallel dispatch:** Independent tasks get separate prompts for simultaneous execution

### Step 6: Execution (per task)
- **6a — LDD:** `ldd-enforcement` — lint gate. Must pass before TDD.
- **6b — TDD:** `tdd-enforcement` — use the verifier mode that matches the task class: feature = behavior tests, bugfix = reproducer-first, build_validation = failing command-first, lint_cleanup = lint/fmt-first. No code until the chosen verifier fails for the right reason.
- **6c — Implementation:** Agent builds per codegen context. Includes security tests and observability tests only when those overlays are active.

### Step 7: Definition of Done
- **Skill:** `definition-of-done`
- **Core baseline plus active overlays must pass.** Failed active checks block pipeline.

### Step 8: Eval Council — Post-Execution
- **Skill:** `eval-council` (HEAVY — reviewing implementation against brief)
- **Focus:** Did the implementation match the design? Did it stay on the paved road or justify departure? Are construct relationships, verifiers, and production invariants satisfied? Are active overlays satisfied? Is observability complete where active?
- **Storage:** Store the post-execution council report in ADLC process artifact storage with `artifact-type eval`.
- **Verdicts:** APPROVED → Step 9. REVISION REQUIRED → back to Step 6 (max 3 loops).

### Step 8a: Teach-First Calibration
- **Skill:** `teach` plus `slop-judge` criteria reuse
- **Gate:** Run `bin/adlc teach-first-gate --build-brief <brief> --criteria-store <store> --json` before approving an active taste or operator-judgment surface.
- **Behavior:** If criteria already exist, cite the criteria ID. If not, emit a teach packet with key concepts, at least 3 concrete criteria, and a good-versus-bad contrast pair; the operator edits/ratifies it before the gate opens.

### Step 9: Stop Slop + PR Hygiene
- **Skill:** `stop-slop` (content mode on PR description)
- **Threshold:** 35/50
- **Hygiene scan:** Run `bin/adlc pr-hygiene-scan --build-brief <brief> --title <title> --body <body> --base-branch <base> --default-branch <default> --json`. It fails on pipeline artifacts, banned internal tokens, absolute local paths, removed CI gates supplied to the scan, and undocumented stacked bases.

### Step 9a: Operator Comprehension
- **Gate:** Run `bin/adlc operator-comprehension-gate --build-brief <brief> --quiz <quiz> --json` before `engineer_review` when blast radius is medium or high.
- **Behavior:** The quiz must cover behavior change, blast radius, and failure modes using concrete diff/task terms. A failed quiz emits remediation and blocks until retake passes; explicit delegation records as `delegated`, not `passed`, in the run report.

### Step 10: Create PR
- **Diff contract:** PR diff contains product code, tests, and user-facing docs only. Pipeline artifacts - Build Briefs, eval/council reports, tech-debt audits, closeout or validation scripts, and goal prompts - live in ADLC process artifact storage keyed by target repo and task, not in the target repo diff.
- **Base policy:** Cut from the target repo default branch. A non-default base is allowed only when the brief documents a genuine code dependency on an unmerged PR; dependent PRs remain drafts and name the dependency in the body.
- **Language contract:** PR title/body use product language from `product_vocabulary`; internal codenames, ticket IDs, stack labels, and phase names are banned.
- **Output:** PR with: summary, active overlay summaries, DoD checklist, council verdict, test results, risk tier, PR hygiene scan result
- **Merge policy:** Routine=auto-merge, Elevated=human review, Critical=human sign-off

## Failure Handling

| Failure | Response |
|---------|---------|
| PRD ambiguous after 5 turns | Escalate to human |
| Brief fails council 3 times | Escalate with council feedback |
| Execution fails DoD | Revision loop (max 3), then escalate |
| Post-execution council rejects 3 times | Escalate with full context |
