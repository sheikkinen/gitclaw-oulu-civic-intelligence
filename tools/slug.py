"""Sanitize issue titles into feature slugs. Slugs flow into shell
commands and paths — strictly [a-z0-9-]."""

import re
import sys
from pathlib import Path


def make(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = s[:40].rstrip("-")
    return s or "feature"


def unique(title: str, issue: int, root: str | Path = "features") -> str:
    """Collision-aware slug: similar titles must not share a feature dir."""
    s = make(title)
    if not (Path(root) / s).exists():
        return s
    suffix = f"-{issue}"
    return s[: 40 - len(suffix)].rstrip("-") + suffix


if __name__ == "__main__":
    print(unique(sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else make(sys.argv[1]))
