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
4. Any violations?
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

## Verification

- [ ] All configured linters pass with zero violations
- [ ] All configured formatters produce no changes (code is already formatted)
- [ ] All type checkers pass with zero errors
- [ ] LDD ran BEFORE TDD (not after)
- [ ] LDD re-ran AFTER TDD REFACTOR step
