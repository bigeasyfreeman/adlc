# ADLC Skill-and-Loop Productization Strategy

Status: proposed execution contract  
Research date: 2026-07-14  
Repository snapshot: `fcf6b3e` plus the uncommitted public-hygiene and runtime-hardening work already present in the worktree  
Companion Build Brief: `docs/build-briefs/adlc-skill-loop-productization.json`

## Executive decision

Migrate ADLC by changing its product surface, not by replacing its verified kernel.

The target is one installable `adlc` skill that routes a small command vocabulary into three explicit loops—Build, Fix, and Review—while the existing schema, state, permission, verification, queue, worktree, and evidence machinery remains the deterministic execution kernel.

The public product promise is:

> Run repeatable build, fix, and review loops with your coding agent, with every completion claim tied to evidence.

This is the Impeccable pattern adapted to engineering control:

- one canonical skill instead of 55 independently exposed skills;
- short command references loaded only when a command is invoked;
- project context loaded before action;
- deterministic scripts for work that should not depend on model judgment;
- one canonical source compiled into provider-specific installations;
- behavioral tests that inspect tool traces under pressure, not only prose or schema shape;
- a public README that leads with an outcome, a one-command install, and a reproducible demonstration.

ADLC should not become a clone of Impeccable. Impeccable's product is design quality. ADLC's defensible product is evidence-bound engineering execution across agent harnesses.

## Why this is the correct migration

ADLC already has the difficult control-plane parts: a stateful workflow, schema-backed artifacts, explicit approval points, deterministic gates, action admission, queue/worktree primitives, completion auditing, and provider adapters. Rebuilding those as prose loops would discard the strongest part of the project.

The current weakness is the product interface:

- 55 skills are installed as peer concepts even though most users need a small set of outcomes.
- More than 60 CLI commands are visible at the front door.
- The README asks the user to understand the machinery before experiencing a successful run.
- public provider claims and local implementation state have diverged in the past;
- installation is checkout-oriented rather than release-oriented;
- schema and fixture coverage is materially stronger than recorded live generative coverage;
- public evidence does not yet make the framework easy to trust, explain, or demonstrate.

The migration therefore inverts the interface:

```text
User intent
   |
   v
one `adlc` skill and a small command router
   |
   +--> Build loop
   +--> Fix loop
   +--> Review loop
   |
   v
ADLC deterministic kernel
schemas | state | permissions | gates | queue | worktrees | evidence
   |
   v
provider adapter and coding harness
```

## Research basis

### Impeccable

The current Impeccable repository uses one canonical skill source, command-specific reference files, a required context loader, deterministic detector scripts and hooks, a compiler that creates provider-specific bundles, install/update/link commands, static installation tests, and provider-backed behavioral scenarios that assert tool traces. Its public documentation pairs a short promise with install instructions, command references, examples, tutorials, and a concrete case study.

The useful lesson is not “put everything in Markdown.” It is “make one teachable front door, load only the knowledge required for the current command, and prove behavior where the model is tempted to skip the method.”

Research refs:

- <https://impeccable.style/docs/>
- <https://github.com/pbakaus/impeccable>
- inspected repository commit `8259c28209b92792005cec14dad573df39f68eaf`

### ADLC

The repository graph reports 333 indexed files, 13,996 nodes, and 17,152 relationships at the audited snapshot. Direct inspection found 55 manifest skills, 13 agent definitions, more than 60 CLI commands, a large deterministic runtime, and existing Build/Fix loop concepts. The current worktree also contains an unfinished but valuable public-hygiene and runtime-hardening change: honest provider wording, retry enforcement, approval records, community files, CI expansion, and stale-doc archival.

That in-flight change is a prerequisite, not disposable work. It must be reviewed, validated, and landed as a clean baseline before the skill migration begins.

## Product definition

### Category

ADLC is an evidence-bound control plane for AI-assisted software delivery.

It is not:

- a replacement coding agent;
- a general multi-agent chat framework;
- a promise that every supported harness behaves identically;
- a compliance certification product;
- a collection of unrelated domain skills.

