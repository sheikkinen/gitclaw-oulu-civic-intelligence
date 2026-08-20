"""FR-841: owner-committed reference assets — select, stage, verify.

Trust derives from Git-tracked files under references/<set>/ at the checked-out
HEAD, never from issue prose. The issue's `Reference-set:` line only selects a
set; parsing lives here in tested code, not in workflow shell.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
SELECT_RE = re.compile(r"^Reference-set: (\S+)\s*$", re.MULTILINE)
MAX_FILES = 8
MAX_FILE_BYTES = 256 * 1024
MAX_SET_BYTES = 1024 * 1024
RESERVED_NAMES = {"manifest.json"}


class ReferenceAssetsError(Exception):
    """Any selection, provenance, bound, or integrity violation."""


def _fail(reason: str) -> None:
    raise ReferenceAssetsError(reason)


def select_set(issue_body: str) -> str:
    """Exact full-line selection; '' when no line, error on many/malformed."""
    body = issue_body or ""
    attempts = [line for line in body.splitlines() if line.startswith("Reference-set:")]
    if not attempts:
        return ""
    if len(attempts) > 1:
        _fail("multiple Reference-set lines")
    match = re.fullmatch(r"Reference-set: (\S+)\s*", attempts[0])
    if not match or not SLUG_RE.match(match.group(1)):
        _fail("malformed Reference-set name")
    return match.group(1)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        _fail(f"git {args[0]} failed: {result.stderr.strip()[:200]}")
    return result.stdout


def _tracked_clean_files(root: Path, set_name: str) -> list[str]:
    prefix = f"references/{set_name}/"
    tracked = [
        line for line in _git(root, "ls-files", "--", prefix).splitlines() if line
    ]
    if not tracked:
        _fail(f"unknown or empty reference set: {set_name}")
    dirty = _git(root, "status", "--porcelain", "--", prefix).strip()
    if dirty:
        _fail(f"reference set has uncommitted changes: {dirty[:200]}")
    return sorted(tracked)


def _validate_file(root: Path, tracked_path: str, set_name: str) -> bytes:
    rel = tracked_path[len(f"references/{set_name}/") :]
    if not rel or ".." in rel.split("/"):
        _fail(f"path escape: {tracked_path}")
    if Path(rel).name in RESERVED_NAMES:
        _fail(f"reserved file name in set: {rel}")
    source = root / tracked_path
    if source.is_symlink() or not source.is_file():
        _fail(f"not a regular file: {tracked_path}")
    raw = source.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        _fail(f"file exceeds {MAX_FILE_BYTES} bytes: {rel}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail(f"not UTF-8 text: {rel}")
    return raw


def stage_set(root: Path, feature: str, set_name: str) -> str:
    root = Path(root)
    if not SLUG_RE.match(feature or ""):
        _fail("feature_name is not a canonical slug")
    if not SLUG_RE.match(set_name or ""):
        _fail("set name is not a canonical slug")
    tracked = _tracked_clean_files(root, set_name)
    if len(tracked) > MAX_FILES:
        _fail(f"set exceeds {MAX_FILES} files")
    contents: dict[str, bytes] = {}
    total = 0
    for tracked_path in tracked:
        raw = _validate_file(root, tracked_path, set_name)
        total += len(raw)
        if total > MAX_SET_BYTES:
            _fail(f"set exceeds {MAX_SET_BYTES} bytes")
        contents[tracked_path[len(f"references/{set_name}/") :]] = raw

    feature_dir = root / "features" / feature
    if feature_dir.is_symlink():
        _fail("feature directory is a symlink")
    reference_dir = feature_dir / "reference"
    if reference_dir.exists() or reference_dir.is_symlink():
        _fail("reference/ already exists")

    commit = _git(root, "rev-parse", "HEAD").strip()
    manifest = {
        "version": 1,
        "set": set_name,
        "commit": commit,
        "files": [
            {"path": rel, "sha256": hashlib.sha256(raw).hexdigest()}
            for rel, raw in sorted(contents.items())
        ],
    }
    encoded = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")

    staging = feature_dir / ".reference.tmp"
    try:
        for rel, raw in contents.items():
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (staging / "manifest.json").write_bytes(encoded)
        os.rename(staging, reference_dir)
    except OSError as exc:
        _fail(f"staging failed: {exc}")
    finally:
        if staging.exists():
            import shutil

            shutil.rmtree(staging, ignore_errors=True)
    return hashlib.sha256(encoded).hexdigest()


def verify_set(root: Path, feature: str, expected_sha256: str) -> None:
    root = Path(root)
    if not SLUG_RE.match(feature or ""):
        _fail("feature_name is not a canonical slug")
    reference_dir = root / "features" / feature / "reference"
    if expected_sha256 == "":
        if reference_dir.exists() or reference_dir.is_symlink():
            _fail("reference/ exists but no set was staged")
        return
    if not re.match(r"^[0-9a-f]{64}$", expected_sha256):
        _fail("expected hash is not a lowercase sha256")
    manifest_file = reference_dir / "manifest.json"
    if manifest_file.is_symlink() or not manifest_file.is_file():
        _fail("manifest.json missing or not a regular file")
    raw = manifest_file.read_bytes()
    import hmac

    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
        _fail("manifest hash mismatch")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"manifest is not strict UTF-8 JSON: {exc}")
    if (
        not isinstance(manifest, dict)
        or manifest.get("version") != 1
        or not re.match(r"^[0-9a-f]{40}$", str(manifest.get("commit", "")))
        or not SLUG_RE.match(str(manifest.get("set", "")))
        or not isinstance(manifest.get("files"), list)
    ):
        _fail("manifest has invalid schema")
    listed = set()
    for entry in manifest["files"]:
        rel = entry["path"]
        listed.add(rel)
        target = reference_dir / rel
        if target.is_symlink() or not target.is_file():
            _fail(f"listed file missing or irregular: {rel}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            _fail(f"file hash mismatch: {rel}")
    on_disk = {
        str(p.relative_to(reference_dir))
        for p in reference_dir.rglob("*")
        if p.is_file() or p.is_symlink()
    } - {"manifest.json"}
    if on_disk != listed:
        _fail(f"unlisted or missing files: {sorted(on_disk ^ listed)[:5]}")


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["select"] and len(argv) == 1:
            print(select_set(os.environ.get("ISSUE_BODY", "")))
            return 0
        if argv[:1] == ["stage"] and len(argv) == 3:
            print(stage_set(Path.cwd(), argv[1], argv[2]))
            return 0
        if argv[:1] == ["verify"] and len(argv) == 3:
            verify_set(Path.cwd(), argv[1], argv[2])
            return 0
        print("usage: reference_assets select|stage|verify ...", file=sys.stderr)
        return 2
    except ReferenceAssetsError as exc:
        print(f"reference_assets: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
