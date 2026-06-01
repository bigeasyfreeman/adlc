---
name: context-layers
description: "Builds structural, semantic, and philosophical context artifacts for a module or service: module manifest, behavioral contracts, and decision log."
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: overlay
  consumes_manifest: true
  trigger_fields:
    - new_module
    - new_interface
    - service_boundary_change
    - api_change
    - data_format_change
    - persistent_storage
  produces:
    - module_manifest
    - behavioral_contracts
    - decision_log
---

# Context Layers

## Purpose

ADLC prevents dark code by embedding comprehension into the codebase. This skill captures three layers for any module or service that is new, heavily changed, ownership-sensitive, or hard to explain:

1. **Structural context** - where it sits and what it touches.
2. **Semantic context** - what its interfaces promise.
3. **Philosophical context** - why it is built this way.

These artifacts are codebase assets. They are not planning notes.

## Standalone Interview Mode

Open with:

"I'm going to help you build three context layers for a module or service: structural, semantic, and philosophical. Which module or service do you want to document? Give me its name and a brief description of what it does."

Then ask layer questions in sequence and wait for answers.

### Layer 1 - Structural Context

Ask:

- What does this module depend on?
- What depends on this module?
- What data does it read?
- What data does it write or modify?
- How is it deployed?
- Does it share caches, databases, queues, file systems, or other resources?

Probe vague answers. For example: "When you say it talks to the user service, is that a synchronous API call, an event, or a shared database read?"

### Layer 2 - Semantic Context

For each major interface, ask:

- Idempotency: can it be called twice safely?
- Failure modes: how does it fail and what does the caller see?
- Performance expectations: latency, throughput, and load behavior.
- Side effects: state changes, downstream events, cache invalidation.
- Retry semantics: what is safe and what is dangerous?
- Data sensitivity: PII, credentials, financial data, compliance data, or public data.

Push back on "it just works normally." That is a comprehension gap.

### Layer 3 - Philosophical Context

Ask:

- Why was this architecture chosen over alternatives?
- What constraints are not obvious from the code?
- What looks like a bug or debt but is intentional?
- What would break if someone made the obvious improvement?
- Did incidents shape the design?
- Are there regulatory, compliance, or contractual reasons for decisions?

If the user does not know, record the gap explicitly: "Reasoning unknown. Treat as load-bearing; do not modify without investigation."

Before outputting artifacts, confirm: "I have enough to generate your three context artifacts. Want me to proceed, or is there anything you want to add or correct?"

## ADLC Embedded Mode

When this skill runs inside ADLC, generate artifact requirements in the Build Brief instead of conducting a long interview if the repo evidence is enough. Ask the engineer only for gaps that cannot be inferred safely.

Create or update context artifacts when:
- a task adds a module, service, public interface, schema, event, or queue contract
- a task changes ownership, deployment, persistence, or retry behavior
- graph research identifies a dark-code hotspot
- code review cannot explain blast radius from the diff and existing docs

## Artifact 1: Module Manifest

Markdown file suitable for the module root, such as `MODULE_MANIFEST.md` or `CONTEXT.md`.

Required sections:
- Module name and one-line purpose
- Dependency map with dependency type: sync API, async event, shared DB, queue, filesystem, library, external API
- Dependent map with the same detail level
- Data flows: what it reads, writes, and where
- Shared resources
- Deployment model
- Owner and on-call rotation if known
- Dark-code hotspots and unknowns

## Artifact 2: Behavioral Contracts

Markdown file or structured comments next to interface definitions.

For each interface:
- interface name and one-line purpose
- idempotency guarantee: yes, no, or conditional
- failure modes and caller-visible behavior
- performance envelope
- side effects
- retry guidance
- data classification

## Artifact 3: Decision Log

Markdown file structured as decisions.

For each decision:
- Decision
- Date
- Context
- Alternatives considered
- Consequences
- **Warning:** what would break if this decision were reversed

## Guardrails

- Never invent dependencies, interfaces, failure modes, or decisions.
- Unknown context is valuable; capture it explicitly.
- Do not redesign the system. Document what exists and why.
- If a described behavior is unowned or uncertain, flag it as a dark-code hotspot in the manifest.
- Include a header comment noting capture date and capture source.

