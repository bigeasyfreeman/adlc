# Fix-loop invoice allocation demo

This fixture contains a reproducible product defect: proportional discount allocation rounds every line independently, so the allocated cents can differ from the invoice-level discount. That breaks the accounting invariant that line allocations must reconcile exactly to the invoice total.

The benchmark copies `starting/` into a clean Git repository, verifies its pinned starting commit, installs the Codex bundle, and executes the public Fix control path. It proves the test is red for the intended reconciliation failure, stops and resumes at a human gate without replaying a completed side effect, applies the bounded repair in `expected/`, verifies green, reviews the one-file diff, and runs a separate-session completion audit.

Run the published configuration from the ADLC repository root:

```bash
python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json
```

The configuration is deterministic and invokes no model or hosted provider. Its token and provider-cost range is therefore exactly zero. It demonstrates ADLC's named control properties on this fixture; it does not establish universal superiority, future model behavior, or GA readiness.
