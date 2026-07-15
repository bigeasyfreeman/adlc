# Skills, loops, kernel, evidence, and approvals

ADLC separates judgment from deterministic control.

- The **skill** is the one public `adlc` router installed into a coding-agent provider.
- A **loop** is a bounded Build, Fix, or Review state machine with declared inputs, gates, terminal states, and recovery behavior.
- The **kernel** owns schema validation, state, action admission, test selection, approvals, idempotency, resume, and evidence records.
- **Evidence** is a replayable command result or versioned artifact tied to a scoped claim.
- **Approval** authorizes a named decision or effect; it is not a general waiver of later gates.

```text
intent → skill routing → loop proposal → kernel admission → effect/test
                                      ↘ block / await approval / escalate
```

The coding agent performs research, diagnosis, planning, implementation, and review judgment. The kernel does not decide product intent or claim that a model followed instructions. Conversely, model confidence cannot replace kernel proof.

Review is read-only. Build and Fix may mutate local files after their preconditions are met. Publish, merge, deploy, destructive recovery, privileged access, and paid execution remain separately approved effects.

`doc_honesty_section`: Architectural separation narrows failure modes; it does not eliminate provider variance or software defects.

`no_overclaim`: “Evidence-bound” means claims point to scoped evidence, not that all outcomes are correct.

`limitations`: External harnesses remain responsible for truthful identity, credentials, and execution context.
