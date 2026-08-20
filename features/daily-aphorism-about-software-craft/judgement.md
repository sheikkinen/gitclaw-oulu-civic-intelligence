# Judgement: features/daily-aphorism-about-software-craft/FR.md — Daily Aphorism About Software Craft

**Verdict:** APPROVED WITH REVISIONS — sound, minimal, on-pattern fixture, structurally identical to the committed `horoscope`/`haiku` precedents and confirmed to lint cleanly; authority to implement activates once R-1 is folded into the FR.

**Reviewed against:** `features/daily-aphorism-about-software-craft/FR.md` (full text); `features/horoscope/graph.yaml` and `features/horoscope/prompts/horoscope.yaml` (cited precedent, verified to exist and match the described `prompts_relative`/`prompts_dir`/`state`/`state_key` shape); `features/haiku/FR.md`, `features/haiku/judgement.md`, and `features/haiku/graph.yaml` (cited structurally-analogous precedent FR, its prior judgement, and its as-built graph — confirms the pattern and shows R-1/R-2 fold outcomes from the prior judge cycle); `tests/test_contain.py` and `tests/test_intake_tools.py` (confirm no dedicated per-feature pytest file exists for `horoscope` or `haiku` — only allowlist/slug-utility references — so CLI-only validation is consistent with actual repo practice, not just aspirational); local `yamlgraph` CLI invoked directly (`yamlgraph graph lint`) against a reconstructed copy of the FR's exact example `graph.yaml` and `prompts/aphorism.yaml` — passed with no issues, confirming feasibility; `.github/skills/judge-fr/doctrine.md` (judge contract); `.github/skills/judge-fr/judgement.template.md` (output shape).

## What is sound

- **Scope is minimal and single-purpose**: one `llm` node, `START -> generate -> END`, no bundled concerns, exactly mirroring `horoscope`/`haiku`.
- **Architecture alignment is strong and verified**: the proposed `graph.yaml` and `prompts/aphorism.yaml` are structurally identical to the real, committed `features/horoscope/graph.yaml`/`prompts/horoscope.yaml` (same `prompts_relative`/`prompts_dir` convention, same `state: {date: str}` / `state_key` wiring, same `schema.fields.<key>` shape). I linted the FR's exact example graph and a matching prompt file with the local `yamlgraph` CLI — both passed with zero issues.
- **No secrets or side effects**: pure LLM generation, no external API, no new dependency, no new credential — satisfies the "YAMLGraph-only artifacts, no new secrets/side effects" constraint outright.
- **Already incorporates prior judgement lessons**: unlike the initial `haiku` FR, this FR pre-resolves the "conditional acceptance criterion" defect flagged in `features/haiku/judgement.md` R-2 by stating outright (AC-05) that no doc/changelog surface exists for the `horoscope`/`haiku` precedents and is therefore not required here — verified true by inspection of the repo (no `README.md` features list, no changelog referencing either fixture).
- **Testability is genuine**: AC-03 (`yamlgraph graph lint`) and AC-04 (`yamlgraph graph run ... --full` producing a non-empty `aphorism` key) are both directly executable commands with observable pass/fail outcomes — no pytest scaffolding is required to make them mechanically checkable, and this matches actual (not aspirational) repo practice: neither `horoscope` nor `haiku` has a dedicated `tests/test_*.py` file today.
- **Strategic classification fits**: a third fixture of the same shape as `horoscope`/`haiku` is legitimate contrib/example work (2+ existing precedents, no new abstraction needed), not framework-primitive scope creep, and it does not touch gitclaw workflow machinery (`gitclaw.yaml`, `prompts/plan.yaml`, `prompts/judge.yaml`, `prompts/enforce.yaml`, `prompts/review.yaml`).

## Required revisions

### R-1: Remove AC-05 entirely rather than listing a "dropped" criterion

AC-05 currently reads as an acceptance criterion ("No documentation/changelog surface exists... This criterion is dropped."), which is self-contradictory: a criterion that announces its own irrelevance is not a criterion. This is the same ambiguity flagged as R-2 in `features/haiku/judgement.md` — resolve it the same way: delete AC-05 outright and, if the rationale is worth preserving, move it to a one-line note in the Proposed Solution or Alternatives Considered section (e.g., "No documentation surface is updated: `horoscope` and `haiku` have no README/changelog entries, and by symmetry this fixture does not add one either"). The Acceptance Criteria list must contain only criteria that are actually required, not criteria that document their own absence.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `features/daily-aphorism-about-software-craft/graph.yaml` |
| D-2 | `features/daily-aphorism-about-software-craft/prompts/aphorism.yaml` |

**Not authorized:** any change to `gitclaw.yaml`, `prompts/plan.yaml`, `prompts/judge.yaml`, `prompts/enforce.yaml`, `prompts/review.yaml`, or other gitclaw workflow machinery; any new pytest file (none is required — CLI lint/run validation per AC-03/AC-04 is sufficient and matches actual `horoscope`/`haiku` precedent); any change to `features/horoscope/**` or `features/haiku/**`; any new dependency, API client, or secret/credential; any documentation/changelog file. Gaps discovered in YAMLGraph core or gitclaw's workflow machinery while implementing this FR must be filed as a separate FR, not patched inline here.

## Revised acceptance criteria

- [ ] AC-01: `features/daily-aphorism-about-software-craft/graph.yaml` exists, defines a single `llm` node (`generate`) with `START -> generate -> END`, `prompts_relative: true`, `prompts_dir: prompts`, `state: {date: str}`, and `state_key: aphorism`.
- [ ] AC-02: `features/daily-aphorism-about-software-craft/prompts/aphorism.yaml` instructs the model to produce exactly one short, original, unattributed aphorism about the craft of building software, with no additional commentary, and declares a `schema.fields.aphorism` block matching `state_key: aphorism`.
- [ ] AC-03: `yamlgraph graph lint features/daily-aphorism-about-software-craft/graph.yaml` exits with no errors.
- [ ] AC-04: `yamlgraph graph run features/daily-aphorism-about-software-craft/graph.yaml --var date="<fixed-test-date>" --full` produces a non-empty `aphorism` state value.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | No live external API calls, new secrets, or credentials may be introduced. | GATE |
| C-2 | No edits outside `features/daily-aphorism-about-software-craft/**`. | GATE |
| C-3 | `yamlgraph graph lint features/daily-aphorism-about-software-craft/graph.yaml` must pass with zero issues before the FR can move to Completed. | GATE |
| C-4 | R-1 (deletion of AC-05 as a self-contradictory criterion) must be folded into `features/daily-aphorism-about-software-craft/FR.md` before implementation authority is exercised. | GATE |

Authority granted: none yet — authority to implement `features/daily-aphorism-about-software-craft/graph.yaml` and `features/daily-aphorism-about-software-craft/prompts/aphorism.yaml` activates only after R-1 is folded into `features/daily-aphorism-about-software-craft/FR.md` and the revised FR is re-submitted for enforcement.
