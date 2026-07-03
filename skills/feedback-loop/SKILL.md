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

1. Read supplied review comments or run `gh pr view <id> --comments` and inspect
   unresolved review threads when thread state is available.
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

Example: Interralis maintainer comments like "this file does two jobs", "split
the coordinator from worker logic", "do not use file size as a gate", and "use
the product term in the PR" become target repo conventions or vocabulary rules.
They must not be buried as chat-only reminders.

### Acceptance Walkthrough: Interralis PR #225 And #226

Use these review threads as the regression fixture for maintainer-comment intake:

- PR #225 (`Add harness metadata source discovery`) review comment identifies a
  file whose first module doc describes registry and discovery inventory, then
  calls out three jobs in one file: registry data/types, id inference, and a
  filesystem discovery walker. It also flags filesystem walking mixed with pure
  registry and normalization helpers.
- PR #226 (`Add LLM persona UX regression harness`) review comment identifies a
  flat `persona_ux.rs` file containing catalog data, runner logic, an LLM
  subprocess driver, report file I/O, report explanation, and pure types/probes.
  It says the work should become a recursive directory module with pure files
  and documented impure subprocess/filesystem shells.

Expected distillation:

```json
{
  "repo_conventions": [
    {
      "source_ref": "interralis#225",
      "rule": "Every Rust module's first //! line must state one responsibility; if the responsibility needs 'and' or names multiple jobs, split the file.",
      "verification_predicate": "Run bin/adlc convention-scan --file <changed Rust file> --json and inspect module-doc first lines for multi-job wording.",
      "applies_to": ["changed Rust files"]
    },
    {
      "source_ref": "interralis#226",
      "rule": "When a Rust module grows sub-parts, split it into a directory module recursively instead of keeping a flat catch-all file.",
      "verification_predicate": "Review scaffold and changed files for catch-all roles such as catalog plus runner plus driver plus report in one file.",
      "applies_to": ["planned files", "changed Rust files"]
    },
    {
      "source_ref": "interralis#225,#226",
      "rule": "Keep pure core logic separate from filesystem, subprocess, environment, database, and network impure shells.",
      "verification_predicate": "Run bin/adlc convention-scan --file <changed Rust file> --json and verify side-effect calls live in modules documented as impure shells.",
      "applies_to": ["changed Rust files"]
    }
  ],
  "product_vocabulary": [],
  "skill_file_rule_changes": [
    "build-feature Step 2 must ingest target-repo maintainer conventions before Build Brief decomposition.",
    "architecture-pattern must require recursive directory-module decomposition when a file grows sub-parts."
  ]
}
```

Passing outcome: the intake can regenerate the convention set above from the PR
comments without relying on this document's prose. Failing outcome: the comments
are classified as `one_off`, produce no verification predicate, or create a
generic ADLC skill rule without a target-repo `repo_conventions` rule.

## Step 2: Eval Case Promotion

Before distilling a new skill rule, convert quality failures into candidate eval cases. This keeps slop fixes measurable instead of turning every correction into another prompt note.

Candidate sources:
- `human_edit`
- `council_rejection`
- `runtime_failure`
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
