---
skill: stop-slop
version: 2.0
description: Dual-mode slop detection for code and content. ADLC v2 spec.
when:
  - glob: "**/*.md"
    event: pre-commit
  - glob: "**/*.txt"
    event: pre-commit
  - glob: "**/*.py"
    event: pre-commit
  - glob: "**/*.ts"
    event: pre-commit
  - glob: "**/*.js"
    event: pre-commit
  - glob: "**/*.jsx"
    event: pre-commit
  - glob: "**/*.tsx"
    event: pre-commit
  - agent: magnus
    event: content_drafting
  - agent: magnus
    event: content_strategy
  - agent: sander
    event: outreach_copy
  - agent: sander
    event: outreach_delivery
  - command: stop-slop
  - command: slop-check
---

# Stop Slop v2: Code + Content Pattern Removal

> Dual-mode slop detector. Mode 1 catches placeholder code, god functions, duplication, and missing wiring. Mode 2 catches AI writing patterns, banned phrases, and weak prose. Both modes gate delivery.

---

## Mode 1: Code Slop

Detects structural code problems that indicate incomplete, lazy, or AI-generated code. Runs on all `.py`, `.ts`, `.js`, `.jsx`, `.tsx` files.

### Detection Patterns

#### 1. Placeholder Detection

Regex rules. Any match is a hard failure — no scoring, immediate fix required.

```
pass\s*(#.*)?$          # bare pass statements
TODO\b                  # TODO comments
FIXME\b                 # FIXME comments
raise NotImplementedError
\.\.\.\s*$              # ellipsis as function body
```

AST rules (Python):
- Function body is a single `pass` or `Expr(Constant(Ellipsis))` node
- Class body is a single `pass` node with no docstring

AST rules (TypeScript/JavaScript):
- Function body is empty block `{}`
- Function body throws `new Error("not implemented")`

#### 2. God Function Growth

**Ceiling:** 50 SLOC per function (default). Configurable via `.stop-slop.yml`:

```yaml
code_slop:
  max_function_sloc: 50
```

Measurement: count non-blank, non-comment, non-decorator lines inside the function body. Exceeding the ceiling triggers a warning. Exceeding 2x the ceiling is a hard failure.

#### 3. Near-Duplicate Code Blocks

Flag any two code blocks (3+ lines) with >80% token similarity within the same file or across files in the same commit. Uses normalized token comparison (strip whitespace, normalize variable names to positional placeholders).

Threshold: 80% similarity = warning. 95% similarity = hard failure (copy-paste detected).

#### 4. Identity Transforms in Comprehensions

Regex/AST detection for comprehensions that return the loop variable unchanged:

```python
# Flagged:
[x for x in items]
[item for item in collection]
{k: v for k, v in d.items()}

# Not flagged (these transform):
[x.name for x in items]
[x for x in items if x.active]
```

#### 5. Unnecessary Defensive Comparisons

Detect patterns where the comparison is redundant:

```python
# Flagged:
if x == True:
if x == False:
if x == None:
if len(items) > 0:
if len(items) != 0:
if bool(x):

# Fix:
if x:
if not x:
if x is None:
if items:
if items:
if x:
```

#### 6. Hardcoded URLs, Ports, Timeouts Outside Config

Regex patterns for values that belong in configuration:

```
https?://[^\s"']+            # URLs (except in config/, .env, tests/)
:\d{4,5}[/"'\s]             # port numbers
timeout\s*=\s*\d+           # hardcoded timeouts
sleep\(\s*\d+               # hardcoded sleep values
```

Exemptions: files matching `**/config/**`, `**/.env*`, `**/test*/**`, `**/fixture*/**`, `**/mock*/**`.

#### 7. Missing Integration Wiring

Detect functions/classes that are defined but never imported or called elsewhere in the project. Applies to:
- Exported functions not imported anywhere
- Route handlers not registered in a router
- Event handlers not subscribed to any emitter
- CLI commands defined but not added to a command group

