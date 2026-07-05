---
name: feedback-loop
description: "Self-improving skill system. Captures diffs between agent output and human edits, distills patterns into rules, writes them back to skill files. Makes Build and Fix loops better over time."
---

# Feedback Loop

## Overview

The Feedback Loop makes both the Build Loop and Fix Loop better over time by learning from human edits and execution outcomes. Skills are not static — they evolve.

## The Pipeline

```
Human edits output → Diff captured → Classified by type + skill →
  Candidate eval case captured →
  Nightly: cases and diffs grouped →
    10+ similar edits? → Distill candidate rule →
      Validate against recent outputs →
        Write rule to skill file (version controlled) →
          Next execution uses updated skill
```

## Step 1: Diff Capture

After every human edit to agent output:

| Field | What to Record |
|-------|---------------|
| Original text | What the agent produced |
| Edited text | What the human changed it to |
| Diff | Unified diff format |
| Edit type | factual_correction, style_adjustment, scope_change, security_fix, structural_change, slop_removal |
| Skill source | Which skill produced the original output |
| Pipeline phase | Which phase produced the original |
| Timestamp | When the edit was made |

## Step 1b: Maintainer PR Comment Intake

Maintainer review comments are convention input, not just one-off fixes. After
every PR review cycle:

1. Read supplied review comments or run `gh pr view <id> --comments` / `gh api`
   against the PR issue comments and review-comment endpoints. Preserve the
   verbatim comment body, comment URL, author, PR number, and fetch command in
   the fixture or report provenance.
2. Classify each actionable comment as one of:
   - `target_repo_convention`: a target-repo rule that future Build Briefs must
     carry in `repo_conventions.rules[]`.
   - `product_vocabulary`: an internal term that must be mapped or banned in
     `product_vocabulary`.
   - `adlc_skill_rule`: a generic ADLC skill behavior that belongs in a skill
     file.
   - `one_off`: local feedback that should not become a rule.
3. For `target_repo_convention`, write a candidate rule with `source_ref`,
   `rule`, `verification_predicate`, `applies_to`, and sample changed files.
   The rule must be deterministic or cite the exact file review evidence needed.
4. For `product_vocabulary`, add a candidate `internal -> product` mapping or
   `banned_tokens[]` entry and test it with `bin/adlc pr-hygiene-scan`.
5. For `adlc_skill_rule`, route the candidate through the normal Pattern
   Distillation validation path before changing a skill.

Example: Interralis maintainer comments that enumerate multiple jobs in a Rust
file, ask for a directory module, or call out pure code mixed with filesystem or
subprocess side effects become target repo conventions. Separate feedback such
as "use the product term in the PR" becomes vocabulary input. Do not treat
thin-coordinator or size-gate boundaries as coming from those PR comments unless
the comment text explicitly says so.

### Acceptance Walkthrough: Interralis PR #225 And #226

Use the verbatim GitHub issue-comment bodies from these merged PRs as the
regression fixture for maintainer-comment intake. The review-comment endpoints
for both PRs returned empty arrays, and the approving review bodies were empty,
so the fixture source is the Aether- issue comments:

- PR #225 (`Add harness metadata source discovery`) issue comment identifies a
  file whose first module doc describes registry and discovery inventory, then
  calls out three jobs in one file: registry data/types, id inference, and a
  filesystem discovery walker. It also flags filesystem walking mixed with pure
  registry and normalization helpers.
- PR #226 (`Add LLM persona UX regression harness`) issue comment identifies a
  flat `persona_ux.rs` file containing catalog data, runner logic, an LLM
  subprocess driver, report file I/O, report explanation, and pure types/probes.
  It says the work should become a recursive directory module with pure files
  and documented impure subprocess/filesystem shells, preserving the pure core logic
  boundary the comment actually names.

Do not derive these rules from PR #225 or #226:

- Thin coordinators: this is supported by `CLAUDE.md` and later merge feedback,
  not by the two maintainer comments in this fixture.
- Line count or file size as a criterion: PR #226 mentions `1367 lines` as
  evidence that responsibilities have accumulated, but the intake must record it
  only as ignored evidence. The phrase "file size as a gate" is a
  non-derivation here, not a rule.
- Generic environment, database, or network impure-shell scope: those may be
  supported by broader repo conventions, but these two comments only mention
  filesystem and subprocess side effects.

Expected distillation:

