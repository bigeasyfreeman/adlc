# ADLC — Agentic Development Lifecycle

This project uses the ADLC framework for AI-assisted development.

## Pipeline

The ADLC pipeline converts feature descriptions into production code:

```
Triage → Research → Plan ↔ Review → Code (parallel) → QA → Security → PR → Engineer Review
```

## Working Agreements

- Every acceptance criterion uses Given/When/Then format
- Every coding task must be self-contained (zero-read principle: all context inlined)
- Type 1 decisions (irreversible: data models, public APIs, auth) always escalate to human
- Type 2 decisions (reversible: implementation, internal APIs) decide and document rationale
- Agents emit structured labels: `lgtm`, `revise`, `escalate`, `pass`, `fail`
- Parallel tasks explicitly flagged — serial execution of independent tasks is a velocity failure
- No TODO/FIXME/PLACEHOLDER in shipped code
- Security review runs appsec-threat-model baseline on every change

## Build & Test

- Run tests after every code change
- TDD enforcement: RED → GREEN → REFACTOR per acceptance criterion
- Max 2 fix attempts before escalating
- Max 3 plan review iterations before escalating

## Skills Available

Injectable skills in the skills directory cover:
- **Engineering**: codebase-research, eval-council, codegen-context, tdd-enforcement, systematic-debugging, architecture-pattern, qa-test-data, ci-cd-pipeline
- **Security**: appsec-threat-model, llm-security, agentic-security, api-security, infra-security
- **Product**: prd-generation, ux-flow-builder, figma-integration, gong-customer-evidence
- **Integrations**: jira-ticket-creation, confluence-decomposition, slack-orchestration, grafana-observability, incident-runbook
