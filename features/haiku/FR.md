# Feature Request: Daily Haiku About the Weather in Oulu

**Priority:** LOW
**Type:** Feature
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-08-20

## Summary
Add a `haiku` YAMLGraph feature (analogous to the existing `horoscope` fixture)
that generates one daily haiku (5-7-5 syllable structure) about the current
weather in Oulu, Finland, written in a tone of dry Finnish stoicism.

## Value Statement
Users following the daily cron output get a short, atmospheric weather haiku
for Oulu instead of a conventional forecast.

## Problem
There is no graph/prompt pair that produces a weather-themed haiku for a
specific location. The requester wants a lightweight, single-output artifact
(one haiku, nothing else) suitable for a daily automated run, following the
pattern already established by `features/horoscope`.

## Proposed Solution
Mirror the `features/horoscope` fixture structure:

- `features/haiku/graph.yaml` — a minimal graph (`START -> generate -> END`)
  with one `llm` node producing a `state_key: haiku`. The graph takes a
  single input variable, `date` (via `state: {date: str}`). The location
  ("Oulu, Finland") is **not** a state/variable field — it is a fixed string
  embedded directly in the prompt's prose instructions, exactly as shown in
  the example graph below. *(Revision R-3: removed the earlier "optionally a
  fixed `location` state field" language — this was ambiguous and
  contradicted the example, which never declared a `location` state entry.)*
- `features/haiku/prompts/haiku.yaml` (per `prompts_relative`/`prompts_dir`
  convention) — a prompt instructing the model to:
  - Write exactly one haiku (5-7-5 syllables).
  - Base it on the current/typical weather conditions in Oulu, Finland, for
    the given date.
  - Use a tone of dry Finnish stoicism.
  - Output only the haiku text — no preamble, explanation, or extra
    commentary.
  - Declare a `schema.fields.haiku` block (mirroring
    `horoscope.yaml`'s `schema.fields.horoscope` shape) so the schema field
    name matches `state_key: haiku` exactly. *(Revision R-4: made the prompt
    schema shape explicit — no interpretive latitude left to the enforcer.)*

Example graph shape (final, matches implementation):

```yaml
version: "1.0"
name: haiku-cron-fixture
description: Generate a daily weather haiku for Oulu, Finland, in a dry Finnish stoic tone.

prompts_relative: true
prompts_dir: prompts

defaults:
  temperature: 0.7

state:
  date: str

nodes:
  generate:
    type: llm
    prompt: haiku
    variables:
      date: "{state.date}"
    state_key: haiku

edges:
  - from: START
    to: generate
  - from: generate
    to: END
```

Example prompt shape (final, matches implementation):

```yaml
schema:
  name: WeatherHaiku
  fields:
    haiku:
      type: str
      description: "A single 5-7-5 haiku about the current weather in Oulu, Finland, in a dry Finnish stoic tone"

system: |
  You are a laconic Finnish poet. You write only haiku, in a tone of dry
  Finnish stoicism (sisu, understatement, no exclamation). Return only the
  requested haiku, nothing else.

user: |
  Write one haiku (5-7-5 syllables) about the current weather in Oulu,
  Finland, on {date}.

  Style requirements:
  - Exactly one haiku, 5-7-5 syllable structure.
  - Tone: dry Finnish stoicism.
  - Output the haiku only — no title, no explanation, no extra commentary.
```

**Validation command (R-4):** `yamlgraph graph lint features/haiku/graph.yaml`
is the exact, confirmed-working validation command (no "or repo-equivalent"
hedge).

## Acceptance Criteria
- [ ] AC-01: `features/haiku/graph.yaml` exists, defines a single `llm` node
      (`generate`) with `START -> generate -> END`, `prompts_relative: true`,
      `prompts_dir: prompts`, `state: {date: str}`, and `state_key: haiku`.
- [ ] AC-02: `features/haiku/prompts/haiku.yaml` instructs the model to
      produce exactly one 5-7-5 haiku about Oulu, Finland weather in a dry
      Finnish stoic tone, with no additional commentary, and declares a
      `schema.fields.haiku` block matching `state_key: haiku`.
- [ ] AC-03: `yamlgraph graph lint features/haiku/graph.yaml` exits with no
      errors. *(R-4: exact command, no hedge.)*
- [ ] AC-04: `yamlgraph graph run features/haiku/graph.yaml --var date="<fixed-test-date>" --full`
      produces a non-empty `haiku` state value. *(R-1: replaced the false
      "consistent with existing `tests/` conventions for `horoscope`"
      precedent — no such test exists in `tests/` — with this concrete,
      self-contained CLI smoke check. Per the enforcement-stage instructions
      for this FR, authored artifacts are restricted to `features/haiku/`
      only, so validation is performed via the `yamlgraph` CLI rather than a
      new `tests/test_haiku.py` file.)*
- [ ] AC-05: No documentation/changelog surface exists for the `horoscope`
      precedent (no `README.md`/features-list entry references it), so by
      symmetry no such surface is required for `haiku` either. This
      criterion is dropped. *(R-2: removed the unconditional-vs-drop
      ambiguity by confirming no analogous doc surface exists to update.)*

## Alternatives Considered
- Reuse the `horoscope` graph with a different prompt only: rejected because
  a distinct named feature (`haiku`) was explicitly requested, and keeping
  fixtures separate matches the existing one-feature-per-directory layout.
- Fetching live weather data via an external API: out of scope for this FR;
  the requester only asked for a haiku "about the current weather," which the
  LLM can approximate from general/seasonal knowledge unless a future FR adds
  a real weather data source.

## Related
- Issue #2: "Daily haiku about the weather in Oulu"
- `features/horoscope/graph.yaml` (pattern reference)