```json
{
  "repo_conventions": [
    {
      "source_ref": "interralis#225",
      "rule": "Every Rust module's first //! line must state one responsibility; when review evidence names multiple jobs or needs \"and\", enumerate those roles and split the file.",
      "verification_predicate": "Run bin/adlc convention-scan --file <changed Rust file> --json and inspect module-doc first lines for multi-job wording and enumerated roles.",
      "applies_to": ["changed Rust files"]
    },
    {
      "source_ref": "interralis#226",
      "rule": "When a Rust responsibility grows sub-parts, split it into a recursive directory module instead of keeping catalog, runner, driver, report, and type roles in one flat file.",
      "verification_predicate": "Review planned and changed Rust files for catch-all roles such as catalog plus runner plus driver plus report in one flat file.",
      "applies_to": ["planned files", "changed Rust files"]
    },
    {
      "source_ref": "interralis#225,#226",
      "rule": "Keep pure Rust type, catalog, probe, and normalization logic separate from filesystem and subprocess impure shell modules.",
      "verification_predicate": "Run bin/adlc convention-scan --file <changed Rust file> --json and verify filesystem or subprocess side effects live in isolated impure shell modules.",
      "applies_to": ["changed Rust files"]
    }
  ],
  "product_vocabulary": [],
  "skill_file_rule_changes": []
}
```

Passing outcome: the intake can regenerate the convention set above from the PR
comments without relying on this document's prose, while also recording per-
comment provenance and ignored size evidence. Failing outcome: the comments are
classified as `one_off`, produce no verification predicate, create a generic
ADLC skill rule without a target-repo `repo_conventions` rule, or derive
thin-coordinator / size-gate rules from these two comments.

## Step 2: Eval Case Promotion

Before distilling a new skill rule, convert quality failures into candidate eval cases. This keeps slop fixes measurable instead of turning every correction into another prompt note.

Candidate sources:
- `human_edit`
- `council_rejection`
- `runtime_failure`
- `deviation_log`
- `production_sample`
- `incident`
- `support_ticket`
- `analytics_drop`
- `other`

Promotion record:

```json
{
  "source": "human_edit",
  "skill_source": "stop-slop | slop-judge | codegen-context | other",
  "pipeline_phase": "string",
  "input": "string",
  "bad_output": "string",
  "corrected_output": "string",
  "expected_quality": "string",
  "metric": "rubric_score | exact_match | schema_validity | semantic_similarity | test_strength",
  "threshold": 0.7,
  "owner": "string",
  "status": "candidate | accepted | rejected"
}
```

Rules:
- Human edits with `edit_type = slop_removal` always create a candidate eval case.
- `slop-judge` revisions with `new_eval_case_candidate` create a candidate eval case.
- Eval Council findings with `missing_slop_quality_gate`, `slop_score_below_threshold`, or `slop_regression` create a candidate eval case or a missing-benchmark task.
- Execution deviation logs with a ledger-absent architecture decision create a brief-generator defect record. Use `bin/adlc deviation-log-validate` to count `brief_generator_defect_count`; architecture-affecting ledger-absent deviations become feedback to the Build Brief generator, not silent coder cleanup.
- Completion audit findings from `bin/adlc completion-audit` are candidate rule evidence. Contradictions and confirmed thinness must be emitted as `feedback_findings` and can promote into `docs/solutions/predicate-library.json` rules with stable `PRED-*` IDs.
- Candidate cases require human or council approval before they become permanent blocking gates.
- Accepted cases are added to the task or skill benchmark before any generalized rule is written.

## Step 3: Pattern Distillation (Nightly)

1. Read accumulated diffs since last distillation
2. Group by (skill_source, edit_type)
3. When 10+ similar edits accumulate for the same pattern:
   - Use LLM to identify the common pattern across edits
   - Distill into a candidate rule (specific, actionable)
   - Validate: would this rule have prevented the edits in recent outputs?
   - If validation score > 80%: write rule to skill file
4. When a rule has prevented 0 edits for 30+ days:
   - Flag for potential removal (BPE: don't accumulate stale rules)

## Step 4: Skill Update

- All rule changes are version-controlled (git)
- Changelog entry per rule: what changed, why, evidence (N edits)
- Human can override any auto-generated rule
- Stale rules (unused 30 days) flagged, not auto-removed

## Domain Adaptation

**SWElfare:** Post-merge diff capture between agent PR and merged version. Updates: codegen context assembly, anti-slop rules, brief generation prompts.

**Magnus:** Post-publish diff between draft and Eric's edited/published version. Updates: voice profile (`eric-voice-profile.md`), external Magnus `content-forge` rules, slop gate banned phrases.

**Ratatosk:** Post-settlement outcome vs prediction. Updates: signal weighting, strategy parameters, conviction calibration, experiment loop priorities.

## Guardrails

- Candidate rules require validation (>80% effectiveness) before activation
- All changes auditable via git history
- Stale rules (unused 30 days) flagged for removal review
- Human override on any auto-generated rule
- Rules that contradict existing human-set rules are flagged, not auto-applied
- Maximum 5 new rules per distillation cycle (prevent rule explosion)

## BPE Compliance

The feedback loop should make skills SIMPLER over time, not more complex. If a rule addresses a model limitation that has been resolved, the loop should flag it for removal. The quarterly BPE audit asks: "Which rules can we remove because models no longer need them?"
