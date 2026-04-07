# Version Compatibility Matrix

## Purpose
Track producer/consumer compatibility for each contract surface.

## Matrix
| Contract Surface | Producer Version | Consumer(s) | Compatible Consumer Versions | Notes |
|---|---|---|---|---|
| PRD Template | 1.x | Build Brief Agent, PRD Evaluator | Build Brief 1.x, Evaluator 1.x | Header and table names are strict |
| Repo Map | 1.x | Build Brief, Council, Codegen, Security Skills | All consumers 1.x | Highest fan-out surface |
| Build Brief | 1.x | JIRA, Confluence, QA, CI/CD, Codegen | Consumers 1.x | Section 8 task schema required |
| Eval Verdict | 1.x | Build Brief loop, Slack, Deploy gate | Consumers 1.x | Verdict enum is strict |
| Security Assessment | 1.x | Eval Council Security Auditor | Council 1.x | Shared across five domains |
| Skill MCP I/O | 1.x per skill | Calling skill wrappers | Matching major only | Enforced via `contract_version` |

## Update Policy
Update this matrix for every major or minor contract bump.
