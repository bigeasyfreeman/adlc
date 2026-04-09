---
name: reuse-analysis
description: "Discovers existing functions/patterns/utilities that must be reused (not reimplemented) and identifies antipatterns to avoid. Triggers at Phase 1 (discovery) and Phase 5 (verification)."
---

# Reuse Analysis

## Overview

Before building anything new, prove it doesn't already exist. This skill discovers reusable code, enforces pattern continuation, and prevents antipattern repetition.

## When to Use

- **Phase 1 (discovery):** Scan codebase for existing patterns before design
- **Phase 5 (verification):** Verify implementation didn't duplicate existing code
- **Manual:** When assessing whether to build or reuse

## Discovery Process

### Step 1: AST-Based Scan
Parse the codebase to find existing functions, classes, and utilities. Prioritize:
- `utils/`, `helpers/`, `common/`, `shared/` modules
- Functions with docstrings matching task keywords
- Recently modified functions (likely well-maintained)

### Step 2: Keyword Matching
Match task description terms against:
- Function names and class names
- Docstrings and inline comments
- Module-level documentation

### Step 3: LLM-Filtered Relevance
Rank discovered items by relevance to the current task. Filter out false positives.

### Output: Reusable Items

```markdown
### DO NOT REIMPLEMENT: function_name
- File: path/to/file.py:42
- Signature: def function_name(arg1: str, arg2: int) -> Result
- Purpose: One-line description of what it does
- How to use: `result = function_name("input", 42)`
```

## Antipattern Catalog

Known bad patterns in the codebase that must NOT be repeated:

```markdown
### ANTIPATTERN: descriptive_name
- What: Description of the bad pattern
- Where seen: path/to/file.py (if known, or "historical")
- Why bad: Explanation of the problem it causes
- Instead: What to do instead
```

### Sources for Antipatterns
1. Learning store (historical failures)
2. Council rejection reasons (patterns that got flagged)
3. Post-execution slop findings (recurring violations)
4. Human edit patterns (things humans keep removing)

## Verification (Phase 5)

### Reimplementation Detection
Compare new functions against the reuse catalog:
1. Extract new function definitions from the diff
2. Compare names and signatures against catalog
3. Check for >80% code similarity with existing functions
4. Flag violations with: what was reimplemented, where the original lives, how to use it

### Blocking Behavior
- Near-duplicate detection (>80% similarity) **BLOCKS pipeline**
- Report includes specific remediation: "Use `existing_function()` from `path/to/module.py` instead"

## BPE Compliance

**Remove when:** Models consistently discover and reuse existing patterns without hints. At that point, keep verification (Phase 5) but remove discovery hints (Phase 1).

## Common Rationalizations

| Excuse | Rebuttal |
|--------|---------|
| "My version is slightly different" | Extend the existing function. Don't duplicate and diverge. |
| "I didn't know it existed" | That's why reuse analysis runs first. Now you know. |
| "The existing code is messy" | Refactor it in a separate task. Don't create a parallel implementation. |
| "It's faster to rewrite" | Rewriting is faster today. Maintaining two versions is slower forever. |

## Verification Checklist

- [ ] Reuse analysis ran before design (Phase 1)
- [ ] All reusable items listed with "DO NOT REIMPLEMENT" tags
- [ ] Antipatterns identified and documented
- [ ] Implementation verified: no reimplementation detected (Phase 5)
- [ ] Existing conventions followed (naming, error handling, config patterns)
