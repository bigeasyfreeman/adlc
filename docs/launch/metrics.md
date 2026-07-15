# Local-first beta metrics

ADLC 0.9.0 collects no product telemetry. Operators may calculate these metrics
from sanitized local install manifests, doctor results, and run reports. Raw
target-repository content, prompts, diffs, filenames, credentials, and user
identity are never metric fields.

## Funnel definitions

| Metric | Numerator | Denominator | Window | Zero denominator |
| --- | --- | --- | --- | --- |
| Install success rate | transactional installs with terminal `pass` | recorded install attempts | review week | `null` |
| Doctor pass rate | installs whose required doctor checks pass | completed installs | review week | `null` |
| First-loop activation | projects whose first Build or Fix reaches `pr_ready` with evidence | projects with a passing doctor and an eligible first loop | 7 days from doctor | `null` |
| Median time to first PR-ready | median of `first_pr_ready_at - doctor_passed_at` | activated projects with both timestamps | 7 days from doctor | `null` |
| Returning-project rate | activated projects starting another eligible loop | activated projects observed for a full 7 days | trailing 7-day cohort | `null` |
| Evidence-complete rate | `pr_ready` reports whose declared evidence refs resolve | all `pr_ready` reports | review week | `null` |

Counts are deduplicated by an operator-generated random local project ID. Never
derive that ID from a repository URL, filesystem path, account name, or source
content. A local summary may contain event name, coarse tool version, timestamp,
terminal class, duration bucket, and verifier count.

## Local calculation

Export a sanitized JSON array from local records, review it, and calculate the
table above in an operator-controlled environment. Keep the raw export out of
Git unless it is a purpose-built public fixture. Weekly review records only
aggregate counts, rates, declared exclusions, and missing-data notes.

## Optional anonymous exporter proposal

No exporter or network endpoint ships in 0.9.0. A future proposal must remain
off by default, show the exact payload before consent, require explicit opt-in,
support immediate revocation and local deletion, exclude source content and
stable identity, document retention, and pass separate product-owner and
security/privacy review. Consent to coding-agent provider processing is not
consent to ADLC telemetry.

Stars, downloads, and impressions may be contextual signals; none is the
primary product metric. The beta decision metric is evidence-complete first-loop
activation followed by a returning project within the scoped cohort.

`doc_honesty_section`: Local formulas define how to learn from an opted-in beta
cohort; they are not current adoption measurements.

`no_overclaim`: No traction, retention, or product-market-fit claim exists until
real, consented observations meet a predeclared denominator and review window.

`limitations`: Manual local exports can be incomplete or selection-biased and
must include missing-data notes.
