"""Intake ledger: append-only JSONL state machine (FR-827 R-5).

CLI:
  python -m tools.ledger record <issue> <state> [key=value ...]
  python -m tools.ledger current <issue>
  python -m tools.ledger should-run <issue>   # exit 0 run, 78 skip
"""

import json
import os
import re
import sys
import time
from pathlib import Path

LEDGER = Path("state/issues.jsonl")

TRANSITIONS = {
    "seen": {"planned", "failed_recovery_required"},
    "planned": {"judged_approved", "judged_rejected", "failed_recovery_required"},
    "judged_approved": {"enforced", "failed_recovery_required"},
    "enforced": {"reviewed_approved", "reviewed_rejected", "failed_recovery_required"},
    "reviewed_rejected": {"enforced", "reviewed_rejected_final", "failed_recovery_required"},
    "reviewed_approved": {"pushed", "failed_recovery_required"},
    "pushed": {"closed", "failed_recovery_required"},
}

TERMINAL = {"closed", "judged_rejected", "reviewed_rejected_final", "failed_recovery_required"}

STATES = set(TRANSITIONS) | TERMINAL


class IllegalTransition(Exception):
    pass


def is_terminal(state: str) -> bool:
    return state in TERMINAL


def _validate_repository(repository: str) -> str:
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        raise ValueError("repository must be non-empty owner/name")
    return repository


def _entries(path: Path, repository: str, issue: int) -> list[dict]:
    repository = _validate_repository(repository)
    if not Path(path).exists():
        return []
    out = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("repository") == repository and entry["issue"] == issue:
            out.append(entry)
    return out


def current(path: Path, repository: str, issue: int) -> str | None:
    entries = _entries(path, repository, issue)
    return entries[-1]["state"] if entries else None


def record(path: Path, repository: str, issue: int, state: str, **extra) -> None:
    repository = _validate_repository(repository)
    if state not in STATES:
        raise IllegalTransition(f"unknown state: {state}")
    prev = current(path, repository, issue)
    if prev is None:
        if state != "seen":
            raise IllegalTransition(f"first state must be 'seen', got '{state}'")
    else:
        if prev in TERMINAL:
            raise IllegalTransition(f"'{prev}' is terminal")
        allowed = TRANSITIONS[prev]
        if state not in allowed:
            raise IllegalTransition(f"'{prev}' -> '{state}' not allowed")
        # one remediation lap: a second reviewed_rejected forbids re-enforce
        if state == "enforced" and prev == "reviewed_rejected":
            rejections = [
                e
                for e in _entries(path, repository, issue)
                if e["state"] == "reviewed_rejected"
            ]
            if len(rejections) >= 2:
                raise IllegalTransition("remediation lap already used")
    entry = {
        "repository": repository,
        "issue": issue,
        "state": state,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def should_run(path: Path, repository: str, issue: int) -> bool:
    state = current(path, repository, issue)
    return state is None or not is_terminal(state)


def gate_code(path: Path, repository: str, issue: int) -> int:
    """Intake gate: 0 fresh, 78 terminal (idempotent skip), 65 interrupted."""
    state = current(path, repository, issue)
    if state is None:
        return 0
    if is_terminal(state):
        return 78
    return 65


def main(argv: list[str]) -> int:
    cmd, issue = argv[0], int(argv[1])
    repository = os.environ.get("GITCLAW_REPOSITORY")
    if repository is None:
        raise SystemExit("GITCLAW_REPOSITORY is required (owner/name)")
    try:
        repository = _validate_repository(repository)
    except ValueError as exc:
        raise SystemExit(f"invalid GITCLAW_REPOSITORY: {exc}") from exc
    if cmd == "record":
        extra = dict(kv.split("=", 1) for kv in argv[3:])
        record(LEDGER, repository, issue, argv[2], **extra)
        return 0
    if cmd == "current":
        print(current(LEDGER, repository, issue) or "")
        return 0
    if cmd == "should-run":
        return gate_code(LEDGER, repository, issue)
    raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
