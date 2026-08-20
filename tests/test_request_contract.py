"""FR-840: immutable owner-request artifact writer/verifier contract."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from tools import request_contract  # noqa: E402

REPO = "sheikkinen/gitclaw"
FEATURE = "exact-feature"


def write(root, **overrides):
    kwargs = {
        "root": root,
        "feature": FEATURE,
        "issue_number": 7,
        "repository": REPO,
        "title": "Exact owner title",
        "body": "Exact owner body\nwith Ünïcode 🐾 and\nnewlines",
    }
    kwargs.update(overrides)
    return request_contract.write_request(**kwargs)


def artifact(root):
    return root / "features" / FEATURE / "request.json"


def test_write_creates_canonical_json_and_returns_only_hash(tmp_path):
    digest = write(tmp_path)
    raw = artifact(tmp_path).read_bytes()
    assert digest == hashlib.sha256(raw).hexdigest()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    data = json.loads(raw)
    assert data == {
        "version": 1,
        "repository": REPO,
        "issue_number": 7,
        "feature_name": FEATURE,
        "title": "Exact owner title",
        "body": "Exact owner body\nwith Ünïcode 🐾 and\nnewlines",
    }
    assert list(data) == sorted(data)  # sorted keys
    assert "\\u" not in raw.decode("utf-8")  # ensure_ascii=False


def test_write_round_trips_unicode_and_newlines(tmp_path):
    body = "ä\r\nö\n\tend🐾"
    write(tmp_path, body=body)
    assert json.loads(artifact(tmp_path).read_text())["body"] == body


@pytest.mark.parametrize(
    "overrides",
    [
        {"repository": ""},
        {"repository": "no-slash"},
        {"repository": "a/b/c"},
        {"feature": "Bad_Slug"},
        {"feature": "-leading"},
        {"feature": ""},
        {"issue_number": 0},
        {"issue_number": -3},
        {"title": ""},
        {"title": "x" * 257},
        {"body": ""},
        {"body": "x" * (1024 * 1024 + 1)},
        {"title": "nul\x00byte"},
        {"body": "nul\x00byte"},
    ],
)
def test_write_rejects_invalid_inputs(tmp_path, overrides):
    with pytest.raises(request_contract.RequestContractError):
        write(tmp_path, **overrides)
    assert not artifact(tmp_path).exists()  # atomic: no partial artifact


def test_write_rejects_preexisting_artifact(tmp_path):
    write(tmp_path)
    with pytest.raises(request_contract.RequestContractError):
        write(tmp_path)


def test_write_rejects_symlinked_parent(tmp_path):
    real = tmp_path / "real"
    real.mkdir(parents=True)
    features = tmp_path / "features"
    features.mkdir()
    (features / FEATURE).symlink_to(real)
    with pytest.raises(request_contract.RequestContractError):
        write(tmp_path)


def test_verify_accepts_written_artifact(tmp_path):
    digest = write(tmp_path)
    request_contract.verify_request(tmp_path, FEATURE, digest)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda p: p.write_bytes(p.read_bytes().replace(b"owner", b"OWNER")),
        lambda p: p.write_text(p.read_text() + " "),
        lambda p: p.unlink(),
        lambda p: p.write_text("not json\n"),
        lambda p: p.write_text('{"version": 1}\n'),
        lambda p: p.write_text(
            '{"version": 1, "repository": "sheikkinen/gitclaw", '
            '"issue_number": 7, "feature_name": "exact-feature", '
            '"title": "t", "body": "b", "extra": 1}\n'
        ),
        lambda p: p.write_text(
            '{"version": "1", "repository": "sheikkinen/gitclaw", '
            '"issue_number": 7, "feature_name": "exact-feature", '
            '"title": "t", "body": "b"}\n'
        ),
    ],
)
def test_verify_rejects_tampered_artifact(tmp_path, tamper):
    digest = write(tmp_path)
    tamper(artifact(tmp_path))
    with pytest.raises(request_contract.RequestContractError):
        request_contract.verify_request(tmp_path, FEATURE, digest)


def test_verify_rejects_wrong_hash_and_duplicate_keys(tmp_path):
    write(tmp_path)
    with pytest.raises(request_contract.RequestContractError):
        request_contract.verify_request(tmp_path, FEATURE, "0" * 64)
    dup = (
        '{"version": 1, "version": 1, "repository": "sheikkinen/gitclaw", '
        '"issue_number": 7, "feature_name": "exact-feature", '
        '"title": "t", "body": "b"}\n'
    )
    artifact(tmp_path).write_text(dup)
    digest = hashlib.sha256(dup.encode()).hexdigest()
    with pytest.raises(request_contract.RequestContractError):
        request_contract.verify_request(tmp_path, FEATURE, digest)


def test_verify_rejects_symlinked_artifact(tmp_path):
    digest = write(tmp_path)
    real = artifact(tmp_path)
    moved = tmp_path / "moved.json"
    moved.write_bytes(real.read_bytes())
    real.unlink()
    real.symlink_to(moved)
    with pytest.raises(request_contract.RequestContractError):
        request_contract.verify_request(tmp_path, FEATURE, digest)


def test_verify_rejects_feature_incoherence(tmp_path):
    digest = write(tmp_path)
    other = tmp_path / "features" / "other-feature"
    other.mkdir(parents=True)
    (other / "request.json").write_bytes(artifact(tmp_path).read_bytes())
    with pytest.raises(request_contract.RequestContractError):
        request_contract.verify_request(tmp_path, "other-feature", digest)


def test_cli_write_prints_only_hash_and_verify_round_trips(tmp_path):
    root = Path(__file__).parents[1]
    env = dict(os.environ)
    env.update(
        GITCLAW_REPOSITORY=REPO,
        ISSUE_TITLE="CLI title",
        ISSUE_BODY="CLI body 🐾\nsecond line",
        PYTHONPATH=str(root),
    )
    out = subprocess.run(
        [sys.executable, "-m", "tools.request_contract", "write", FEATURE, "9"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert out.returncode == 0, out.stderr
    digest = out.stdout.strip()
    assert len(digest) == 64 and digest == out.stdout.strip().lower()
    assert "CLI title" not in out.stdout + out.stderr
    assert "CLI body" not in out.stdout + out.stderr
    check = subprocess.run(
        [sys.executable, "-m", "tools.request_contract", "verify", FEATURE, digest],
        capture_output=True,
        text=True,
        env={**env, "PYTHONPATH": str(root)},
        cwd=tmp_path,
    )
    assert check.returncode == 0, check.stderr
    bad = subprocess.run(
        [sys.executable, "-m", "tools.request_contract", "verify", FEATURE, "0" * 64],
        capture_output=True,
        text=True,
        env={**env, "PYTHONPATH": str(root)},
        cwd=tmp_path,
    )
    assert bad.returncode != 0
    assert "CLI body" not in bad.stdout + bad.stderr
