"""FR-841: owner reference assets — select/stage/verify contract."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from tools import reference_assets  # noqa: E402

SET_NAME = "probe-kit"
FEATURE = "exact-feature"


def make_repo(tmp_path, files=None):
    """Git repo with a committed reference set."""
    if files is None:
        files = {"a.sh": "#!/bin/sh\necho a ä🐾\n", "docs/b.md": "# b\n"}
    root = tmp_path / "repo"
    set_dir = root / "references" / SET_NAME
    for rel, text in files.items():
        target = set_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "seed"],
    ):
        subprocess.run(cmd, cwd=root, check=True, env=env, capture_output=True)
    return root


def stage(root):
    return reference_assets.stage_set(root, FEATURE, SET_NAME)


def manifest_path(root):
    return root / "features" / FEATURE / "reference" / "manifest.json"


# --- select -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("no selection here", ""),
        ("Reference-set: probe-kit", "probe-kit"),
        ("text before\nReference-set: probe-kit\ntext after", "probe-kit"),
        ("> quoted Reference-set: probe-kit", ""),
        ("reference-set: probe-kit", ""),
    ],
)
def test_select_full_line_semantics(body, expected):
    assert reference_assets.select_set(body) == expected


@pytest.mark.parametrize(
    "body",
    [
        "Reference-set: probe-kit\nReference-set: probe-kit",
        "Reference-set: probe-kit\nReference-set: other-set",
        "Reference-set: Bad_Name",
        "Reference-set: -leading",
        "Reference-set: ",
        "Reference-set: probe-kit is great",
    ],
)
def test_select_rejects_multiple_or_malformed(body):
    with pytest.raises(reference_assets.ReferenceAssetsError):
        reference_assets.select_set(body)


# --- stage ------------------------------------------------------------------


def test_stage_copies_tracked_files_and_prints_only_manifest_hash(tmp_path):
    root = make_repo(tmp_path)
    digest = stage(root)
    raw = manifest_path(root).read_bytes()
    assert digest == hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    assert data["version"] == 1
    assert data["set"] == SET_NAME
    assert len(data["commit"]) == 40
    assert [f["path"] for f in data["files"]] == ["a.sh", "docs/b.md"]
    copied = root / "features" / FEATURE / "reference" / "a.sh"
    assert "ä🐾" in copied.read_text()


def test_stage_rejects_unknown_untracked_modified_and_reserved(tmp_path):
    root = make_repo(tmp_path)
    with pytest.raises(reference_assets.ReferenceAssetsError):
        reference_assets.stage_set(root, FEATURE, "unknown-set")
    (root / "references" / SET_NAME / "untracked.md").write_text("new\n")
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(root)
    (root / "references" / SET_NAME / "untracked.md").unlink()
    (root / "references" / SET_NAME / "a.sh").write_text("modified\n")
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(root)


def test_stage_rejects_reserved_manifest_name(tmp_path):
    root = make_repo(tmp_path, {"a.sh": "a\n", "manifest.json": "{}\n"})
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(root)


def test_stage_rejects_bounds_and_binary(tmp_path):
    many = {f"f{i}.md": "x\n" for i in range(9)}
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(make_repo(tmp_path / "many", many))
    big = {"big.md": "x" * (256 * 1024 + 1)}
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(make_repo(tmp_path / "big", big))


def test_stage_rejects_symlink_and_preexisting_reference(tmp_path):
    root = make_repo(tmp_path)
    (root / "features" / FEATURE / "reference").mkdir(parents=True)
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(root)


def test_stage_failure_is_atomic(tmp_path):
    big = {"ok.md": "fine\n", "big.md": "x" * (256 * 1024 + 1)}
    root = make_repo(tmp_path, big)
    with pytest.raises(reference_assets.ReferenceAssetsError):
        stage(root)
    assert not (root / "features" / FEATURE / "reference").exists()


# --- verify -----------------------------------------------------------------


def test_verify_accepts_staged_set(tmp_path):
    root = make_repo(tmp_path)
    digest = stage(root)
    reference_assets.verify_set(root, FEATURE, digest)


def test_verify_empty_hash_requires_no_reference_dir(tmp_path):
    root = make_repo(tmp_path)
    reference_assets.verify_set(root, FEATURE, "")
    digest = stage(root)
    with pytest.raises(reference_assets.ReferenceAssetsError):
        reference_assets.verify_set(root, FEATURE, "")
    reference_assets.verify_set(root, FEATURE, digest)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda ref: (ref / "a.sh").write_text("tampered\n"),
        lambda ref: (ref / "manifest.json").write_text("{}\n"),
        lambda ref: (ref / "manifest.json").unlink(),
        lambda ref: (ref / "extra.md").write_text("smuggled\n"),
        lambda ref: (ref / "a.sh").unlink(),
    ],
)
def test_verify_rejects_tamper(tmp_path, tamper):
    root = make_repo(tmp_path)
    digest = stage(root)
    tamper(root / "features" / FEATURE / "reference")
    with pytest.raises(reference_assets.ReferenceAssetsError):
        reference_assets.verify_set(root, FEATURE, digest)


def test_verify_rejects_wrong_hash(tmp_path):
    root = make_repo(tmp_path)
    stage(root)
    with pytest.raises(reference_assets.ReferenceAssetsError):
        reference_assets.verify_set(root, FEATURE, "0" * 64)


# --- CLI --------------------------------------------------------------------


def test_cli_select_stage_verify_round_trip(tmp_path):
    root = make_repo(tmp_path)
    tools_root = Path(__file__).parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(tools_root),
        "ISSUE_BODY": f"Reference-set: {SET_NAME}",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }

    def cli(*args):
        return subprocess.run(
            [sys.executable, "-m", "tools.reference_assets", *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=root,
        )

    selected = cli("select")
    assert selected.returncode == 0 and selected.stdout.strip() == SET_NAME
    staged = cli("stage", FEATURE, SET_NAME)
    assert staged.returncode == 0, staged.stderr
    digest = staged.stdout.strip()
    assert len(digest) == 64
    assert cli("verify", FEATURE, digest).returncode == 0
    assert cli("verify", FEATURE, "0" * 64).returncode != 0
    no_selection = subprocess.run(
        [sys.executable, "-m", "tools.reference_assets", "select"],
        capture_output=True,
        text=True,
        env={**env, "ISSUE_BODY": "plain body"},
        cwd=root,
    )
    assert no_selection.returncode == 0 and no_selection.stdout.strip() == ""
