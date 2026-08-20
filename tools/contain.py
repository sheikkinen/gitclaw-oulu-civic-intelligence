"""Diff containment gate (FR-827 R-4): allowlist-only, fail closed.

CLI: python -m tools.contain <feature_name>
Checks every changed/untracked path from `git status --porcelain`;
exits 1 listing violations if any path falls outside the allowlist.
"""

import posixpath
import subprocess
import sys


def _allowed(path: str, feature: str) -> bool:
    path = path.rstrip("/")  # git reports untracked dirs with trailing slash
    norm = posixpath.normpath(path)
    if norm != path or path.startswith("/") or ".." in path.split("/"):
        return False
    return norm == "state/issues.jsonl" or norm == f"features/{feature}" or norm.startswith(f"features/{feature}/")


def violations(paths: list[str], feature: str) -> list[str]:
    return [p for p in paths if not _allowed(p, feature)]


def changed_paths() -> list[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    paths = []
    for line in out.splitlines():
        entry = line[3:]
        if " -> " in entry:  # rename: check both sides
            old, new = entry.split(" -> ", 1)
            paths.extend([old, new])
        else:
            paths.append(entry)
    return [p.strip('"') for p in paths]


def main(feature: str) -> int:
    bad = violations(changed_paths(), feature)
    if bad:
        print("containment gate FAILED — paths outside allowlist:", file=sys.stderr)
        for p in bad:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("containment gate OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