### Initial user

The first user is a senior engineer or hands-on engineering lead who already uses Claude Code or Codex and wants repeatable, interruptible, auditable execution without writing a new orchestration prompt for every task.

The first team use case is a small engineering organization that needs to know what an agent changed, which gates actually ran, what remains unproven, and where human approval is required.

### Initial wedge

The wedge is the Fix loop because it has the clearest demonstration:

1. capture a real failing behavior;
2. reproduce it before changing code;
3. create a verifier that fails for the right reason;
4. implement the smallest bounded repair;
5. run independent review and completion checks;
6. produce a PR-ready evidence package;
7. interrupt and resume once to prove durable state.

Build and read-only Review ship in the same product vocabulary, but the first public proof should be a real Fix run.

## Target public interface

### One skill

The source package should have this shape:

```text
skill/
  SKILL.src.md
  reference/
    command-init.md
    command-shape.md
    command-build.md
    command-fix.md
    command-review.md
    command-harden.md
    command-ship.md
    command-status.md
    command-resume.md
    command-doctor.md
    command-learn.md
    register-product.md
    register-engineering.md
    register-security.md
    register-release.md
  scripts/
    context.py
    detect.py
    verify-install.py
```

`SKILL.src.md` owns only the promise, trigger language, command router, universal safety rules, and context-loading protocol. Detailed procedures live in one-level references and are loaded only for the selected command.

The installed skill appears as `adlc` in each supported harness. The 55 current skill directories become one of four things:

1. command reference content;
2. an internal capability pack selected by applicability;
3. a deterministic kernel command;
4. deprecated or deleted material with a recorded replacement.

Nothing is removed until the mapping ledger identifies its replacement, consumers, compatibility window, and proof.

### Public commands

| Command | User outcome | Mutation posture |
|---|---|---|
| `/adlc init` | Detect repo instructions and establish ADLC project context | writes only reviewed `.adlc` project config |
| `/adlc shape` | Turn ambiguous intent into a bounded, decision-ready brief | artifacts only |
| `/adlc build` | Run the Build loop from accepted intent to PR-ready evidence | gated mutation |
| `/adlc fix` | Run the Fix loop from reproduction to PR-ready evidence | gated mutation |
| `/adlc review` | Inspect a change and return evidence-backed findings | read-only by default |
| `/adlc harden` | Run applicable security, reliability, compatibility, and quality gates | gated mutation only when explicitly requested |
| `/adlc ship` | Prepare the release or PR package and stop at external approval | external mutation requires approval |
| `/adlc status` | Explain current state, blockers, evidence, and next action | read-only |
| `/adlc resume` | Continue the persisted run without replaying completed side effects | gated mutation |
| `/adlc doctor` | Verify install, provider bundle, runtime, schemas, and credentials posture | read-only |
| `/adlc learn` | Propose a reusable learning from verified evidence | local proposal; promotion gated |

The existing low-level commands remain available during the compatibility window. They are documented under an advanced reference rather than presented as the onboarding path.

### Project context

