---
title: "Compound context passes references instead of full notes"
date: "2026-06-07"
adlc_domain: "workflow"
problem_type: "convention"
module: "scripts/adlc.py"
severity: "low"
track: "knowledge"
tags: ["compound-context", "learning-refs"]
related_tasks: ["ADLC-CEI-002", "ADLC-CEI-003"]
source_evidence:
  - "docs/specs/compound-engineering-learning-store.md"
verifier:
  type: "command"
  command: "bin/adlc compound-context --workspace . --json"
  expected: "returns compact learning refs"
redaction_review:
  status: "passed"
  reviewer: "adlc"
stale_conditions:
  - "docs/solutions frontmatter contract changes"
---

# Compound context passes references instead of full notes

## Context

ADLC needs prior verified learnings before research without bloating downstream prompts.

## Learning

Compound context should emit compact references with paths, short summaries, source evidence, verifier refs, and stale status.

## Applicability

Use this for research, planning, reuse analysis, and context assembly. Do not treat a learning ref as proof that current code already behaves correctly.

## Evidence

- Source: `docs/specs/compound-engineering-learning-store.md`
- Verifier: `bin/adlc compound-context --workspace . --json`

## Stale Conditions

- Refresh when the learning-entry schema changes.

## Guidance

Pass IDs and paths to downstream agents. Inline only a short distilled summary and verifier reference.

## Examples

`learning_refs[0].path` points to a markdown entry; `learning_refs[0].summary` is a short extract.
