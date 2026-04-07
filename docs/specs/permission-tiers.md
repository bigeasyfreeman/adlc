# Permission Tiers Spec

## Tiers
- `unrestricted`: read-only tools (research, evidence lookup, baseline pulls)
- `requires_approval`: mutating non-destructive actions (JIRA create, Confluence create, scaffold writes, git branch)
- `requires_escalation`: destructive/high-risk actions (deploy to production, irreversible migrations, flag kill-switches)

## Decision Flow
1. Resolve tool tier from registry metadata.
2. Apply policy for current phase and actor.
3. If unresolved Type 1 decision exists, block mutating/destructive actions.
4. Persist decision in permission logs and audit trail.

## Minimum Enforcement
- no tier metadata => deny tool
- no decision record => deny execution
- escalation approvals must include approver identity and rationale
