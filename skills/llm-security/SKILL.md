# OWASP LLM Security Skill

> Threat analysis for LLM-integrated systems against OWASP Top 10 for LLM Applications (v2.0, 2025). Covers prompt injection, output handling, agency boundaries, and supply chain risks specific to LLM-powered features.

## Trigger

Invoke when: a task involves LLM calls (`llm_call_fn`), prompt construction, model output parsing, RAG/embedding pipelines, agent orchestration, or any feature where an LLM produces content that drives downstream behavior.

## Input Contract

```json
{
  "task_spec": "TaskSpec from Build Brief",
  "repo_map": "Cached codebase research output",
  "llm_touchpoints": ["list of functions/modules that call LLMs or process LLM output"],
  "agent_topology": "description of agent interactions if multi-agent"
}
```

## OWASP Top 10 for LLM Applications (2025) Checklist

### LLM01: Prompt Injection

- [ ] System prompts do not contain secrets, API keys, or connection strings
- [ ] User-supplied content is clearly delimited in prompts (e.g., triple backticks, XML tags)
- [ ] LLM output is never directly executed as code without sandboxing
- [ ] Indirect injection vectors audited: any data the LLM reads (issues, PRs, comments, file contents) could contain adversarial prompts
- [ ] Privilege separation: the LLM's suggested actions are validated before execution

**Project-specific example:** Issue tracker bodies are the primary indirect injection vector. Issue content flows into decomposition prompts, codegen contexts, and executor instructions. Intake classifiers, scope analyzers, and decomposition gates all parse user-controlled text through LLMs. Each must treat issue content as potentially adversarial.

### LLM02: Sensitive Information Disclosure

- [ ] LLM prompts do not include credentials, tokens, or secrets
- [ ] LLM responses are filtered before logging or display
- [ ] Training/fine-tuning data does not contain PII or proprietary secrets
- [ ] Model outputs are not cached in ways that leak across contexts

**Project-specific example:** Codegen context assemblers that inline source code into prompts must ensure no secrets from `.env` or config files are included. Components that log LLM interactions must apply redaction before writing. Learning systems that store outcomes must scrub sensitive content from stored patterns.

### LLM03: Supply Chain

- [ ] LLM provider APIs are called via authenticated, encrypted channels
- [ ] Model versions are pinned or documented (no silent model swaps)
- [ ] Third-party prompt templates or plugins are vetted
- [ ] Embedding models are from trusted sources with verified integrity

**Project-specific example:** LLM client modules must pin model identifiers. Executor binaries must be verified. Any tool/skill plugins must be from trusted sources.

### LLM04: Data and Model Poisoning

- [ ] Training/fine-tuning data sources are verified
- [ ] Learning system inputs are validated before storage
- [ ] Drift detection exists for model behavior changes
- [ ] Adversarial examples are included in test suites

**Project-specific example:** A learning system that ingests outcomes from automated runs is vulnerable. If an attacker can influence issue content that the system processes, they can poison the learning loop. Outcome validation must check for anomalous patterns before updating policy. Any confidence updater must have bounds on how much a single outcome can shift behavior.

### LLM05: Improper Output Handling

- [ ] LLM output is treated as untrusted input for all downstream processing
- [ ] JSON extraction from LLM output uses safe parsing with fallbacks
- [ ] LLM-generated code is executed only in sandboxed environments
- [ ] LLM-generated content displayed to users is sanitized (XSS prevention)
- [ ] LLM output used in database queries is parameterized

**Project-specific example:** Every module using JSON extraction from LLM responses must handle malformed output gracefully. Decomposition gates that produce slice plans from LLMs must validate them against the actual codebase before creating child issues. PR engines must sanitize LLM-generated descriptions. Executor code output must pass all quality gates before merge.

### LLM06: Excessive Agency

- [ ] LLM-driven actions are scoped to minimum required permissions
- [ ] High-impact actions require human approval (merge to production, delete resources, modify access)
- [ ] Tool/function calling is restricted to an allowlist
- [ ] Rate limits exist on LLM-triggered actions
- [ ] Circuit breakers prevent runaway agent loops

