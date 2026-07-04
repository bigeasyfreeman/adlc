# Feedback Loop Real Data Walkthrough

OS-6 uses `tests/fixtures/interralis-pr-review-comments.json` as the regression
fixture for maintainer-comment intake. The fixture was fetched read-only from a
local Interralis checkout with `gh pr view` and `gh api` calls recorded in
`fixture_provenance`. The pull review-comment endpoints for Interralis PR #225
and PR #226 returned empty arrays, so the convention evidence is the verbatim
Aether- issue-comment body on each PR.

## Supported Derivations

The comments support exactly these `repo_conventions.rules[]`:

- `REVIEW_COMMENT_ONE_RESPONSIBILITY`: the comments say the first module doc line
  needs `and`, then enumerate distinct jobs in one Rust file. The resulting rule
  requires one responsibility and enumerated review evidence when a split is
  required.
- `REVIEW_COMMENT_RECURSIVE_DIRECTORY_MODULE`: PR #226 says the flat
  `persona_ux.rs` file should become `persona_ux/` with catalog, runner, driver,
  report, and type files.
- `REVIEW_COMMENT_PURE_CORE_IMPURE_SHELL`: PR #225 and PR #226 identify
  filesystem walking, report file I/O, and subprocess spawning mixed with pure
  registry, catalog, probe, type, or normalization logic.

## Non-Derivations

These two PR comments do not support a thin-coordinator rule. That rule belongs
to Interralis `CLAUDE.md` and later merge feedback, not this fixture.

The comments also do not support a line-count or file-size gate. PR #226 mentions
`1367 lines` only as evidence that responsibilities accumulated; ADLC records
that as ignored evidence and never turns it into a criterion.

The comments do not support broad environment, database, or network impure-shell
scope. Those may be supported by broader target-repo conventions, but this
fixture only names filesystem and subprocess side effects.

## Standing Intake Path

Given a merged or reviewed PR, run:

```bash
bin/adlc feedback-conventions --repo OWNER/REPO --pr PR_NUMBER --json
```

Pass `--pr` multiple times to distill a batch. The command fetches maintainer
issue comments, inline review comments, and non-empty review bodies through `gh`,
filters out PR-author comments, then records every comment in
`intake_records[]` as either `repo_conventions_rule`, `skill_rule_change`, or
`one_off`. Schema-compatible convention rules stay in
`repo_conventions.rules[]`; richer comment IDs and URLs stay in
`derived_rule_provenance`.
