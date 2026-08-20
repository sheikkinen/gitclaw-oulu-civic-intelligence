"""Bounded subprocess lifecycle tests for the GitClaw cron runner (FR-835)."""

import os
import sys
import time

import pytest

from tools import cron_run


def assert_process_exits(pid: int, message: str) -> None:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    pytest.fail(message)


def test_bounded_process_kills_child_when_stdout_limit_is_crossed():
    returncode, stdout, stderr, error = cron_run._run_bounded(
        [
            sys.executable,
            "-c",
            f"import sys; sys.stdout.buffer.write(b'x' * {cron_run.MAX_PROCESS_STDOUT_BYTES + 1})",
        ],
        timeout=5,
    )
    assert returncode != 0
    assert len(stdout) > cron_run.MAX_PROCESS_STDOUT_BYTES
    assert stderr == b""
    assert error == f"stdout exceeds {cron_run.MAX_PROCESS_STDOUT_BYTES} bytes"


def test_bounded_process_timeout_kills_descendant_process_group(tmp_path):
    pid_path = tmp_path / "child.pid"
    child_code = (
        "import os,time,pathlib; "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid())); "
        "time.sleep(60)"
    )
    parent_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        "time.sleep(60)"
    )
    _, _, _, error = cron_run._run_bounded(
        [sys.executable, "-c", parent_code], timeout=1
    )
    assert error == "timeout after 1s"
    assert_process_exits(
        int(pid_path.read_text()),
        "descendant process survived bounded-runner timeout",
    )


def test_bounded_process_timeout_applies_after_both_pipes_close():
    started = time.monotonic()
    _, _, _, error = cron_run._run_bounded(
        [
            sys.executable,
            "-c",
            "import os,time; os.close(1); os.close(2); time.sleep(60)",
        ],
        timeout=1,
    )
    assert error == "timeout after 1s"
    assert time.monotonic() - started < 3


def test_bounded_process_kills_group_after_session_leader_exits(tmp_path):
    pid_path = tmp_path / "orphan.pid"
    child_code = (
        "import os,time,pathlib; "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid())); "
        "time.sleep(60)"
    )
    parent_code = (
        f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child_code!r}])"
    )
    _, _, _, error = cron_run._run_bounded(
        [sys.executable, "-c", parent_code], timeout=1
    )
    assert error == "timeout after 1s"
    assert_process_exits(
        int(pid_path.read_text()), "descendant survived after session leader exited"
    )


def test_bounded_process_output_limit_kills_descendant_after_leader_exits(tmp_path):
    pid_path = tmp_path / "noisy-orphan.pid"
    child_code = (
        "import os,pathlib; "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid())); "
        "chunk=b'x'*65536; "
        "exec('while True:\\n os.write(1,chunk)')"
    )
    parent_code = (
        f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child_code!r}])"
    )
    _, _, _, error = cron_run._run_bounded(
        [sys.executable, "-c", parent_code], timeout=5
    )
    assert error == f"stdout exceeds {cron_run.MAX_PROCESS_STDOUT_BYTES} bytes"
    assert_process_exits(
        int(pid_path.read_text()),
        "descendant survived bounded-runner stdout limit",
    )


def test_bounded_process_rejects_descendant_that_closes_pipes(tmp_path):
    pid_path = tmp_path / "invisible-orphan.pid"
    child_code = (
        "import os,time,pathlib; "
        f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid())); "
        "os.close(1); os.close(2); time.sleep(60)"
    )
    parent_code = (
        f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child_code!r}])"
    )
    _, _, _, error = cron_run._run_bounded(
        [sys.executable, "-c", parent_code], timeout=5
    )
    assert error == "descendant processes outlived graph"
    assert_process_exits(
        int(pid_path.read_text()),
        "pipe-closing descendant survived graph completion",
    )
