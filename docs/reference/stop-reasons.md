# Stop reasons

ADLC treats stopping as a first-class result.

| Stop class | Meaning | Recovery |
|---|---|---|
| human gate | A named decision or effect needs approval. | Record the decision and rationale, then resume. |
| credentials missing | Required provider or service authentication is unavailable. | Authenticate through the provider; never paste secrets into artifacts. |
| verifier failed | The declared check failed. | Preserve output, diagnose, repair, and rerun. |
| evidence missing | A completion or support claim lacks its required proof. | Collect the named evidence or narrow the claim. |
| permission denied | Action admission refused the proposed effect. | Reduce scope or obtain explicit authority. |
| compatibility/drift conflict | Managed or external state no longer matches the recorded contract. | Compare and reconcile explicitly; do not overwrite. |
| retry exhausted | A bounded loop made no sufficient progress. | Escalate with attempts and residual evidence. |
| external state pending | Merge, deploy, market, human, or service state has not changed yet. | Wait or monitor; do not claim completion. |

Terminal names vary by loop, but every result should say what stopped, what was proved, and the next safe action.

`doc_honesty_section`: A stop reason is evidence of control behavior, not evidence that the underlying issue is solved.

`no_overclaim`: Blocked is never silently converted to pass.

`limitations`: Provider-specific failures may need additional external diagnostics.
