# Authoring Report: features/haiku

Target repository: `/Users/sheikki/Documents/src/gitclaw`

## Scope

Implemented per `features/haiku/FR.md` (revised to fold judgement R-1
through R-4) and frozen scope in `features/haiku/judgement.md`
(APPROVED WITH REVISIONS). Per the enforcement-stage instructions for this
task, authored artifacts were restricted to `features/haiku/` only
(YAML-only, no new test file outside that directory, no edits to
`gitclaw.yaml`, `prompts/plan.yaml`, or `features/horoscope/**`).

## Artifacts

- `features/haiku/graph.yaml` — new
- `features/haiku/prompts/haiku.yaml` — new
- `features/haiku/FR.md` — updated (folded R-1 through R-4)

No other files were modified.

## Precedent

- Adapted the committed `features/horoscope/graph.yaml` and
  `features/horoscope/prompts/horoscope.yaml` structure (same
  `prompts_relative`/`prompts_dir` convention, same `state`/`state_key`
  pattern, same `schema.fields.<key>` prompt shape).

## Validation

- `yamlgraph graph lint features/haiku/graph.yaml`
  → **passed**, no issues:
  ```
  ✅ graph.yaml - No issues found
  ✅ All graphs passed linting
  ```

- `yamlgraph graph run features/haiku/graph.yaml --var date="2026-08-20" --full`
  → **passed**. Result:
  ```
  current_step: generate
  date: 2026-08-20
  haiku: {'haiku': 'Cold wind off the bay,\nthe birches lean and endure,\nrain taps on the roof'}
  ```
  Backing model was `deepseek/deepseek-v4-flash` (via LangSmith trace
  `01a01cb4-960e-73f2-b85f-e091cc7696fd`). One transient `400 Bad Request`
  on the first structured-output attempt was automatically handled by
  yamlgraph's existing JSON-extraction fallback (FR-464); the retry
  succeeded with `200 OK`. This is pre-existing yamlgraph executor behavior,
  not a defect introduced by this feature.

## Deviations from judgement.md (documented, not silent)

- **AC-04 (test coverage):** `judgement.md` D-3/AC-04 called for a new
  `tests/test_haiku.py`. The enforcement-stage instructions for this task
  explicitly restrict authored artifacts to `features/haiku/` (YAML-only,
  "few LLM nodes"), so no `tests/test_haiku.py` was created. Coverage for
  AC-04 is instead evidenced by the `yamlgraph graph run ... --full` smoke
  run above, which is the exact validation command mandated by this task.
  This deviation is recorded in the folded `FR.md` (AC-04 note) as well.
- **AC-05 (documentation):** No documentation/changelog surface exists for
  the `horoscope` precedent (no `README.md` features list references it),
  so by symmetry AC-05 was dropped rather than fabricated. No doc files
  were touched.

## Repairs

None required — lint and run both passed on first attempt using the
example shapes carried over from `features/horoscope`.
