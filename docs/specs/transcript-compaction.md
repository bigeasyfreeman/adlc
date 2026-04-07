# Transcript Compaction Spec

## Trigger Conditions
Compact conversation context when any condition is true:
- context window usage > 80%
- token budget usage > 70%
- conversation length > 20 turns

## Strategy
1. Keep last 5 turns verbatim.
2. Summarize older turns into decision-oriented bullets.
3. Replace inlined code with signatures + key logic notes.
4. Reduce repo map payload to sections relevant to current phase.

## Must Not Compact
- current phase and checkpoint state
- unresolved Type 1 decisions
- open risks and blockers
- G/W/T acceptance criteria

## Output Marker
Emit `context.compacted` metadata with source-turn range and summary hash.
