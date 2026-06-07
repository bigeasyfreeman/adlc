---
title: "Preserve task IDs across Build Brief revisions"
date: "2026-06-07"
adlc_domain: "workflow"
problem_type: "bugfix"
module: "docs/schemas/build-brief.schema.json"
severity: "medium"
track: "bugfix"
tags: ["task-identity", "resume"]
related_tasks: ["ADLC-CEI-004"]
source_evidence:
  - "docs/research/compound-engineering-plugin-adlc-review.md"
verifier:
  type: "command"
  command: "bash tests/test_adlc_contracts.sh"
  expected: "passes"
redaction_review:
  status: "passed"
  reviewer: "adlc"
stale_conditions:
  - "Build Brief task schema changes"
---

# Preserve task IDs across Build Brief revisions

## Context

ADLC work-item emitters and resume state depend on stable task identifiers.

## Symptom

Revised decompositions can become hard to resume when task identity is implicit in ordering.

## Root Cause

The task contract did not expose an optional stable identity and verifier fingerprint for downstream state.

## Fix

Keep `task_id` stable and add optional task identity and resume fingerprint fields.

## Prevention

Contract tests assert that optional resume fingerprint fields are accepted and preserved by emitters.

## Learning

Task identity should be semantic and durable. Splits should keep the original ID on the original concept and allocate new IDs for new work.

## Applicability

Applies to Build Brief revisions and workflow resume.

## Evidence

- Source: `docs/research/compound-engineering-plugin-adlc-review.md`
- Verifier: `bash tests/test_adlc_contracts.sh`

## Stale Conditions

- Revisit when workflow-state schema changes.
