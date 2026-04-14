# LLM vs Deterministic Rebalance

## Principle

ADLC treats deterministic code as the measurement layer and LLMs as the judgement layer.

- Deterministic code extracts facts, validates schemas, computes overlaps, runs commands, measures coverage, and counts mutants.
- LLMs decide only when a measured result still needs interpretation: ambiguous triage, specificity, semantic verifier coverage, surviving-mutant materiality, content slop, and section-policy overrides.
- If the model were materially better tomorrow, measurement code should still exist. If the model were materially better tomorrow, judgement code should become cheaper or more accurate without changing the deterministic harness around it.

## Node Map

| DAG node | Measurement work (deterministic) | Judgement work (LLM) | Why |
|---|---|---|---|
| `triage` | Extract signal features from filenames, task keywords, linked PR refs, and reproducer presence; carry repo path forward. | Classify task, score confidence, and resolve the middle confidence band with `brief-clarity-judge`. | Classification is ambiguous; signal extraction is not. |
| `research` | Gather repo evidence, file paths, and structural references. | None in this rebalance. | Research remains evidence assembly. |
| `plan` | Preserve manifest fields and verifier contracts. | None in this rebalance. | Planning consumes judgement from earlier nodes rather than redoing it. |
| `plan_review` Gate 0 | Validate Build Brief / manifest JSON shape, compute verifier target intersection, tally disagreement arithmetic. | Run `specificity-judge`, `verifier-semantic-judge`, and `section-policy-judge` when the deterministic screens say judgement is needed. | Presence checks and arithmetic are cheap; specificity and semantic coverage are not. |
| `scaffold` | Generate files and wiring from plan outputs. | None. | This node is deterministic by design. |
| `gen_tests` | Translate verifier contract into tests / reproducers and verify target-file intersections. | None in this rebalance. | Test generation stays bound to the deterministic verifier contract. |
| `context_assembly` | Inline task context, files, tests, schemas, and manifest. | None. | Assembly is packaging, not judgement. |
| `code` | Run verifiers, compare expected failure modes by substring / regex / Levenshtein threshold, count passing / failing tests. | Judge only ambiguous expected-failure-mode matches after deterministic comparison cannot decide. | Exact or near-exact matching is measurement; ambiguous mismatch interpretation is judgement. |
| `code_review` | Reuse manifest overlays, verifier artifacts, and deterministic checks. | Eval Council personas remain LLM judgement. | Review is interpretation-heavy. |
| `security` | Run scanners and collect concrete evidence. | Security personas interpret risk and mitigation sufficiency. | Findings need judgement after measurement. |
| `qa` | Run lint, tests, and command verifiers. | None. | Pure measurement. |
| `test_strength` | Detect language, run coverage on changed lines, run mutation tooling, batch surviving mutants. | `mutant-materiality-judge` classifies surviving mutants as trivial or material. | Coverage and kill-rate are measurement; surviving-mutant importance is judgement. |
| `slop_gate` | Apply regex / pattern first-pass filters. | `slop-judge` decides whether non-regex prose is still filler, passive evasion, or tautology. | Regex catches obvious slop; residual prose quality needs judgement. |
| `pr_prep` | Assemble package, copy evidence, preserve DoD results. | None in this rebalance. | Packaging is deterministic. |
| `engineer_review` | Surface prior outputs. | Human judgement. | Human gate remains the final override. |

## Judge Inventory

| Judge skill | Path | Model class slot | Expected calls / run | Cost guard |
|---|---|---|---|---|
| Brief clarity | `skills/brief-clarity-judge/SKILL.md` | `fast_judge` | 0-1 | 700 max tokens / call |
| Specificity | `skills/specificity-judge/SKILL.md` | `fast_judge` | 1-4 | 900 max tokens / call |
| Verifier semantic | `skills/verifier-semantic-judge/SKILL.md` | `fast_judge` | 0-4 | 650 max tokens / call |
| Slop | `skills/slop-judge/SKILL.md` | `fast_judge` | 0-3 | 750 max tokens / call |
| Section policy | `skills/section-policy-judge/SKILL.md` | `fast_judge` | 0-2 | 700 max tokens / call |
| Mutant materiality | `skills/mutant-materiality-judge/SKILL.md` | `deep_judge` | 0-3 batched calls | 1400 max tokens / call |

## Slot Resolution

Judge skills do not hardcode a runtime name or concrete model. They request a `model_class` slot and let the runtime binding resolve it:

1. `skills/manifest.json` declares `runtime_model_map.<runtime>.fast_judge` and `runtime_model_map.<runtime>.deep_judge` for every modeled agent.
2. Smoke runs dispatch through `tests/smoke/stages/_invoke.sh`, which sources `tests/smoke/adapters/<runtime>.sh`.
3. Production runners mirror the same adapter contract through `WORKFLOW.md` backend commands and the binding rules in `docs/specs/dag-binding.md`.

The adapter layer is therefore the only place that knows how a runtime actually turns a model slot into a live invocation.