#### 8. Missing TDD Protocol

For any new function added in a commit, check that a corresponding test file or test function exists. Naming conventions checked:
- `test_<function_name>` in `tests/` or `test_*.py`
- `<function_name>.test.ts` or `<function_name>.spec.ts`
- `describe("<FunctionName>"` block in test files

Missing test coverage for new functions = warning. Missing test file entirely = hard failure.

### Code Slop Scoring

Hard failures block the commit/delivery. Warnings accumulate:
- 0 warnings: clean
- 1-3 warnings: proceed with notice
- 4+ warnings: block until addressed

---

## Mode 2: Content Slop

Detects AI writing patterns in prose. Runs on all `.md`, `.txt` files and all agent content outputs. Every outbound piece — content, outreach, proposals — runs through this before delivery.

### The Eight Rules

**1. Active voice. Human subjects.**
Find the actor. Make them the subject. "The team shipped it" not "It was shipped." "You read the data and concluded" not "The data tells us."

**2. Cut all adverbs (-ly words).**
No -ly words. No really, just, literally, genuinely, honestly, simply, actually, deeply, truly, fundamentally, inherently, inevitably, interestingly, importantly, crucially.

**3. No throat-clearing openers.**
State the point. Not "Here's the thing:" or "Let me be clear:" or "The uncomfortable truth is." Start with the content.

**4. No binary contrasts ("Not X. But Y.").**
"Not X. But Y." becomes "Y." Drop the negation. State the point directly. The reader does not need the runway.

**5. No rhetorical setups ("Here's what I mean:").**
"Here's what I mean:" becomes the meaning itself. "Think about it:" becomes trust the reader. "What if I told you" becomes just tell them.

**6. No vague declaratives.**
"The implications are significant" says nothing. Name the implication. "The stakes are high" says nothing. Name the stake.

**7. No dramatic fragmentation (staccato lists).**
"Speed. Quality. Cost." becomes "Speed, quality, cost." Complete sentences. No staccato drama.

**8. Specificity over abstraction.**
Put the reader in the room. Concrete scenes over narrator-from-a-distance. "You sit down on Monday and realize your pipeline is empty" beats "Teams often struggle with pipeline consistency."

### Banned Phrases (Immediate Removal)

#### Throat-clearing
- "Here's the thing:" / "Here's what X" / "Here's why X"
- "The uncomfortable truth is" / "The real X is"
- "Let me be clear" / "I'll say it again:" / "I'm going to be honest"
- "Can we talk about" / "It turns out"

#### Emphasis crutches
- "Full stop." / "Period." / "Let that sink in."
- "Make no mistake" / "This matters because"

#### Business jargon (replace with plain language)
- navigate → handle / address
- unpack → explain / examine
- lean into → accept / embrace
- landscape → situation / field
- game-changer → significant
- synergy → (delete)
- double down → commit
- deep dive → analysis
- circle back → return to
- moving forward → next

#### Adverbs
really, just, literally, genuinely, honestly, simply, actually, deeply, truly, fundamentally, inherently, inevitably, interestingly, importantly, crucially

#### Filler phrases
- "At its core" / "In today's X" / "It's worth noting"
- "At the end of the day" / "When it comes to" / "In a world where"
- "The reality is" / "What this means is"

#### Meta-commentary
- "As we'll see..." / "Let me walk you through..." / "In this section..."
- "I want to explore..." / "Plot twist:" / "Spoiler:"

#### Vague declaratives
- "The implications are significant"
- "The reasons are structural"
- "The stakes are high" / "The consequences are real"
- "This is genuinely hard" / "This is what X actually looks like"

### Structural Patterns to Remove

#### Binary contrasts → state directly
| Pattern | Fix |
|---------|-----|
| "Not X. But Y." | Say Y. |
| "X isn't the problem. Y is." | "Y is the problem." |
| "The answer isn't X. It's Y." | "Y." |
| "Not just X but also Y" | "X and Y" or just "Y" |
| "stops being X and starts being Y" | "becomes Y" |

