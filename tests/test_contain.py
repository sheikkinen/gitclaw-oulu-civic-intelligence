"""Diff containment gate (FR-827 R-4) — RED spec. Fail closed."""

import pytest

from tools import contain


ALLOW_OK = [
    "features/haiku/graph.yaml",
    "features/haiku/prompts/haiku.yaml",
    "features/haiku/tools/fetch.py",
    "features/haiku/tests/test_fetch.py",
    "features/haiku/FR.md",
    "features/haiku/judgement.md",
    "features/haiku/review.md",
    "features/haiku/authoring-report.md",
    "state/issues.jsonl",
]

DENY = [
    ".github/workflows/intake.yml",
    ".github/workflows/evil.yml",
    ".github/skills/judge-fr/doctrine.md",
    "policy/generated-features.md",
    "gitclaw.yaml",
    "prompts/plan.yaml",
    "tools/ledger.py",
    "tools/contain.py",
    "requirements.txt",
    "package.json",
    "README.md",
    "features/other-feature/graph.yaml",
    "outputs/2026-08-20-haiku.md",
    ".git/hooks/pre-commit",
]


def test_allowlist_paths_pass():
    assert contain.violations(ALLOW_OK, "haiku") == []


@pytest.mark.parametrize("path", DENY)
def test_out_of_allowlist_fails_closed(path):
    assert contain.violations([path], "haiku") == [path]


def test_mixed_diff_reports_only_violations():
    paths = ALLOW_OK + [".github/workflows/evil.yml"]
    assert contain.violations(paths, "haiku") == [".github/workflows/evil.yml"]


def test_traversal_rejected():
    assert contain.violations(["features/haiku/../../.github/x.yml"], "haiku")
    assert contain.violations(["features/haiku/./../evil.py"], "haiku")


def test_untracked_dir_trailing_slash_allowed():
    """git status reports untracked dirs as 'features/haiku/'."""
    assert contain.violations(["features/haiku/"], "haiku") == []
    assert contain.violations(["features/other/"], "haiku") == ["features/other/"]
    assert contain.violations([".github/"], "haiku") == [".github/"]
