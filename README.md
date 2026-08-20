# gitclaw 🐾

**Issue in, feature out, output every morning.**

gitclaw is a forkable template repo: file a GitHub issue describing a
small daily LLM feature ("daily haiku about the weather in Oulu"), and
a plan → judge → enforce → review pipeline — run entirely by GitHub
Copilot CLI inside GitHub Actions — writes the feature request, judges
it, implements it as a [YAMLGraph](https://github.com/sheikkinen/yamlgraph)
graph, reviews the diff, and commits it. A daily cron then runs every
accepted feature and commits its output.

## Use it

1. **Use this template** (green button) to create your own copy.
2. Enable Actions on your copy (template instantiation disables workflows).
3. Set two repository secrets:
   | Secret | Value |
   |---|---|
   | `COPILOT_CLI_TOKEN` | a GitHub token with Copilot access (e.g. `gh auth token`) — consumed as `COPILOT_GITHUB_TOKEN` by Copilot CLI |
   | `ANTHROPIC_API_KEY` | provider key for running the generated graphs |

   No PAT is needed for git/issue operations — the built-in
   `GITHUB_TOKEN` with `contents: write` / `issues: write` suffices.

   Set/rotate the token without ever displaying it:

   ```bash
   gh auth token | gh secret set COPILOT_CLI_TOKEN -R <owner>/<repo>
   printenv ANTHROPIC_API_KEY | gh secret set ANTHROPIC_API_KEY -R <owner>/<repo>
   ```

   `COPILOT_CLI_TOKEN` is an OAuth token that lives until revoked
   (logout, `gh auth refresh`, password change, or ~1 year unused).
   If pipelines start failing at the plan step, rotate it and probe
   with `gh workflow run spike-copilot-cli.yml`.
4. File an issue with a one-line feature wish. Watch the pipeline.
5. Every morning (06:00 UTC), `cron.yml` runs all accepted features and
   commits their outputs to `outputs/`.

## Trust model

The intake workflow triggers on all issues but the **job-level `if` is
the sole barrier** before LLM execution with secrets:

- `opened`: issue author must be `OWNER`, `MEMBER`, or `COLLABORATOR`.
  `CONTRIBUTOR` is deliberately excluded — a merged typo fix must not
  grant LLM invocation rights.
- `labeled`: label must be `gitclaw` **and the sender applying it must
  be the repo owner** — label presence alone is insufficient (issue
  forms can auto-apply labels; no template in this repo may auto-apply
  `gitclaw`).

Anonymous/other issues never reach the LLM. Issue text enters shell
steps only via `env:` blocks, never inline `${{ }}` interpolation.

## Pipeline

```
issue → request.json (trusted workflow, hash-pinned)
      → ledger(seen) → plan → judge ──REJECTED──→ comment + close
                                │
                     APPROVED / WITH REVISIONS
                                ▼
                      enforce (resumes plan session)
                                ▼
                             review ──REJECTED / WITH REVISIONS──→ remediation lap
                                │                                  (re-enforce + re-review,
                                │                                   then final reject)
                        APPROVED (exact)
                                ▼
              containment gate → commit → comment → close
```

- **Immutable owner request**: the workflow writes
  `features/<name>/request.json` from the issue before any model stage and
  passes only its SHA-256 into the graph; the exact bytes are re-verified
  after plan, judge, enforce, and review. Owner text never enters shell
  arguments, logs, or graph state. Judgement/review revisions may only
  clarify or tighten — contradicting the owner request is a rejection — and
  enforcement may not edit `request.json`, `FR.md`, or `judgement.md`.
- **Convergence**: judgement revisions are controlling additive constraints
  over frozen `FR.md` prose; review never blocks on unfolded prose. Exactly
  one remediation lap is allowed — a second non-approved review posts the
  review and closes the issue via final rejection.
- **Model pin**: all four pipeline stages pin `claude-sonnet-5` via
  `cli_flags.model` so verdict behavior is reproducible; forks whose Copilot
  plan lacks that model change one value per node in `gitclaw.yaml`.
- **Reference assets**: an issue may add one exact `Reference-set: <name>`
  line to adapt owner-committed files from `references/<name>/` (Git-tracked
  at HEAD, ≤8 UTF-8 files, ≤256 KiB each, ≤1 MiB total, `manifest.json`
  reserved). The workflow stages them into `features/<slug>/reference/` with
  a hash manifest verified at every stage; models adapt but never execute
  them. Issue prose still selects only — it grants nothing beyond the set
  name. If a model refuses the adaptation, the fallback is operator-authored
  code with gitclaw used for review only.

- **Verdicts are read from artifacts** (`judgement.md` / `review.md`),
  never from LLM stdout tokens. Unparseable verdict = fail closed.
- **Ledger** (`state/issues.jsonl`): append-only frozen state machine
  (`tools/ledger.py`); every transition commits immediately. Illegal
  transitions raise.
- **Containment** (`tools/contain.py`): fail-closed allowlist — a
  pipeline run may only touch `features/<name>/**` and the ledger.
  Anything else aborts before push.
- **Idempotency**: re-delivered events skip terminal issues (exit 78);
  interrupted non-terminal issues demand human recovery (exit 65).

## Composition

Generated features remain isolated ownership units; their directories are not
shared libraries. A composer declares exact dependencies in its contained
`composition.json`. Cron validates the dependency graph, runs each dependency
at most once, and passes direct same-run results through a bounded
`source_snapshots` JSON string. Successful entries carry unchanged candidate
text; failed entries carry a bounded reason. Composers still run on partial or
all-dependency failure so they can report health explicitly.

Manifests are regular contained files capped at 16 KiB. Candidates are capped
at 32 KiB of UTF-8 and the envelope at 96 KiB, below Linux's per-argument
ceiling. Cron terminates a graph that exceeds its bounded stdout/stderr or
timeout and records process-spawn failures per feature.

No generated feature may import or read a sibling feature, copy its adapter,
re-fetch its source, or use prior `outputs/` as input. Invalid manifests and
cycles fail the affected features and their dependents while unrelated valid
features continue. The platform schedules and transports results; it does not
interpret, merge, or repair source facts.

## Layout

```
gitclaw.yaml            orchestrator graph (YAMLGraph)
prompts/                plan / judge / enforce / review contracts
features/<name>/        FR.md, judgement.md, review.md,
                        authoring-report.md, graph.yaml, prompts/,
                        optional composition.json
tools/                  ledger, containment, slug, cron runner
scripts/author-report.sh  mechanical artifact verifier
state/issues.jsonl      append-only ledger
outputs/                daily cron outputs
.github/skills/         vendored authoring/judging doctrine snapshot
```

## Security & misuse warnings

Read this before forking. gitclaw hands an LLM agent shell access on
a CI runner with secrets in the environment. The design assumes a
**single trusted operator**; it is not hardened for adversarial
multi-user operation.

**What the gates do and do not protect:**

- The intake trust gate keeps *untrusted people* from triggering the
  LLM. It does nothing about *untrusted content* a trusted person
  pastes into an issue (indirect prompt injection). Don't paste text
  from unknown sources into gitclaw issues.
- The pipeline's copilot sessions run with `allow_all_tools` — full
  shell on the runner. Secrets (`COPILOT_CLI_TOKEN`,
  `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`) are in the process
  environment. The diff-containment gate constrains what gets
  *committed by the happy path*; it is advisory against a genuinely
  malicious model, which could exfiltrate env vars or push directly
  mid-session. Your protection there is model-vendor alignment plus
  the trust gate — treat it as such.
- `GITHUB_TOKEN` cannot modify `.github/workflows/**` (GitHub blocks
  this for Actions tokens) — workflow self-modification is refused at
  the platform layer.
- Generated feature graphs may declare and use tools — that is the
  point of them — which means cron executes LLM-reviewed shell/python
  daily with secrets in env. The review phase and the trust gate are
  the barriers; inspect `features/*/graph.yaml` after each merge if
  that trade is too sharp for your fork. The binding
  [generated-feature policy](policy/generated-features.md) permits
  bounded, unauthenticated reads from named public sources, but forbids
  generated features from reading credentials or performing external writes.

**Sharp edges for adopters:**

- `COPILOT_CLI_TOKEN` is typically a full user OAuth token — broader
  than this repo needs. Prefer a dedicated machine account or a
  fine-grained token; rotate it if a run ever looks off.
- Cost: every trusted issue burns Copilot and Anthropic quota; every
  fork's cron burns it daily, forever, until you disable the
  workflow. There is no budget cap — set provider spend limits.
- Unpinned supply chain: `pip install yamlgraph` and
  `npm install -g @github/copilot` install latest at run time. Pin
  versions in the workflows if you need reproducibility over
  freshness.
- Generated content ships unreviewed by humans: the judge and
  reviewer are LLMs. You are the publisher of whatever your copy
  commits. Machine output may be wrong, derivative, or embarrassing —
  the LICENSE disclaims warranty, not your accountability.
- Do not point gitclaw at a repo containing anything you would not
  hand to an LLM with shell access.

## Limitations

- Copilot CLI must authenticate via `COPILOT_GITHUB_TOKEN`; there is no
  API fallback. If your token lacks Copilot access, intake fails.
- Cron cadence is best-effort (GitHub scheduled workflows may delay or
  skip under load).
- A failed cron feature is recorded (`outputs/<date>-<name>.failed.json`)
  and does not block other features; the job exits 1 as an operator
  signal.
- Public-source tools run with network access and can break when upstream
  availability or schemas change; these failures must surface through the
  feature's explicit failure contract and `.failed.json`.
- One remediation lap on review rejection, then final reject — no
  infinite enforce loops.
- `tools/` requires Python ≥ 3.10 (`X | Y` unions); workflows pin 3.12.

Governed by yamlgraph FR-827.