#### False agency → name the human
| Pattern | Fix |
|---------|-----|
| "the data tells us" | "we read the data and concluded" |
| "the culture shifts" | "people changed how they work" |
| "the market rewards" | "buyers pay for" |
| "the decision emerges" | "X decided" |
| "the conversation moves toward" | "they steered toward" |

#### Sentence structure
- No em-dashes. Use commas or periods.
- No three-item lists. Use two or one.
- No sentences starting with What/When/Where/Which/Who/Why/How — lead with subject or verb.
- No paragraphs starting with "So".
- Vary sentence length. No three consecutive equal-length sentences.
- No every paragraph ending with a punchy one-liner.

### 5-Dimension Scoring (1-10 each, total out of 50)

| Dimension | What it measures | Signs of failure |
|-----------|-----------------|-----------------|
| **Directness** | How much filtering/softening exists | Qualifiers, hedges, throat-clearing before the point |
| **Rhythm** | Sentence length variation | Three equal-length sentences in a row; staccato fragmentation |
| **Trust** | Authenticity; no false sincerity | "I promise," performative emphasis, manufactured drama |
| **Authenticity** | Specificity and concrete detail | Abstract claims, narrator-from-a-distance, vague declaratives |
| **Density** | Compression; no filler | Phrases that add words without adding meaning |

**Score bands:**
- 43-50: Ship as-is
- 35-42: Minor revision before human review
- 25-34: Significant revision required — do not submit to human
- Below 25: Rewrite from scratch

**Thresholds:**
- General content (Magnus, internal): **35/50**
- Outreach and external-facing (Sander, proposals): **38/50**

Below threshold = revise internally. At or above threshold = proceed to human review.

### Before/After Reference

**Before:** "Here's the thing: building products is hard. Not because the technology is complex. Because people are complex. Let that sink in."
**After:** "Building products is hard. Technology is manageable. People aren't."

**Before:** "In today's fast-paced landscape, we need to lean into discomfort and navigate uncertainty with clarity. This matters because your competition isn't waiting."
**After:** "Move faster. Your competition is."

**Before:** "Speed. Quality. Cost. You can only pick two. That's it. That's the tradeoff."
**After:** "Speed, quality, cost — pick two."

**Before:** "What if I told you that the best teams don't optimize for productivity? Here's what I mean: they optimize for learning. Think about it."
**After:** "The best teams optimize for learning, not productivity."

**Before:** "It turns out that most teams struggle with alignment. The uncomfortable truth is that nobody wants to admit they're confused. And that's okay."
**After:** "Teams struggle with alignment. Nobody admits confusion."

---

## Integration

### Magnus Brand Foundation

After stop-slop scoring, also verify against the Magnus brand foundation (`charters/magnus-brand-foundation.md`):
- No vocabulary from "never use" list
- Sentence structure matches Eric's voice patterns
- Side-by-side test: does this read as Eric or as AI?

Stop-slop clears the AI patterns. Brand foundation checks the voice. Both must pass.

### Configuration

Optional `.stop-slop.yml` in project root:

```yaml
code_slop:
  max_function_sloc: 50
  duplicate_threshold: 0.80
  exclude:
    - "**/migrations/**"
    - "**/generated/**"
    - "**/vendor/**"

content_slop:
  threshold_general: 35
  threshold_outreach: 38
  exclude:
    - "**/CHANGELOG.md"
    - "**/LICENSE*"
```

### CLI Interface

```bash
# Mode 1: Code slop check
stop-slop code --input ./src/ --output ./code-report.json

# Mode 2: Content slop score
stop-slop content --input ./draft.md --output ./score.json

# Content slop score and revise (up to 2 passes)
stop-slop content --input ./draft.md --revise --passes 2 --output ./revised.md

# Outreach mode (higher threshold: 38/50)
stop-slop content --input ./outreach.md --mode outreach

# Run both modes on a commit
stop-slop all --commit HEAD
```
