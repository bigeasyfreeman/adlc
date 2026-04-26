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
  Nightly: diffs grouped →
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

## Step 2: Pattern Distillation (Nightly)

1. Read accumulated diffs since last distillation
2. Group by (skill_source, edit_type)
3. When 10+ similar edits accumulate for the same pattern:
   - Use LLM to identify the common pattern across edits
   - Distill into a candidate rule (specific, actionable)
   - Validate: would this rule have prevented the edits in recent outputs?
   - If validation score > 80%: write rule to skill file
4. When a rule has prevented 0 edits for 30+ days:
   - Flag for potential removal (BPE: don't accumulate stale rules)

## Step 3: Skill Update

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
