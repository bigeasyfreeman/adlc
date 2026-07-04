# ADLC Process Artifact Storage

ADLC process artifacts are planner, evaluator, audit, and closeout materials that
support a run but are not product code, product tests, or user-facing target-repo
documentation. They must live outside the target repository diff.

## Storage Root

The canonical root is `ADLC_PROCESS_ARTIFACT_ROOT` when set. Otherwise it is the
ADLC checkout's `.adlc/process-artifacts` directory. This root is ignored by git
in the ADLC checkout and is separate from the target repository.

Use the deterministic helper before writing any process artifact:

```bash
bin/adlc process-artifact-path \
  --target-repo owner/repo \
  --task TASK-123 \
  --artifact-type build-brief \
  --filename build-brief.json \
  --json
```

The command only computes the path. Writers create parent directories and write
their own schema-valid or markdown output at the returned `path`.

## Layout

Every path is keyed by target repository, task, run, and artifact family:

```text
{storage_root}
  {target_repo_key}
    {task_key}
      {run_id}
        build-brief
          build-brief.json
        eval
          eval.json
        audit
          audit.json
        closeout
          closeout.md
        validation
          validation.json
```

`target_repo_key` is derived from `owner/repo` or a GitHub URL when available. For
local paths, it is the sanitized directory name plus an eight-character hash of
the canonical path. `task_key` is the sanitized Build Brief task ID, tracker key,
or closeout task key. `run_id` defaults to `current` and should be set to the
workflow run or session ID when one exists.

## Required Writers

The Build Brief agent and any skill or agent that writes these materials must use
this storage contract:

- Build Brief drafts and approved briefs: `artifact-type build-brief`
- Eval and council verdict reports: `artifact-type eval`
- Test-strength, dark-code, tech-debt, loop-maturity, and similar audits:
  `artifact-type audit`
- PR packages, validation summaries, and learning-capture closeout decisions:
  `artifact-type closeout` or `artifact-type validation`

Target repositories may keep transient runtime state under their ignored local
workspace state directory, but canonical process artifacts must be written to
this ADLC-side store and referenced from PR bodies or work items by path or
tracker link. They must not be added to target-repo commits.

## PR Hygiene

`bin/adlc pr-hygiene-scan` blocks process artifact paths, goal prompt names,
local absolute paths, banned internal vocabulary, removed target-repo gates, and
undocumented stacked bases. A target-repo PR containing process artifact paths
must be fixed by moving those files to this storage layout, not by renaming them
inside the target repo.
