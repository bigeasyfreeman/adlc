# ADLC Graph Research End-to-End Goal Prompt

Use this prompt to run an ADLC change end to end with graph-backed research, optional Beads task memory, context-layer generation, implementation, comprehension review, validation, and closeout.

## Launch

From the ADLC repo or target repo:

```bash
cat /Users/eric/adlc/ADLC_GRAPH_RESEARCH_E2E_GOAL_PROMPT.md | codex exec -C /path/to/target-repo -m gpt-5-codex -c model_reasoning_effort='"xhigh"' -
```

Replace `/path/to/target-repo` with the repo to change.

## Prompt

You are executing an ADLC end-to-end implementation goal. Work in the current target repo. Do not stop at a plan unless blocked by missing information that cannot be recovered from the repo, graph, issue tracker, or tests.

### User Goal

Implement the following request:

```text
[PASTE THE FEATURE, BUG, PRD, TICKET, OR CHANGE REQUEST HERE]
```

Known constraints, if any:

```text
[PASTE CONSTRAINTS, OUT OF SCOPE, TARGET TICKETS, DEADLINES, OR ACCEPTANCE CRITERIA HERE]
```

### Required ADLC Workflow

Follow this workflow in order. Keep artifacts concrete and repo-local where appropriate.

1. **Repo Safety Preflight**
   - Run `git status --short`.
   - Identify user WIP and preserve it.
   - Do not revert unrelated changes.
   - Record the current branch and `git rev-parse HEAD`.

2. **Graph Research Gate**
   - If `graphify-out/wiki/index.md` exists, navigate it first.
   - Else if `graphify-out/GRAPH_REPORT.md` exists, read it before broad source search.
   - Compare the Graphify report commit against `git rev-parse HEAD`.
   - If stale or missing and Graphify is available, run `graphify update .`.
   - Run graph queries before broad grep:
     - `graphify query "What modules and interfaces are relevant to this change?"`
     - `graphify query "What existing implementation should be reused or extended?"`
     - `graphify query "What backward compatibility and forward compatibility paths could this affect?"`
     - `graphify query "What cross-module paths create dark-code risk for this request?"`
   - Treat Graphify as a map, not proof. Directly verify critical claims in source, schemas, tests, or docs.
   - If Graphify cannot run, continue with explicit reduced-confidence notes.

3. **Optional Beads Task Memory**
   - If `.beads/` exists or `bd` is available, run `bd prime`.
   - Use `bd ready --json` for ready-work context if this is a ticket decomposition or multi-slice task.
   - Use Beads only for task memory, dependencies, blockers, and handoff notes. Do not treat it as architecture evidence.

4. **Codebase Research**
   - Build a short repo map for the relevant area: modules, interfaces, data flows, tests, owners if discoverable, and existing patterns.
   - Identify reuse opportunities and cite exact files.
   - Identify tech debt only when it is evidence-backed and relevant to this request.
   - Separate supported, unsupported, and contradicted claims.

5. **Dark-Code Risk Check**
   - Check for structural dark-code risk: emergent cross-service behavior, untyped data flows, non-engineer workflows touching production data, unowned behaviors.
   - Check for velocity dark-code risk: AI-generated or fast-shipped code without comprehension artifacts, missing specs, missing ownership, or review depth mismatch.
   - If team, ownership, AI-usage, or incident data is unavailable, write `insufficient data to assess` instead of guessing.
   - Convert confirmed risk into Build Brief constraints or context artifact tasks.

6. **Build Brief**
   - Produce a concise Build Brief before coding.
   - Include:
     - scope and out of scope
     - graph research evidence
     - reuse paths
     - compatibility constraints, including backward, forward, rollback, and downgrade behavior
     - task breakdown with dependencies
     - verification spec for each task
     - context-layer artifact requirements
     - open questions and Type 1 decisions
   - Escalate only Type 1 decisions that are irreversible or costly to reverse: data models, public APIs, auth, tenancy, external integration commitments.

7. **Context Layers**
   - For any new or materially changed module, service, public interface, schema, event, queue, persistence behavior, retry behavior, ownership boundary, or graph-identified dark-code hotspot, create or update:
     - module manifest or `CONTEXT.md`
     - behavioral contracts near interfaces or as markdown
     - decision log or ADR
   - Do not invent rationale. If unknown, write: `Reasoning unknown. Treat as load-bearing; do not modify without investigation.`

8. **Implementation**
   - Implement the smallest correct change.
   - Reuse cited implementations and patterns.
   - Do not create parallel helpers, duplicate abstractions, placeholder code, or speculative future architecture.
   - Keep changes scoped to the Build Brief.

9. **Comprehension Gate**
   - Review the diff for understanding, not style.
   - Produce a comprehension artifact with:
     - change summary
     - findings table
     - blast radius map for medium+ risk
     - questions before merging
     - verdict: `CLEAR`, `REVIEW REQUIRED`, or `HOLD`
   - If verdict is `REVIEW REQUIRED`, answer every question with cited evidence or revise.
   - If verdict is `HOLD`, stop and explain the senior-review blocker.

10. **Validation**
   - Run the primary verifier first.
   - Run relevant unit, integration, lint, format, smoke, or E2E checks.
   - Run repo-specific contract checks when present.
   - Run `git diff --check`.
   - After code changes, run `graphify update .` if Graphify is available.

11. **Closeout**
   - Summarize changed files and behavior.
   - Include validation commands and results.
   - Include Graphify freshness status.
   - Include unresolved risk, open questions, or skipped checks.
   - Separate shipped code from local-only planning artifacts.

### Output Requirements

Keep the final answer concise and evidence-backed:

- What changed
- Where it changed
- What validation passed or failed
- Graphify/Beads status
- Any remaining blockers or risks

Do not claim compatibility, coverage, ticket closure, PR readiness, or merge readiness without direct evidence.

