---
title: "Short reusable learning title"
date: "YYYY-MM-DD"
adlc_domain: "workflow"
problem_type: "workflow"
module: "path/or/module"
severity: "medium"
track: "knowledge"
tags: ["tag-one", "tag-two"]
related_tasks: ["BRIEF-ID-001"]
source_evidence:
  - "path/to/file:line"
verifier:
  type: "command"
  command: "command that proved the learning"
  expected: "passes"
redaction_review:
  status: "passed"
  reviewer: "name-or-role"
stale_conditions:
  - "condition that should trigger scoped refresh"
---

# Short reusable learning title

## Context

What was being changed or investigated.

## Learning

The reusable lesson in one or two paragraphs.

## Applicability

Where this applies and where it does not apply.

## Evidence

- Source: `path/to/file:line`
- Verifier: `command`

## Stale Conditions

- Re-run scoped refresh when the module, verifier, or contract changes.

## Guidance

Concrete guidance for future ADLC agents.

## Examples

Small example or reference path.