**Project-specific example:** This is the core risk for autonomous development systems. An agent that autonomously creates branches, writes code, opens PRs, and merges needs strong controls: confidence-threshold merge gates (e.g., auto-merge >= 0.85, human gate < 0.60), human-gate patterns for sensitive files, max failure retries, and multi-perspective checks (e.g., Eval Council). Any new capability must explicitly define its agency boundary.

### LLM07: System Prompt Leakage

- [ ] System prompts are designed assuming they will be disclosed
- [ ] No secrets, internal URLs, or architecture details in system prompts that aren't already public
- [ ] System prompts are version-controlled and reviewed

**Project-specific example:** Codegen context assemblers build prompts that include repo structure, file contents, and integration wiring. These prompts should not include deployment credentials, infrastructure details, or private API endpoints. Prompts ARE the spec -- they should be auditable.

### LLM08: Vector and Embedding Weaknesses

- [ ] If RAG is used: access controls on vector store match source document permissions
- [ ] Tenant isolation in multi-tenant embedding scenarios
- [ ] Embedding inputs are sanitized (no injection into embedding space)
- [ ] Retrieval results are filtered by user/agent permission level

**Project-specific example:** If your project does not use RAG or vector stores, mark N/A. If AutoContext or similar features are added, this becomes relevant. Flag for future review.

### LLM09: Misinformation

- [ ] LLM outputs used for decisions are verified against authoritative sources
- [ ] Confidence scoring is applied to LLM judgments
- [ ] Fallback to deterministic logic exists when LLM confidence is low
- [ ] Critical decisions are not made solely on LLM output

**Project-specific example:** An LLM call pattern with deterministic fallback is the primary mitigation. Every intelligence module should fall back to static heuristics when the LLM is unavailable or returns low-confidence results. Multi-perspective validation (e.g., Eval Council) adds a second layer. Learning systems must not amplify hallucinated patterns.

### LLM10: Unbounded Consumption

- [ ] LLM API calls have timeout limits
- [ ] Token/cost budgets exist per operation
- [ ] Retry logic has exponential backoff and max attempts
- [ ] Monitoring and alerting on LLM spend anomalies

**Project-specific example:** Configure timeouts for each LLM-calling component (e.g., `decomposer.timeout_seconds: 300`). Each executor invocation needs a timeout. CI fix loops need max iterations (e.g., `max_iterations_per_pr: 5`). Backend services need max retries (e.g., `max_failure_retries_per_item: 3`). These are the consumption boundaries -- any new LLM call path must define its own.

## Output Contract

```json
{
  "task_id": "string",
  "llm_threat_assessment": {
    "LLM01_prompt_injection": { "risk": "HIGH|MEDIUM|LOW|N/A", "vectors": [], "mitigations": [] },
    "LLM02_disclosure": { "...": "..." },
    "LLM03_supply_chain": { "...": "..." },
    "LLM04_poisoning": { "...": "..." },
    "LLM05_output_handling": { "...": "..." },
    "LLM06_excessive_agency": { "...": "..." },
    "LLM07_prompt_leakage": { "...": "..." },
    "LLM08_vector_weaknesses": { "...": "..." },
    "LLM09_misinformation": { "...": "..." },
    "LLM10_unbounded_consumption": { "...": "..." }
  },
  "overall_risk": "HIGH|MEDIUM|LOW",
  "blocking_findings": [],
  "advisory_findings": []
}
```

## Quality Gates

- LLM06 (Excessive Agency) is ALWAYS applicable for autonomous agent tasks — it must never be marked N/A
- LLM01 (Prompt Injection) is applicable whenever the task processes external text through an LLM
- HIGH risk findings block merge
- Every `llm_call_fn` call site must have a documented fallback path

## Framework Hardening Addendum

- **Contract versioning:** Include `contract_version` in all skill payloads and enforce compatibility before processing.
- **Schema validation:** Validate LLM security findings against `docs/schemas/security-assessment.schema.json` and fail on contract drift.
- **Budget controls:** Any LLM-assisted checks must honor per-skill budgets from `docs/specs/token-budgets.md` with pre-turn checks.
- **Stop reasons:** Return structured stop reasons when analysis is blocked (`budget_exhausted`, `missing_llm_touchpoints`, `contract_mismatch`).

