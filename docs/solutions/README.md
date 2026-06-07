# ADLC Solution Learnings

This directory is ADLC's compound engineering learning store. Add entries only when a verified run produced reusable knowledge that should make a future run cheaper or safer.

Rules:

- Use `docs/solutions/_template.md`.
- Validate entries with `python3 scripts/validate_learning_entry.py <path>`.
- Cite source evidence and verifier evidence. A learning without evidence does not belong here.
- Keep entries compact. Future prompts receive IDs, paths, summaries, verifier refs, and source refs, not the full document.
- Do not store secrets, private tokens, credentials, private endpoints, or unsupported environment claims.
- Mark stale conditions up front so refresh can be scoped.

The default workflow works when this directory is empty. Missing or empty learnings are explicit compound-context no-ops, not failures.
