# Fix-loop invoice allocation demo

This fixture contains a reproducible product defect: proportional discount allocation rounds every line independently, so the allocated cents can differ from the invoice-level discount. That breaks the accounting invariant that line allocations must reconcile exactly to the invoice total.

The benchmark copies `starting/` into a clean Git repository, verifies its pinned starting commit, installs the Codex bundle, and executes a live Fix control path. It proves the exact test is red for the intended reconciliation failure, requires the first Codex turn to stop without edits at the human gate, resumes that same session after approval, verifies green, checks the one-file scope, and sends the result to a distinct read-only Codex review session before the completion audit. The fixture contains no expected or canned repair.

Run the published configuration from the ADLC repository root:

```bash
python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json
```

This command makes nine provider calls for three attempts and can take several minutes. Use `--plan --json` to inspect its call, token, timeout, and marginal-cost bounds without execution. Results demonstrate named control properties only for the disclosed fixture, versions, model, harness, and sample; they do not establish universal superiority, future model behavior, or GA readiness.
