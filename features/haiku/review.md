# Review: features/haiku (working-tree diff)

**Verdict:** APPROVED WITH REVISIONS

**Reviewed against:** `features/haiku/FR.md` (revised, R-1–R-4 folded),
`features/haiku/judgement.md` (APPROVED WITH REVISIONS, frozen scope D-1/D-2/D-3,
GATEs C-1–C-4). Input closure: working-tree diff under `features/haiku/`, the two
governing docs, and repo doctrine — no author chat narrative consulted.

**Note on process:** no GitHub PR exists for this change (untracked local diff);
reviewed the working tree as the task explicitly instructed, in place of `gh pr
diff`.

## Blocking findings

1. **P1 — D-3 deliverable (`tests/test_haiku.py`) is missing, contradicting the
   judgement's revised AC-04 and frozen scope table.** `judgement.md` lists
   `tests/test_haiku.py` as deliverable D-3 and its revised AC-04 requires a test
   file that "asserts the resulting `haiku` state value is a non-empty string."
   GATE C-4 requires R-1 (which specifically prescribes this test file) to be
   folded into `FR.md` before implementation authority activates. Instead,
   `FR.md`'s own AC-04 text rewrites the requirement to a CLI smoke-check only,
   and `authoring-report.md` confirms no test file was created, citing
   unspecified "enforcement-stage instructions for this task" as authority for
   the substitution. Those instructions are not part of the input closure
   (FR.md + judgement.md) and cannot override a GATE condition in the frozen
   judgement. This is source-of-truth drift between the judgement's authority
   and the FR's self-reported fold, not a harmless simplification — the
   judgement never sanctioned dropping D-3.
   **Fix:** either add `tests/test_haiku.py` per the judgement's literal R-1/AC-04
   text, or return to the judge stage for an explicit re-judgement that
   authorizes the CLI-only validation substitution before this is merged.

## Non-blocking notes

- `outputs/routes/route.jsonl` shows uncommitted diff entries from `yamlgraph`
  run/route telemetry (both the author's `graph run` validation and this
  review's re-validation). This is automatic CLI log output, not an authored
  scope change, and sits outside `features/haiku/**`, but reviewers/mergers
  should exclude or `.gitignore` this log rather than commit it as part of the
  PR.
- `FR.md`'s AC-05 removal (no doc surface to update) is consistent with R-2 and
  verified: no `README.md`/features-list entry references `horoscope` either.
  Fine as-is.
- Diff correctly stays within the authorized surface: only
  `features/haiku/graph.yaml`, `features/haiku/prompts/haiku.yaml`,
  `features/haiku/FR.md`, `features/haiku/judgement.md`, and
  `features/haiku/authoring-report.md` are new/touched. No edits to
  `gitclaw.yaml`, `prompts/plan.yaml`, `prompts/judge.yaml`,
  `prompts/enforce.yaml`, `prompts/review.yaml`, or `features/horoscope/**` —
  matches the "Not authorized" list. No new dependencies or secrets introduced.

## Validations run

- `yamlgraph graph lint features/haiku/graph.yaml` → exit 0, `✅ graph.yaml -
  No issues found` / `✅ All graphs passed linting`. Satisfies AC-03 / GATE C-3.
- `yamlgraph graph run features/haiku/graph.yaml --var date="2026-08-20"
  --full` → exit 0, produced non-empty `haiku` state:
  `"Gray rain on the lake\nThe wind is from the northwest\nSummer is over"`.
  Confirms the graph is runnable end-to-end and matches the shape verified in
  `authoring-report.md`. This is the FR's own (unilaterally substituted)
  AC-04 check, not the judgement's literal AC-04 — see P1.
- Manual inspection of `graph.yaml` against judgement AC-01: single `llm` node
  `generate`, `START -> generate -> END`, `prompts_relative: true`,
  `prompts_dir: prompts`, `state: {date: str}`, `state_key: haiku` — all
  present, matches.
- Manual inspection of `prompts/haiku.yaml` against judgement AC-02: instructs
  exactly one 5-7-5 haiku, Oulu/Finland weather, dry Finnish stoic tone, output
  haiku only, `schema.fields.haiku` present matching `state_key: haiku` — all
  present, matches.

## Validations not run

- No test-file validation was possible because `tests/test_haiku.py` (D-3)
  does not exist in the diff — this is itself the P1 finding, not a gap in
  reviewer effort.
- No GitHub PR head/diff check (`gh pr view` / `gh pr diff`) was performed
  because no PR exists for this change; the task explicitly directed review of
  the local working-tree diff instead.
