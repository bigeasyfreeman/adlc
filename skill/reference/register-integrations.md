# Internal Integration Pack Register

Load this register only when the target task explicitly requires one of these systems and the needed local provider or tool is available.

| Integration | Migrated legacy sources | Bounded contract |
| --- | --- | --- |
| GitHub, Jira, Linear, Notion, or Confluence | `github-issue-creation`, `jira-ticket-creation`, `linear-ticket-creation`, `notion-decomposition`, `confluence-decomposition` | Draft from verified source evidence, preserve identifiers and acceptance criteria, show the exact payload, and require approval before external writes. |
| Slack or customer evidence | `slack-orchestration`, `gong-customer-evidence` | Minimize private data, distinguish quotation from inference, show the exact message, and require approval before sending. |
| Figma or UX artifacts | `figma-integration`, `ux-flow-builder` | Verify the referenced design and states, record missing decisions, and do not invent assets or product policy. |

An unavailable integration is a blocker or a draft-only outcome, never permission to simulate a successful external action.