`adlc init` should discover `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, nested instruction files, test commands, and package metadata. It should not overwrite them.

ADLC-owned context lives in:

```text
.adlc/PROJECT.md       # product intent, users, vocabulary, non-goals
.adlc/ENGINEERING.md   # architecture, conventions, validation, release posture
.adlc/config.json      # provider, loop, approval, privacy, and compatibility settings
```

The context loader returns a bounded manifest of source paths, hashes, relevant excerpts, warnings, and missing decisions. The skill consumes that manifest before it routes a command.

This preserves Impeccable's context-first behavior without assuming ADLC owns root-level product files in every target repository.

## Loop contracts

### Build

```text
shape intent -> research -> plan -> human intent gate -> test/scaffold
-> implement -> independent review -> QA/hardening -> completion audit
-> PR/release package -> human external-action gate
```

Exit success requires a clean scoped diff, verifier evidence, resolved required findings, a completion audit by an identity distinct from the executor, and an explicit record of unsupported claims.

### Fix

```text
capture -> confirm -> reproduce -> diagnose -> failing verifier
-> smallest repair -> regression verification -> independent review
-> completion audit -> PR/release package
```

Exit success requires red-before-green evidence. If the defect cannot be reproduced, the loop stops as `needs_evidence`; it must not silently become a speculative refactor.

### Review

```text
establish intent -> inspect diff and contracts -> run selected verifiers
-> rank findings -> check claims -> report
```

Review is read-only unless the user separately invokes Fix. Findings must include evidence, impact, and a bounded repair direction. “Looks good” is not evidence.

### Improvement loop

This is internal and never an automatic mutation path:

```text
observe failure or friction -> capture trace -> propose skill/gate change
-> run static and behavioral holdouts -> independent review
-> promote, hold, retire, or revert
```

Every gate records whether it ran, blocked, found a defect, or produced no finding. A non-security gate with ten eligible zero-finding runs enters retirement review; it is not automatically deleted. Security, privacy, destructive-action, and human-approval gates are exempt from automatic retirement proposals.

## Provider architecture

### Canonical source and compilation

Provider files must be generated from one source. The compiler owns path layout, frontmatter, hooks, command aliases, and provider-specific limits. Generated outputs are never hand-edited.

Initial build targets:

- Claude Code: `.claude/skills/adlc/` and supported project hooks;
- Codex: `.agents/skills/adlc/` plus `AGENTS.md` integration where required.

Cursor, Factory, Antigravity, and other targets remain experimental until both installation conformance and behavioral conformance pass. A generated directory is not evidence that an execution adapter works.

### Conformance states

Each provider is reported independently across four dimensions:

| Dimension | Proof |
|---|---|
| Installation | clean install, update, link, uninstall, and digest verification |
| Invocation | provider actually selects the `adlc` skill for trigger scenarios |
| Behavior | trace scenarios show required context, gates, and stop behavior |
| End to end | a real Build, Fix, or Review loop reaches the claimed terminal state |

Public support labels are `unsupported`, `experimental`, `beta`, or `supported`. The README is generated from the latest signed conformance evidence so prose cannot drift from proof.

## Distribution and installation

ADLC should ship as a Python CLI because the runtime is already Python and the current package metadata is close to publishable. At research time, the PyPI project URL for `adlc` did not resolve, while the npm name `adlc` was occupied by another package. Name availability must be rechecked immediately before publication.

Desired install path:

```bash
pipx install adlc-engineering
# or
uv tool install adlc-engineering

