"""FR-840: immutable owner-request artifact — canonical writer/verifier.

The trusted workflow writes features/<slug>/request.json from GitHub event
data before any model stage; the graph re-verifies exact bytes after every
model stage. Owner title/body never pass through argv, stdout, or graph state.
"""

import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path

TITLE_MAX_CHARS = 256
BODY_MAX_BYTES = 1024 * 1024
ARTIFACT_MAX_BYTES = int(1.1 * 1024 * 1024)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
REQUIRED_KEYS = {
    "version",
    "repository",
    "issue_number",
    "feature_name",
    "title",
    "body",
}


class RequestContractError(Exception):
    """Any request-artifact integrity, schema, path, or bound violation."""


def _fail(reason: str) -> None:
    raise RequestContractError(reason)


def _validate_fields(
    feature: str, issue_number: int, repository: str, title: str, body: str
) -> None:
    if not isinstance(issue_number, int) or issue_number < 1:
        _fail("issue_number must be a positive integer")
    if not SLUG_RE.match(feature or ""):
        _fail("feature_name is not a canonical slug")
    if not REPO_RE.match(repository or ""):
        _fail("repository must be owner/repository")
    if not title or len(title) > TITLE_MAX_CHARS:
        _fail(f"title must be 1..{TITLE_MAX_CHARS} characters")
    if not body or len(body.encode("utf-8")) > BODY_MAX_BYTES:
        _fail(f"body must be 1..{BODY_MAX_BYTES} UTF-8 bytes")
    for name, value in (("title", title), ("body", body)):
        if "\x00" in value:
            _fail(f"{name} contains NUL")


def _canonical_bytes(
    feature: str, issue_number: int, repository: str, title: str, body: str
) -> bytes:
    payload = {
        "body": body,
        "feature_name": feature,
        "issue_number": issue_number,
        "repository": repository,
        "title": title,
        "version": 1,
    }
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    if len(encoded) > ARTIFACT_MAX_BYTES:
        _fail(f"artifact exceeds {ARTIFACT_MAX_BYTES} bytes")
    return encoded


def write_request(
    root: Path, feature: str, issue_number: int, repository: str, title: str, body: str
) -> str:
    _validate_fields(feature, issue_number, repository, title, body)
    encoded = _canonical_bytes(feature, issue_number, repository, title, body)
    parent = Path(root) / "features" / feature
    if parent.is_symlink():
        _fail("feature directory is a symlink")
    if parent.exists() and not parent.is_dir():
        _fail("feature path is not a directory")
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / "request.json"
    if target.exists() or target.is_symlink():
        _fail("request.json already exists")
    temp = parent / ".request.json.tmp"
    try:
        with open(temp, "xb") as handle:
            handle.write(encoded)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            _fail(f"duplicate key: {key}")
        seen[key] = value
    return seen


def verify_request(root: Path, feature: str, expected_sha256: str) -> None:
    if not SLUG_RE.match(feature or ""):
        _fail("feature_name is not a canonical slug")
    if not re.match(r"^[0-9a-f]{64}$", expected_sha256 or ""):
        _fail("expected hash is not a lowercase sha256")
    target = Path(root) / "features" / feature / "request.json"
    if target.is_symlink():
        _fail("request.json is a symlink")
    if not target.is_file():
        _fail("request.json is missing or not a regular file")
    if target.stat().st_size > ARTIFACT_MAX_BYTES:
        _fail("request.json exceeds size bound")
    raw = target.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256):
        _fail("request.json hash mismatch")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"request.json is not strict UTF-8 JSON: {exc}")
    if not isinstance(data, dict) or set(data) != REQUIRED_KEYS:
        _fail("request.json has wrong key set")
    if data["version"] != 1 or isinstance(data["version"], bool):
        _fail("request.json version must be integer 1")
    _validate_fields(
        data["feature_name"],
        data["issue_number"],
        data["repository"],
        data["title"],
        data["body"],
    )
    if data["feature_name"] != feature:
        _fail("request.json feature_name does not match its path")
    if raw != _canonical_bytes(
        data["feature_name"],
        data["issue_number"],
        data["repository"],
        data["title"],
        data["body"],
    ):
        _fail("request.json is not in canonical form")


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 3 and argv[0] == "write":
            digest = write_request(
                Path.cwd(),
                argv[1],
                int(argv[2]),
                os.environ.get("GITCLAW_REPOSITORY", ""),
                os.environ.get("ISSUE_TITLE", ""),
                os.environ.get("ISSUE_BODY", ""),
            )
            print(digest)
            return 0
        if len(argv) == 3 and argv[0] == "verify":
            verify_request(Path.cwd(), argv[1], argv[2])
            return 0
        print("usage: request_contract write|verify <feature> <arg>", file=sys.stderr)
        return 2
    except (RequestContractError, ValueError) as exc:
        # owner text is never echoed; reasons are structural only
        print(f"request_contract: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
