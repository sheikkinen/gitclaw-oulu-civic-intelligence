#!/usr/bin/env bash
# Verify a feature's authoring artifacts (FR-827 R-2).
# The report artifact is the proof — never trust exit codes of the
# authoring session. Usage: scripts/author-report.sh <feature>
set -euo pipefail

feature="${1:?usage: author-report.sh <feature>}"
dir="features/${feature}"
report="${dir}/authoring-report.md"

fail() { echo "AUTHOR-REPORT FAIL: $1" >&2; exit 1; }

[ -f "$report" ] || fail "missing ${report}"
[ "$(wc -c < "$report")" -ge 200 ] || fail "report under 200 bytes — presence without substance"
grep -qi "lint" "$report" || fail "report lacks lint evidence"
grep -qi "smoke\|run" "$report" || fail "report lacks smoke/run evidence"
[ -f "${dir}/graph.yaml" ] || fail "missing ${dir}/graph.yaml"

yamlgraph graph lint "${dir}/graph.yaml" || fail "graph lint failed"

echo "AUTHOR-REPORT OK: ${feature}"