adlc install --provider claude --scope project
adlc doctor
```

Required lifecycle commands:

- `adlc install`
- `adlc update`
- `adlc link` for local development
- `adlc uninstall`
- `adlc doctor`

Install is transactional: stage, validate, replace, record a manifest, and retain rollback metadata. It must not overwrite unmanaged skill files or target-repo instructions without a diff and approval.

## Security and privacy posture

- Hooks are opt-in, provider-native where possible, visible in the install diff, and removable.
- The skill cannot widen tool permissions; all actions still pass the ADLC action-admission policy.
- Credentials are provider-owned and never copied into ADLC artifacts.
- Traces and benchmark artifacts are redacted before publication.
- Telemetry is off by default. Local run metrics are always available; anonymous product telemetry is a separate explicit opt-in.
- Install, update, publish, PR creation, merge, deploy, and external tracker mutation retain explicit approval boundaries.
- Provider-generated files carry source version and digest metadata.

## Behavioral validation

Static validation alone is insufficient for a behavioral skill. ADLC needs a trace-based suite modeled on Impeccable's pressure scenarios.

Minimum scenario groups:

1. ambiguous feature request triggers Shape before mutation;
2. urgent bug request still reproduces before repair;
3. “skip tests” does not bypass required verifier evidence;
4. review remains read-only;
5. missing credentials stop cleanly without claiming provider success;
6. destructive or external actions stop at approval;
7. interrupt and resume do not replay completed side effects;
8. target-repo conventions override generic ADLC defaults;
9. unsupported provider does not get labeled supported;
10. context remains bounded and command-specific;
11. executor and completion auditor identities differ;
12. a generated-output change runs its quality gate before promotion.

Assertions should inspect tool calls, state transitions, evidence paths, stop reasons, and absence of forbidden mutations. Text rubrics are secondary.

The suite has three layers:

- fixture layer: deterministic and credential-free on every PR;
- provider layer: scheduled and manually runnable with credentials;
- canonical real-work layer: release-blocking recorded runs with raw redacted traces.

## Repository and documentation productization

### Phase-zero cleanup

Before migration work starts:

1. inventory the current dirty worktree by owner and intent;
2. run the current CI and public-hygiene checks;
3. split unrelated changes if needed;
4. review and land the public-hygiene/runtime-hardening baseline;
5. ensure the default branch and public GitHub README reflect the landed truth;
6. create a release tag only after a clean checkout reproduces the validation.

The migration must not be layered onto an unreviewed 43-file diff. That would make failures impossible to attribute and would mix public-truth fixes with a new interface.

### README contract

The root README becomes a product landing page, not the full operator manual. Its order is fixed:

1. one-sentence promise;
2. 30-second install;
3. 5-minute Fix example;
4. what the three loops do;
5. current provider support table generated from evidence;
6. a short “how it works” diagram;
7. safety and human-approval boundaries;
8. proof links: demo, benchmark, raw run evidence;
9. documentation, contribution, security, and roadmap links;
10. honest beta or GA status.

Deep schema, command, and gate material moves to documentation. The README must not contain claims that cannot be regenerated from repository evidence.

### Documentation site

Publish versioned documentation from repository Markdown through MkDocs Material and GitHub Pages. Keep source in the repository and link every version to its tag.

Required navigation:

- Start here
  - What ADLC is
  - Installation
  - First Fix loop
- Concepts
  - skills, loops, kernel, evidence, approvals
- Guides
  - Build
  - Fix
  - Review
  - Resume
  - Provider setup
- Reference
  - public commands
  - configuration
  - artifacts and schemas
  - stop reasons
- Trust
  - support matrix
  - security and privacy
  - benchmark method and raw evidence
  - compatibility and deprecation
- Contribute
  - development
  - skill/reference authoring
  - behavioral scenario authoring
  - release process

Every command page contains purpose, preconditions, example, outputs, stop states, side effects, approval points, and troubleshooting.

### Open-source hygiene

The release branch must contain and validate:

- license, code of conduct, contribution guide, security policy, changelog;
- issue and pull-request templates;
- supported Python versions and locked release tooling;
- dependency and secret scanning;
- code ownership or maintainer policy;
- release notes and semantic versioning policy;
- reproducible source and wheel builds;
- an archived, clearly labeled historical-doc area;
- no local paths, credentials, generated self-installs, stale smoke reports, or private process artifacts.

## Demo, proof, and GTM

### Demonstration asset

Ship a small, intentionally flawed public fixture repository. The ten-minute demo must run from clean install to a PR-ready Fix result and include one interrupt/resume cycle. Publish:

- the starting commit;
- the exact user prompt;
- redacted event trace;
- state and approval records;
- before/after test output;
- final diff and review findings;
- runtime, token, and cost range;
- a replay command.

### Benchmark

The benchmark is not “ADLC beats every other framework.” It measures whether the claimed controls work.

Initial scorecard:

| Metric | Release signal |
|---|---|
| task completion | required terminal state reached |
| verifier validity | test fails before and passes after for the intended reason |
| resume integrity | no completed side effect repeats |
| claim accuracy | completion audit finds no contradiction |
| scope control | no out-of-scope product diff |
| human load | count and duration of required decisions |
| time and cost | median plus spread, never a single best run |

Public results require at least three runs per published configuration, raw redacted evidence, model/provider/version disclosure, and failure publication. Comparisons to external frameworks are allowed only when the same task, environment, and scoring method can be rerun by a third party.

### Launch narrative

The brand thesis is:

> Better agents do not eliminate engineering process. They make it possible to encode the process as a small set of evidence-bound loops instead of an endless prompt chain.

Launch assets:

1. GitHub repository and tagged beta release;
2. documentation site;
3. ten-minute demo video and terminal recording;
4. technical article explaining the proof-inversion problem and the migration;
5. benchmark methodology plus raw runs;
6. concise launch posts for LinkedIn/X, Hacker News, and relevant engineering communities;
7. issue-based feedback path and a public roadmap limited to validated demand.

The interview version is a four-part story: the initial overbuilt control plane, the diagnosis, the facade-first migration, and the measured proof. The public product version leads with the successful loop, not the internal history.

### Funnel and metrics

Primary funnel:

```text
README visit -> install -> doctor pass -> first loop started
-> first loop reaches honest terminal state -> second loop within 14 days
```

Release metrics:

- install success rate by provider;
- median time to `doctor` pass;
- median time to first successful Fix loop;
- loop terminal-state distribution;
- resume success and duplicate-side-effect rate;
- gate catch rate and zero-finding count;
- documentation search exits and broken-link rate;
- returning projects, not only stars;
- provider-specific support failures;
- security/privacy incidents: target zero.

Telemetry remains opt-in. The same metrics must be computable locally from redacted run reports so product validation does not depend on surveillance.

## Execution program

### Phase 0 — establish a trustworthy baseline

Deliver the current truth, hygiene, retry, approval, and conformance work as a reviewed clean change. Prove the default branch and public README match. Freeze new gates until the first canonical run is recorded.

Exit gate: clean checkout, CI green, public-hygiene green, default branch truthful, rollback commit known.

### Phase 1 — freeze the product contract

Create `PRODUCT.md`, editorial style, command vocabulary, support labels, context-file contract, architecture decision records, and the legacy-surface mapping ledger.

Exit gate: one promise, one initial user, one wedge, one command taxonomy, every current skill and agent classified.

### Phase 2 — build the facade and loops

Create the canonical skill source, command references, context loader, and public Build/Fix/Review coordinators. Delegate to existing deterministic commands rather than duplicating gate logic.

Exit gate: fixture scenarios select the right command, load bounded context, and reach the correct deterministic stop state.

### Phase 3 — compile and distribute

Create provider compiler, generated-bundle verification, Python entry point, install/update/link/uninstall/doctor lifecycle, transactional manifests, and consented hooks.

Exit gate: clean virtual environments can install, validate, update, roll back, and uninstall without touching unmanaged files.

### Phase 4 — prove behavior and migrate internals

Add trace-based pressure scenarios, live Claude/Codex conformance, canonical real Fix/Build/Review runs, and the legacy skill compatibility layer. Retire only surfaces with mapped replacements and evidence.

Exit gate: public support table is generated from passing conformance evidence; at least one real Fix run is replayable; old entry points either work or emit a dated migration message.

### Phase 5 — publish the product surface

Rewrite README, publish docs, add examples, record the demo, publish benchmark method/results, complete open-source hygiene, and automate signed releases.

Exit gate: a new user can install and complete the demo from public docs in under ten minutes without repository-owner help.

### Phase 6 — controlled beta and GA

Run a public beta, triage actual usage, fix release blockers, and graduate only the providers and loops that meet the evidence threshold.

GA gate:

- two supported providers only if both pass all four conformance dimensions;
- three recorded runs per published provider/loop configuration or an explicit beta label for thinner evidence;
- zero unresolved critical/high security findings;
- no contradicted public claim;
- install and rollback rehearsed from the published artifact;
- docs and README validated against the released version;
- a human approves publication, package upload, GitHub release, and launch communications.

## Work-item dependency map

```text
MIG-001 baseline
   -> MIG-002 product contract
      -> MIG-003 canonical skill/context
         -> MIG-004 loop command references
            -> MIG-005 runtime facade
               -> MIG-006 provider compiler and install lifecycle
                  -> MIG-007 hooks/action admission
                     -> MIG-008 behavioral conformance
   -> MIG-009 legacy migration/deprecation
   -> MIG-010 README and docs information architecture
      -> MIG-011 documentation site
   -> MIG-012 demo and benchmark
   -> MIG-013 release automation and supply chain
      -> MIG-014 launch kit and feedback loop
         -> MIG-VAL go-live validation
