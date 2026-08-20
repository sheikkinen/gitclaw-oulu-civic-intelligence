# Skills Snapshot

Vendored contract snapshot from `sheikkinen/yamlgraph` — the doctrine
these skills reference (chaplain FSM, hooks, sole-route adapters,
fr-board, prior-art gates) lives in the source repo and does NOT apply
here. In gitclaw, these files are **prompt contracts** consumed by the
pipeline's copilot nodes; the executable authoring route in this repo
is `scripts/author-report.sh` (gitclaw-local, see FR-827 R-2).

| Field | Value |
|---|---|
| Source repo | https://github.com/sheikkinen/yamlgraph |
| Source SHA | `656c345ff0a98c6afb8d5ccb55393e918bcba042` |
| Snapshot date | 2026-08-20 |
| Governing FR | yamlgraph FR-827 |

## Vendored files

- `feature-request/SKILL.md`, `feature-request/FR-TEMPLATE.md` — plan
  stage contract: FR shape, Ideal Result, acceptance criteria.
- `judge-fr/SKILL.md`, `judge-fr/doctrine.md`,
  `judge-fr/judgement.template.md` — judge stage contract: rubric,
  verdict taxonomy, input closure. Adapter/route sections are
  inapplicable; the judge here is a fresh copilot CLI session.
- `review-pr/SKILL.md`, `review-pr/doctrine.md` — review stage
  contract: diff vs frozen scope. GitHub-PR mechanics inapplicable;
  the review here targets the working-tree diff.
- `graph-authoring/SKILL.md`, `graph-authoring/doctrine.md` — enforce
  stage contract: precedent search, lint, smoke, honest validation
  record. The yamlgraph sentinel route is replaced by
  `scripts/author-report.sh` verification.

## Refresh procedure

Re-copy the files from yamlgraph at a newer SHA, update this table,
commit as `chore(skills): refresh snapshot to <sha>`.
