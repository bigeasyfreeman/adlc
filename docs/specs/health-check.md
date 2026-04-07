# Health Check (Doctor Pattern) Spec

## Purpose
Validate critical dependencies before pipeline execution.

## Startup Checks
- Figma token (required only when PRD references Figma links)
- JIRA auth + project access
- Confluence auth + target space access
- Grafana auth + org access
- Slack auth + channel access
- Git repo and branch strategy
- LLM API model availability + budget headroom

## Severity
- **Critical fail (block pipeline):** JIRA, Git, LLM
- **Non-critical fail (warn):** Figma, Grafana, Slack, Confluence (unless phase requires immediate write)

## Output
```json
{
  "status": "blocked",
  "checks": [
    {"dependency": "jira", "status": "pass"},
    {"dependency": "llm", "status": "fail", "reason": "quota exhausted"}
  ],
  "next_action": "resolve critical failures before phase_1"
}
```