```

No execution wave may contain more than six tasks. MIG-001 is deliberately serial because it establishes the baseline for every later verifier.

## Time and staffing envelope

This is larger than a prompt rewrite. For one engineer using ADLC and coding agents, the expected range is six to ten engineer-weeks, commonly four to seven calendar weeks when independent documentation, packaging, provider, and test work can run in parallel. Provider credentials, package-name ownership, and live behavioral failures can extend the range.

Suggested staffing roles, even when one person fills several roles:

- product owner: promise, user, launch, Type 1 decisions;
- runtime owner: facade, state, permissions, compatibility;
- skill owner: canonical skill, references, context, behavioral tests;
- release owner: packaging, CI, docs publication, supply chain;
- independent auditor: completion and public-claim verification.

## Kill, keep, and defer rules

Keep:

- deterministic gates with observed catches or non-removable safety authority;
- schema-backed state and artifacts;
- approval, permission, queue, worktree, completion-audit, and resume semantics;
- provider-independent source contracts;
- verified learning and compatibility evidence.

Kill or demote:

- peer-level public exposure for internal skills;
- duplicated prompt procedures that a command reference or deterministic script owns;
- provider support claims inferred from file presence;
- stale smoke artifacts and historical specs presented as current;
- unrelated domain skills from the default product install;
- README material that belongs in reference docs.

Defer until usage proves demand:

- browser QA as an ADLC-native subsystem;
- a hosted control plane;
- marketplace or enterprise administration;
- providers beyond Claude and Codex;
- automatic gate deletion;
- competitive winner claims.

## Immediate next move

Do not begin by rewriting all 55 skills. Execute MIG-001, then MIG-002, then a vertical Fix-loop slice across MIG-003 through MIG-008 and MIG-012. That slice must end in a clean-install, interruptible, replayable real Fix run.

If that proof fails, repair the facade or kernel before migrating more content. If it succeeds, use the trace and user friction to decide which legacy skills become references, internal packs, deterministic commands, or deletions.

## Planning validation record

The companion Build Brief was checked against the current ADLC runtime on 2026-07-14:

- `validate-artifact --schema build-brief`: valid, zero schema errors;
- `emit-work-items --dry-run --require-ready`: ready, 16/16 artifacts, zero readiness issues, 45 dependency links;
- `clarity-gate --mode headless`: pass, 10 ledger entries, five blindspots, zero blocking questions;
- `module-plan-check`: pass, seven required module plans, eight explicit not-applicable decisions, zero issues;
- `slop-gate`: pass, two generated-agent surfaces with blocking behavioral gates;
- `repo-conventions-check`: pass against 26 freshly extracted rules; six rules are carried directly and twenty duplicate or initial-provider-out-of-scope rules have explicit waivers;
- `bin/adlc ci --json`: pass, 10/10 suites, including 326 CLI assertions, 536 contract assertions, 131 setup assertions, provider-free public acceptance, controlled OS-12 acceptance, 126 backtest assertions, public hygiene, and Python compilation.

The current CI result is useful evidence that the existing deterministic kernel and provider-free fixture lanes are viable. It is not evidence that the proposed one-skill facade, package distribution, live Claude/Codex behavior, documentation site, benchmark, or public release has shipped. Those claims remain owned by the Build Brief tasks and final independent validator.

## No-overclaim boundary

This strategy is implementation-ready planning, not evidence that the migration or public release already exists. The current default branch does not yet expose the proposed one-skill interface, package install, docs site, behavioral matrix, or replayable public demo. “Production-ready,” “supported provider,” and “GA” remain blocked until the corresponding release gates produce actual evidence.
