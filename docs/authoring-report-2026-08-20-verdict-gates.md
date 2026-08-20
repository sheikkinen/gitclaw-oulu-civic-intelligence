# Artifacts

Target repo: `/Users/sheikki/Documents/src/gitclaw`

- `gitclaw.yaml`
- `prompts/judge.yaml`
- `prompts/review.yaml`
- `prompts/enforce.yaml`

# Precedent

- Adapted the existing committed `gitclaw.yaml` orchestration shape and preserved its ledger, contain, push, and loop-count paths.
- Consulted `reference/graph-yaml.md` shell tool documentation for `type: shell`, `parse: text`, and tool node syntax.
- Consulted `yamlgraph/tools/shell.py`; `parse: text` preserves stdout, so authored file-read commands explicitly remove the trailing newline.

# Validation

- `yamlgraph graph lint /Users/sheikki/Documents/src/gitclaw/gitclaw.yaml` -> passed with no issues.
- `yamlgraph graph info /Users/sheikki/Documents/src/gitclaw/gitclaw.yaml` -> passed; graph loads with 16 nodes and 23 edges, including `read_judge_verdict` and `read_review_verdict`.
- `sed -n 's/^\*\*Verdict:\*\* \([A-Z][A-Z ]*[A-Z]\).*/\1/p' /Users/sheikki/Documents/src/gitclaw/features/haiku/judgement.md` -> printed `APPROVED WITH REVISIONS`.

# Repairs

- Replaced stdout-token passthrough gates with deterministic file-reading shell tool nodes.
- Routed approved decision values to the existing approved ledger lanes, rejected decision values to existing close/retry lanes, and all other values to `END` without a ledger transition.
- Updated judge and review prompt contracts so their artifact files carry the routing decision and stdout is ignored.
- Updated enforcement prompt so required revisions are folded into `features/{feature_name}/FR.md` before implementation.

# Blocked validation

- `yamlgraph graph run /Users/sheikki/Documents/src/gitclaw/gitclaw.yaml ...` was not run because the task brief restricts validation to lint and structure only and forbids copilot, gh, and git side effects.
