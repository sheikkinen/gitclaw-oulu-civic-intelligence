# Judgement: features/haiku/FR.md — Daily Haiku About the Weather in Oulu

**Verdict:** APPROVED WITH REVISIONS — sound, minimal, on-pattern fixture; authority to implement activates once R-1 through R-4 are folded into the FR.

**Reviewed against:** `features/haiku/FR.md` (full text); `features/horoscope/graph.yaml` and `features/horoscope/prompts/horoscope.yaml` (cited precedent, verified to exist and match the described shape); `tests/` directory listing (`tests/test_contain.py`, `tests/test_ledger.py` — no horoscope test present, contradicting the FR's cited precedent); `docs/authoring-report-2026-08-20-bootstrap.md` (confirms `yamlgraph graph lint` / `yamlgraph graph run` are the real validation commands); local `yamlgraph` CLI v0.5.17 invoked directly to lint the FR's example graph and a constructed `haiku.yaml` prompt (both passed with no issues); `.github/skills/judge-fr/doctrine.md` (judge contract); `.github/skills/feature-request/SKILL.md` FR template (matches FR.md's actual section structure).

## What is sound

- **Scope is minimal and single-purpose**: one `llm` node, `START -> generate -> END`, no bundled concerns.
- **Architecture alignment is strong**: the proposed `graph.yaml` shape is structurally identical to the real, committed `features/horoscope/graph.yaml` (same `prompts_relative`/`prompts_dir` convention, same `state`/`state_key` pattern). I linted the FR's exact example graph plus a constructed matching prompt with the local `yamlgraph` CLI — both pass with no issues, confirming feasibility.
- **No secrets or side effects**: correctly rejects live weather-API fetching as out of scope, relying on LLM general/seasonal knowledge instead — this keeps the feature within the "YAMLGraph-only artifacts, no new secrets or side effects" constraint.
- **Strategic classification fits**: a second fixture of the same shape as `horoscope` is legitimate contrib/example work, not framework-primitive scope creep, and it does not touch gitclaw workflow machinery (`gitclaw.yaml`, `prompts/plan.yaml`, etc.).

## Required revisions

### R-1: Replace the false test precedent with a concrete, self-contained test spec

The FR's acceptance criterion says a test should be "consistent with existing `tests/` conventions for `horoscope`" — but no such test exists. `tests/` contains only `test_contain.py` and `test_ledger.py`; there is no horoscope test to be consistent with. This acceptance criterion is currently untestable because it points at a precedent that doesn't exist. Replace it with a self-contained spec, e.g.:

> Add `tests/test_haiku.py` that invokes `yamlgraph graph run features/haiku/graph.yaml --var date="<fixed-test-date>" --full` (or the equivalent Python API used elsewhere in `tests/`) and asserts the resulting state contains a non-empty `haiku` key.

### R-2: Make the documentation acceptance criterion unconditional or remove it

"Documentation/changelog fragment added if the repo convention requires one" is not mechanically checkable — "if...requires" is a judgment call, not a check. Either (a) name the specific file to update (e.g., a features list in `README.md`, if one exists) and require it unconditionally, or (b) drop this criterion entirely if no such doc surface currently exists for `horoscope` either (confirm by checking whether `horoscope` itself has a corresponding doc entry — if not, symmetry argues for dropping it here too).

### R-3: Resolve the ambiguity around the `location` field

The prose says the graph takes "`date` (and optionally a fixed `location: \"Oulu, Finland\"`) as input state/variables," but the example graph has no `location` state field at all — "Oulu, Finland" only ever appears in the prompt's prose instructions. Fold this into a single unambiguous statement: the location is a fixed string embedded directly in the prompt text (not a `state`/`variables` entry), matching the given example exactly. Remove the "optionally... as input state" language.

### R-4: Confirm the prompt schema field name and lint command in the FR text

The FR doesn't specify the prompt file's schema (e.g., `schema.name`, `fields.haiku`), only prose instructions. Add the concrete `prompts/haiku.yaml` schema shape (mirroring `horoscope.yaml`'s `schema.fields.<key>` block with `state_key: haiku` wired to a matching schema field) so the enforcer has zero interpretive latitude, and explicitly cite `yamlgraph graph lint <path>` as the exact command (already confirmed working locally) rather than the hedge "or repo-equivalent."

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `features/haiku/graph.yaml` |
| D-2 | `features/haiku/prompts/haiku.yaml` |
| D-3 | `tests/test_haiku.py` (per R-1) |

**Not authorized:** any change to `gitclaw.yaml`, `prompts/plan.yaml`, `prompts/judge.yaml`, `prompts/enforce.yaml`, `prompts/review.yaml`, or other gitclaw workflow machinery; any live weather-data integration, new API client, or new secret/credential; any change to `features/horoscope/**`; any new dependency addition. Gaps discovered in YAMLGraph core or gitclaw's workflow machinery while implementing this FR must be filed as a separate FR, not patched inline here.

## Revised acceptance criteria

- [ ] AC-01: `features/haiku/graph.yaml` exists, defines a single `llm` node (`generate`) with `START -> generate -> END`, `prompts_relative: true`, `prompts_dir: prompts`, `state: {date: str}`, and `state_key: haiku`.
- [ ] AC-02: `features/haiku/prompts/haiku.yaml` instructs the model to produce exactly one 5-7-5 haiku about Oulu, Finland weather in a dry Finnish stoic tone, with no additional commentary, and declares a schema field matching `state_key: haiku`.
- [ ] AC-03: `yamlgraph graph lint features/haiku/graph.yaml` exits with no errors.
- [ ] AC-04: `tests/test_haiku.py` runs the graph (via `yamlgraph graph run` or the repo's Python test harness) with a fixed test `date` and asserts the resulting `haiku` state value is a non-empty string.
- [ ] AC-05 (conditional per R-2): if a documentation surface analogous to `horoscope`'s exists, it is updated to list `haiku`; otherwise this criterion is dropped and the FR states why.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | No live weather API calls, new secrets, or credentials may be introduced. | GATE |
| C-2 | No edits outside `features/haiku/**` and the single new test file in `tests/`. | GATE |
| C-3 | `yamlgraph graph lint features/haiku/graph.yaml` must pass with zero issues before the FR can move to Completed. | GATE |
| C-4 | R-1 through R-4 must be folded into `features/haiku/FR.md` (not just addressed in code) before implementation authority is exercised. | GATE |

Authority granted: none yet — authority to implement `features/haiku/graph.yaml`, `features/haiku/prompts/haiku.yaml`, and `tests/test_haiku.py` activates only after R-1 through R-4 are folded into `features/haiku/FR.md` and the revised FR is re-submitted for enforcement.
