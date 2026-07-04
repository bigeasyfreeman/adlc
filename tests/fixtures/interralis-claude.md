# Interralis — agent context

Standing context for any agent (Claude Code or otherwise) working in this repo.
This is the committed agent-facing context; local ignored `AGENTS.md` files may
point here.
The harness-neutral coding standards contract is
`docs/CODING_STANDARDS_CONTRACT.md`; keep this file aligned with that contract.

## Code conventions: one responsibility per file, one thing per function, composability

These are not aspirations — they are how this codebase is already built. The
`src/enroll/` module is the worked exemplar; read it before writing new code in a
new area, and match its shape. New code that violates these should be reshaped,
not merged.

### 1. The module is the unit of responsibility

- **One responsibility per file**, stated in the first line of the module's `//!`
  doc-comment. Examples: `enroll/hash.rs` → "Reading, hashing, and
  executable-validation"; `enroll/evaluate.rs` → "Drift evaluation … This module
  is pure." If you can't write that one line without "and", the file is doing too
  much — split it.
- **The coordinator file is a thin coordinator, never a worker.** (That file is
  `module.rs` in new code, or `module/mod.rs` in not-yet-migrated modules — see
  "Module file layout" below.) It owns only: the shared error type
  (`EnrollError`), cross-cutting rules everyone uses (`validate_agent_name`,
  `default_profile_for_agent`), and the curated re-export surface. The real work
  lives in submodules.
- The coordinator's doc-comment carries a **one-line index of every submodule and
  its single job** — the map a new reader (or agent) reads first. Keep it in sync
  when you add a submodule.
- When a responsibility grows sub-parts, it becomes a **directory module that
  recursively follows the same shape**. `enroll/setup/mod.rs` is itself an
  orchestrator (`run()` assembles a `SetupReport`) delegating to `report`,
  `ambient_shim`, `supervisor_key`.

#### Module file layout: prefer `module.rs` over `module/mod.rs`

New directory modules use the Rust 2018 path convention: the coordinator lives in
`foo.rs` **beside** its `foo/` directory, not in `foo/mod.rs`. The coordinator's
role is unchanged — only the filename moves out of the directory. Existing
`mod.rs` files are migrated opportunistically when you next touch the module;
this is not a blocking tree-wide cleanup.

Migrating one module is a history-preserving rename with no code edits:

```
git mv src/foo/mod.rs src/foo.rs        # the foo/ directory stays as-is
```

`mod` declarations, `use super::*`, and every external `crate::foo::…` path keep
working because `foo.rs` and `foo/mod.rs` are the same module root; `cargo test`
should stay green with zero source changes. The *only* reasons a move ever needs
an edit:

- **Relative `#[path = "…"]` / `include!` / `include_str!` paths** resolve against
  the file's own directory, which moves up one level in the rename — so `../../x`
  becomes `../x`. (e.g. enroll's `#[path = "../../tests/e2e/enroll/e2e.rs"]` on
  the `e2e` module.)
- **CI manifests that list files by path** — notably the Rust file-size allowlist
  — must update `src/foo/mod.rs` entries to `src/foo.rs`.
- Keep the rename in **its own commit**, separate from any logic change, so review
  is a trivial rename diff and `git blame` stays clean.

### 2. One thing per function

- An orchestrating function reads as a **list of named steps**, each step a helper
  that does exactly one thing. `evaluate_binary` is ~30 lines of composition; the
  logic lives in `recorded_binary_state`, `candidate_supersedes_record`,
  `describe_source`, `stale_refresh_command` — each with a doc-comment stating its
  single job.
- **Verbs name functions that act** (`hash_file`, `read_hash`,
  `canonical_executable`, `describe_source`); **nouns name the things they
  return** (`BinaryEvaluation`, `HashRead`, `DetectedAgent`).
- Multi-argument operations take a **request struct** (`AddRequest`), not a long
  positional parameter list.

### 3. Composability is enforced by separation

- **Pure core, impure shell.** `enroll/evaluate.rs` reads and hashes but never
  mutates trust — it is pure and exhaustively unit-testable. Side effects
  (registry writes, shim install) live only in `enroll/lifecycle.rs`, documented
  as "the only paths that change the registry."
- **Inject the environment, don't reach for it.** `refresh` is a thin wrapper over
  `refresh_with(path, name, now, resolve)` — PATH resolution and the clock
  (`now: &str`) are parameters, so tests exercise relocation without mutating
  process env. Time is always passed in, never read inside logic.
- **One canonical path for a privileged operation, documented as "the *only*
  path."** Trust is re-established solely via `refresh`; nothing auto-trusts.

### 4. Supporting discipline

- **Curated public surface:** `pub use` the real API from `mod.rs`; `pub(crate)`
  for cross-submodule internals. Callers don't reach into submodules.
- **One shared, structured error enum** with context-carrying variants
  (`Io { action: &'static str, … }`); each operation maps to precise variants.
- **Tests live beside the responsibility** — every file has its own
  `#[cfg(test)] mod tests` covering that file's one job, with local helpers
  (`write_exec`, `with_home`).
- **Semantics encoded in types, not comments alone:** `BinaryState` + `is_stale()`
  make fail-closed behavior unavoidable; the "no-overclaim" rule is a field in the
  report, not a hope.

### Checklist before adding or growing a file

- [ ] Can I state this file's responsibility in one "and"-free line?
- [ ] Is the coordinator file still only coordinating (types, shared rules, re-exports)?
- [ ] New directory module? Use `module.rs` + `module/`, not `module/mod.rs`.
- [ ] Does each function do one thing its name promises?
- [ ] Is the pure logic separable from I/O and the environment/clock?
- [ ] Are side effects and privileged operations on a single documented path?
- [ ] Do tests sit next to the responsibility they cover?
