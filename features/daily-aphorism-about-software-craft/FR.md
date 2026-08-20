# Feature Request: Daily Aphorism About Software Craft

**Priority:** LOW
**Type:** Feature
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-08-20

## Summary
Add a `daily-aphorism-about-software-craft` YAMLGraph feature (analogous to
the existing `horoscope` and `haiku` fixtures) that generates one short,
original, memorable aphorism about the craft of building software, with no
attribution.

## Value Statement
Users following the daily cron output get a terse, quotable line about
software craftsmanship instead of a conventional forecast or poem.

## Problem
There is no graph/prompt pair that produces a single original software-craft
aphorism. The requester (issue #3) wants a lightweight, single-output
artifact (one aphorism, nothing else) suitable for a daily automated run,
following the pattern already established by `features/horoscope` and
`features/haiku`.

## Proposed Solution
Mirror the `features/horoscope` and `features/haiku` fixture structure:

- `features/daily-aphorism-about-software-craft/graph.yaml` — a minimal
  graph (`START -> generate -> END`) with one `llm` node producing a
  `state_key: aphorism`. The graph takes a single input variable, `date`
  (via `state: {date: str}`), matching the `horoscope`/`haiku` convention
  even though the aphorism's content need not reference the date directly —
  it exists so the daily cron invocation has a varying input, consistent
  with the sibling fixtures.
- `features/daily-aphorism-about-software-craft/prompts/aphorism.yaml` (per
  `prompts_relative`/`prompts_dir` convention) — a prompt instructing the
  model to:
  - Write exactly one short, original aphorism about the craft of building
    software (not a generic proverb, not a paraphrase of a known quote).
  - Keep it terse and memorable (a single sentence, ideally under ~15
    words).
  - Include **no attribution** — no author name, no quotation marks framing
    it as someone else's words, no "as they say" style hedging.
  - Output only the aphorism text — no preamble, explanation, or extra
    commentary.
  - Declare a `schema.fields.aphorism` block (mirroring `horoscope.yaml`'s
    `schema.fields.horoscope` shape) so the schema field name matches
    `state_key: aphorism` exactly.

Example graph shape:

```yaml
version: "1.0"
name: aphorism-cron-fixture
description: Generate a daily original aphorism about the craft of building software.

prompts_relative: true
prompts_dir: prompts

defaults:
  temperature: 0.7

state:
  date: str

nodes:
  generate:
    type: llm
    prompt: aphorism
    variables:
      date: "{state.date}"
    state_key: aphorism

edges:
  - from: START
    to: generate
  - from: generate
    to: END
```

Example prompt shape:

```yaml
schema:
  name: SoftwareCraftAphorism
  fields:
    aphorism:
      type: str
      description: "A single short, original, unattributed aphorism about the craft of building software"

system: |
  You are a terse writer of original aphorisms about software craft. You
  invent new lines; you do not quote or paraphrase existing proverbs or
  known sayings. Return only the requested aphorism, nothing else.

user: |
  Write one short, original aphorism about the craft of building software,
  for {date}.

  Style requirements:
  - Exactly one aphorism, one sentence, terse and memorable.
  - Original wording — do not reuse or lightly reword a known quote.
  - No attribution: no author name, no framing like "as they say".
  - Output the aphorism only — no title, no explanation, no extra
    commentary.
```

**Validation command:** `yamlgraph graph lint features/daily-aphorism-about-software-craft/graph.yaml`

## Acceptance Criteria
- [ ] AC-01: `features/daily-aphorism-about-software-craft/graph.yaml` exists,
      defines a single `llm` node (`generate`) with
      `START -> generate -> END`, `prompts_relative: true`,
      `prompts_dir: prompts`, `state: {date: str}`, and
      `state_key: aphorism`.
- [ ] AC-02: `features/daily-aphorism-about-software-craft/prompts/aphorism.yaml`
      instructs the model to produce exactly one short, original,
      unattributed aphorism about the craft of building software, with no
      additional commentary, and declares a `schema.fields.aphorism` block
      matching `state_key: aphorism`.
- [ ] AC-03: `yamlgraph graph lint features/daily-aphorism-about-software-craft/graph.yaml`
      exits with no errors.
- [ ] AC-04: `yamlgraph graph run features/daily-aphorism-about-software-craft/graph.yaml --var date="<fixed-test-date>" --full`
      produces a non-empty `aphorism` state value.

No documentation surface is updated: `horoscope` and `haiku` have no
README/changelog entries, and by symmetry this fixture does not add one
either. *(Folded per judgement R-1: removed the self-contradictory AC-05
"criterion that documents its own absence"; rationale preserved here
instead.)*

## Alternatives Considered
- Reuse the `horoscope` or `haiku` graph with only a different prompt:
  rejected because a distinct named feature was explicitly requested in
  issue #3, and keeping fixtures separate matches the existing
  one-feature-per-directory layout.
- Maintaining a fixed pool of pre-written aphorisms and rotating through
  them: rejected because the issue explicitly asks for a newly produced
  original aphorism each day, not a lookup from a static list.

## Related
- Issue #3: "Daily aphorism about software craft"
- `features/horoscope/graph.yaml` (pattern reference)
- `features/haiku/FR.md` (structurally analogous precedent FR)
