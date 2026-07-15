# ADLC 0.9.1 beta demo and recording plan

## Outcome

Show one successful Fix loop from red verifier to PR-ready evidence in under
five minutes, then show the raw benchmark boundary. Do not present internal gate
count as user value.

## Preflight

1. Use a clean temporary clone at the immutable release candidate commit.
2. Set a neutral terminal theme at 1280×720 and remove usernames, absolute
   paths, credentials, notifications, and unrelated repositories.
3. Run `bash tests/acceptance/run_readme_quickstart.sh` once off-camera.
4. Keep telemetry off and disconnect any optional screen-recording analytics.

## Shot list and narration

1. **Problem (20 seconds).** Open the failing invoice-average fixture. Say:
   “The useful question is not whether an agent can edit this file; it is what
   the run can prove.”
2. **Reproduce red (35 seconds).** Run the named verifier and show the expected
   failure. Freeze the frame long enough to read the assertion.
3. **Invoke Fix (45 seconds).** Use the first-Fix prompt. Show the bounded plan,
   affected file, and approval boundary without scrolling through internals.
4. **Repair and green (45 seconds).** Show the one-file diff and the same
   verifier passing.
5. **Resume (35 seconds).** Interrupt at the recorded boundary, resume the same
   session, and show that completed effects are not replayed.
6. **Evidence (50 seconds).** Show the distinct review, completion audit, and
   `pr_ready` report with evidence refs.
7. **Public proof (35 seconds).** Open the benchmark page: three primary runs,
   three independent replays, exact configuration, failures, and limitations.
8. **Call to action (20 seconds).** Point to installation, doctor, the beta
   feedback template, and the private vulnerability channel.

## Edit and publication checklist

- Preserve the actual command output; cuts may remove waiting time only.
- Add captions and a text transcript.
- Verify every spoken product claim appears in `launch-packet.json`.
- Run the public hygiene scanner over frames, transcript, and metadata.
- Export locally; do not upload until `launch_communication` is human-approved.

`doc_honesty_section`: This plan rehearses a repository fixture and does not
claim that a viewer's future agent run will produce the same result.

`no_overclaim`: Do not call the demo autonomous delivery, universal support,
production adoption, or GA.

`limitations`: The recording demonstrates one Fix fixture; Build and Review are
documented product loops but are not live-demonstrated here.
