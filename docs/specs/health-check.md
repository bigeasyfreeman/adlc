# Health Check (Doctor Pattern) Spec

## Purpose
Validate critical dependencies before pipeline execution.

## Startup Checks
- Figma token (required only when PRD references Figma links)
- Configured work-item emitter MCP installed locally, authenticated, and exposing required logical capabilities
- Configured document emitter MCP installed locally, authenticated, and exposing required logical capabilities
- Grafana auth + org access
- Slack auth + channel access
- Git repo and branch strategy
- LLM API model availability + budget headroom

## Severity
- **Critical fail (block pipeline):** configured work-item emitter MCP, Git, LLM
- **Non-critical fail (warn):** Figma, Grafana, Slack, configured document emitter MCP (unless phase requires immediate write)

## Output
```json
{
  "status": "blocked",
  "checks": [
    {"dependency": "github_mcp_provider", "status": "pass"},
    {"dependency": "llm", "status": "fail", "reason": "quota exhausted"}
  ],
  "next_action": "resolve critical failures before phase_1"
}
```
