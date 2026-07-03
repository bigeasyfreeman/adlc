---
name: ldd-enforcement
description: "Lint-Driven Development — formatting and syntax gate that runs BEFORE test execution. Violations block TDD entry. Triggers at Phase 4 entry."
---

# LDD Enforcement (Lint-Driven Development)

## Overview

LDD ensures code is structurally sound before testing begins. Run linters, formatters, and type-checkers FIRST. Fix all violations. Only then proceed to TDD.

**LDD is the formatting and syntax gate. TDD is the success criteria gate. Both are mandatory, both are sequential, both block.**

## When to Use

- **Auto-trigger:** Phase 4 entry, before any TDD cycle
- **Re-trigger:** After TDD REFACTOR step (verify refactoring didn't break lint)
- **Manual:** Any time code quality needs structural verification

## Core Protocol

```
1. Run all configured linters          → collect violations
2. Run all configured formatters       → collect formatting issues
3. Run all configured type-checkers    → collect type errors
4. Run repo convention structural scan → collect convention violations when target repo conventions are present
5. Any violations?
   YES → Fix all violations → Go to step 1
   NO  → Proceed to TDD
```

**This is a hard gate.** Lint violations block test execution. A task cannot enter TDD until LDD is clean.

## Per-Language Defaults

| Language | Linters | Formatters | Type Checkers |
|----------|---------|------------|--------------|
| Python | ruff | black | mypy |
| JavaScript | eslint | prettier | — |
| TypeScript | eslint | prettier | tsc |
| Rust | clippy | rustfmt | (compiler) |
| Go | golangci-lint | gofmt | (compiler) |

## What LDD Covers

| Category | Examples | Why It Matters |
|----------|---------|---------------|
| Code style | Indentation, line length, naming conventions | Consistency reduces cognitive load |
| Type safety | Missing type annotations, type mismatches | Catches bugs before runtime |
| Import hygiene | Unused imports, circular imports, ordering | Reduces dependency surface |
| Dead code | Unreachable code, unused variables/functions | Reduces maintenance burden |
| Naming conventions | snake_case vs camelCase consistency | Pattern recognition speed |
| File structure | Module organization, __init__.py completeness | Navigability |
| Repo conventions | Rust module doc first-line responsibility, impure-shell boundaries, coordinator-thin files | Enforces target repo standards before TDD |

## Repo Convention Structural Scan

When target repo conventions are present, LDD must run the mechanical convention gate for every changed file it supports:

```bash
bin/adlc convention-scan --file <changed-file> --json
```

Rust is supported first. The scan fails a changed Rust file when:

- the first `//!` module-doc line appears to describe multiple jobs with `and`
- the file performs filesystem, subprocess, environment, database, or network calls while the module-doc first line does not declare it an impure shell
- a coordinator file (`mod.rs` or `module.rs` beside `module/`) contains worker logic instead of thin coordination and re-exports

Escape hatch: a task may proceed only if the scan output or task output records an explicit waiver with file, rule, and reason, for example `src/foo.rs:side_effect_without_impure_shell:legacy split tracked separately`. Silent ignores are failures.

Hard boundary: LDD must never use file size, line count, or SLOC as a criterion. Size may be observed by other tools, but it cannot block, warn, or justify a split.

### Worked Example

A Rust file with a first module-doc line such as `//! Reading and writing records` plus `std::fs` access fails before TDD:

```bash
bin/adlc convention-scan --file src/collect.rs --json
```

Expected findings:

- `module_doc_multiple_jobs` because the first `//!` line describes more than one responsibility with `and`
- `side_effect_without_impure_shell` because filesystem access appears without an impure-shell declaration

A coordinator file such as `src/project.rs` or `src/project/mod.rs` also fails with `coordinator_worker_logic` when it contains worker functions instead of declarations, wiring, and re-exports.

## BPE Compliance

LDD checks **outcomes** (does the code pass lint?) not **process** (did the agent format before writing?).

**Remove when:** Models produce lint-clean code >95% of the time. At that point, this gate becomes a no-op validation — keep it running but it won't block.

## Configuration

```yaml
adlc:
  ldd:
    linters:
      - ruff
      - mypy
    formatters:
      - black
    type_checkers: []  # covered by mypy for Python
    convention_scan: true
    block_on_violation: true
    auto_fix: true     # attempt auto-fix before reporting violations
```

## Common Rationalizations

| Excuse | Rebuttal |
|--------|---------|
| "Linting slows down iteration" | A 2-second lint check prevents 20-minute debugging sessions |
| "The code works, formatting doesn't matter" | Unformatted code increases review time and hides bugs |
| "Type annotations are overkill for this" | Types are documentation that the compiler verifies |
| "I'll clean it up later" | Later never comes. Lint debt compounds. |
| "The file is small enough" | File size and line count are not ADLC convention criteria. Enforce responsibility, side effects, and coordinator boundaries instead. |

## Verification

- [ ] All configured linters pass with zero violations
- [ ] All configured formatters produce no changes (code is already formatted)
- [ ] All type checkers pass with zero errors
- [ ] `bin/adlc convention-scan` passes for changed supported files, or every waiver is explicit with file, rule, and reason
- [ ] LDD ran BEFORE TDD (not after)
- [ ] LDD re-ran AFTER TDD REFACTOR step
- [ ] No file-size, line-count, or SLOC criterion was used
