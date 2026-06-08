# Compound Engineering Learning Store

## Purpose

ADLC's compound engineering layer is a repo-local learning and resume system. It makes prior verified work cheap to reuse without importing a second planner or a plugin-specific workflow.

The store lives in `docs/solutions/`. Entries are markdown files with schema-validated frontmatter and compact sections. They are prior-art references, not proof of current behavior. A future run must still verify the code, schema, command, or workflow it changes.

## Entry Tracks

Use one of two tracks:

- `bugfix`: a verified failure, root cause, fix, and prevention note.
- `knowledge`: a verified convention, integration pattern, workflow decision, or reusable implementation note.

Both tracks must include evidence, a verifier, stale conditions, and redaction status. Loop maturity reports can be captured as `knowledge` only when they cite `loop_contract_path`, `loop_maturity_report_path`, and the verifier command that produced the report.

## Frontmatter Contract

Every entry must begin with YAML frontmatter:

```yaml
---
title: "Stable task resume fingerprints"
date: "2026-06-07"
adlc_domain: "workflow"
problem_type: "workflow"
module: "scripts/adlc.py"
severity: "medium"
track: "knowledge"
tags: ["compound-context", "resume"]
related_tasks: ["ADLC-CEI-004"]
source_evidence:
  - "docs/build-briefs/compound-engineering-workflow-integration.json"
verifier:
  type: "command"
  command: "bash tests/test_adlc_cli.sh"
  expected: "passes"
redaction_review:
  status: "passed"
  reviewer: "adlc"
stale_conditions:
  - "workflow-state schema changes"
---
```

Allowed domains: `build_loop`, `fix_loop`, `feedback_loop`, `integration`, `security`, `observability`, `testing`, `workflow`, `other`.

Allowed problem types: `bugfix`, `build_validation`, `lint_cleanup`, `runtime_failure`, `performance`, `security`, `workflow`, `architecture`, `convention`, `tooling`.

Allowed severities: `critical`, `high`, `medium`, `low`.

## Required Sections

After frontmatter, every entry must include these headings:

```markdown
## Context
## Learning
## Applicability
## Evidence
## Stale Conditions
```

Bugfix entries should also include:

```markdown
## Symptom
## Root Cause
## Fix
## Prevention
```

Knowledge entries should also include:

```markdown
## Guidance
## Examples
```

## Redaction Rules

Learning entries must not capture secrets, private tokens, local credentials, or unsupported environment-specific claims. The validator blocks common token and private-key shapes, but reviewers still own final judgment.

When a useful learning depends on a sensitive detail, write the stable behavior and cite the verifier or public path instead of copying the sensitive value.

## Workflow Use

`compound_preflight` scans `docs/solutions/` before research and emits compact `learning_refs`: ID, path, title, tags, summary, source evidence, verifier, stale status, and no-op reasons. It does not paste full entries into downstream prompts.

Research, planning, reuse analysis, and codegen context consume `learning_refs` as prior-art candidates. A task can cite them when they are directly relevant, but code behavior still requires direct verification.

For LLM-driven loop work, compact refs may include:

- `loop_contract_path`
- `loop_maturity_report_path`
- `maturity_verdict`
- score gaps that remain stale until `bin/adlc loop-maturity-audit` is rerun
- the no-overclaim boundary that says whether the loop is `assisted_loop` or `self_autonomous`

`learning_capture` runs after PR prep only when a verified reusable learning exists. `learning_refresh` is scoped maintenance: run it for a stale signal, a requested module/domain, or a significant refactor. Broad refresh is not part of the default build loop.
