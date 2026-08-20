# Artifacts

Target repository: `/Users/sheikki/Documents/src/gitclaw`

- `features/horoscope/graph.yaml`
- `features/horoscope/prompts/horoscope.yaml`
- `gitclaw.yaml`
- `prompts/plan.yaml`
- `prompts/judge.yaml`
- `prompts/enforce.yaml`
- `prompts/review.yaml`

# Precedent

- Adapted committed horoscope precedent: `examples/demos/horoscope/graph.yaml`
  and `examples/demos/horoscope/prompts/horoscope.yaml`.
- Used committed pipeline/spec source:
  `feature-requests/FR-827-gitclaw-forkable-runner.md`, especially the
  Pipeline stages and constraints.
- Used syntax references: `reference/graph-yaml.md` for copilot nodes,
  expression edges, passthrough nodes, and loop limits; `reference/expressions.md`
  for condition syntax.

# Validation

- `yamlgraph graph lint /Users/sheikki/Documents/src/gitclaw/features/horoscope/graph.yaml`
  -> passed with no issues.
- `yamlgraph graph run /Users/sheikki/Documents/src/gitclaw/features/horoscope/graph.yaml --var date="2026-08-20" --full`
  -> passed; produced `horoscope` output for Aries in weather-report style.
- `yamlgraph graph lint /Users/sheikki/Documents/src/gitclaw/gitclaw.yaml`
  -> passed with no issues after repairs.
- `yamlgraph graph info /Users/sheikki/Documents/src/gitclaw/gitclaw.yaml`
  -> passed; showed nodes `plan`, `judge`, `judge_gate`, `enforce`, `review`,
  `review_gate` and 12 edges.

# Repairs

- Quoted colon-bearing condition expressions in `gitclaw.yaml` after YAML parsing
  failed on unquoted gate expressions.
- Removed a prompt phrase that triggered lint warning W026 in `prompts/plan.yaml`.
- Added an explicit conservative route for missing `_loop_counts.enforce` at
  `review_gate` to eliminate lint warning W803.
- Represented gate checks with deterministic passthrough nodes plus expression
  edges because YAMLGraph condition expressions support comparisons, not
  substring operators. The stage prompts require exact single-line stdout tokens
  so equality routing remains deterministic.

# Blocked validation

None.
