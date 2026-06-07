---
title: "Invalid missing verifier"
date: "2026-06-07"
adlc_domain: "workflow"
problem_type: "workflow"
module: "scripts/adlc.py"
severity: "medium"
track: "knowledge"
tags: ["invalid"]
related_tasks: ["ADLC-CEI-001"]
source_evidence:
  - "docs/specs/compound-engineering-learning-store.md"
redaction_review:
  status: "passed"
  reviewer: "adlc"
stale_conditions:
  - "schema changes"
---

# Invalid missing verifier

## Context

This fixture should fail.

## Learning

It lacks verifier frontmatter.

## Applicability

Validation tests only.

## Evidence

- Source: `docs/specs/compound-engineering-learning-store.md`

## Stale Conditions

- None.

## Guidance

Do not use.

## Examples

None.
