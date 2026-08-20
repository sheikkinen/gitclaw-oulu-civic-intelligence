"""Composition boundary for the GitClaw cron runner (FR-835)."""

import json
from pathlib import Path

import pytest

from tools import cron_run


DATE = "2026-08-20"


def add_feature(root: Path, name: str, dependencies: list[str] | None = None) -> Path:
    feature = root / "features" / name
    feature.mkdir(parents=True)
    graph = feature / "graph.yaml"
    graph.touch()
    if dependencies is not None:
        (feature / "composition.json").write_text(
            json.dumps({"version": 1, "dependencies": dependencies}) + "\n"
        )
    return graph


def failed_reason(root: Path, name: str) -> str:
    path = root / "outputs" / f"{DATE}-{name}.failed.json"
    return json.loads(path.read_text())["reason"]


def test_load_manifest_accepts_strict_version_one(tmp_path):
    feature = add_feature(tmp_path, "composer", ["source-b", "source-a"])
    assert cron_run.load_manifest(feature.parent) == ("source-b", "source-a")


@pytest.mark.parametrize(
    "raw, marker",
    [
        ('{"version":1,"version":1,"dependencies":["source"]}', "duplicate key"),
        ('{"version":1,"dependencies":["source"],"extra":true}', "unknown key"),
        ('{"version":2,"dependencies":["source"]}', "version"),
        ('{"version":true,"dependencies":["source"]}', "version"),
        ('{"version":1,"dependencies":"source"}', "dependencies"),
        ('{"version":1,"dependencies":[]}', "non-empty"),
        ('{"version":1,"dependencies":["source","source"]}', "duplicate dependency"),
        ('{"version":1,"dependencies":["../source"]}', "canonical feature slug"),
        ('{"version":1,"dependencies":["/source"]}', "canonical feature slug"),
        ('{"version":1,"dependencies":[1]}', "canonical feature slug"),
    ],
)
def test_load_manifest_rejects_invalid_contract(tmp_path, raw, marker):
    graph = add_feature(tmp_path, "composer")
    (graph.parent / "composition.json").write_text(raw)
    with pytest.raises(cron_run.ManifestError, match=marker):
        cron_run.load_manifest(graph.parent)


def test_invalid_manifest_records_failure_but_unrelated_feature_runs(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "bad")
    (tmp_path / "features" / "bad" / "composition.json").write_text("not json")
    add_feature(tmp_path, "good")
    calls = []

    def fake_run(graph, date, extra_vars=None):
        calls.append((graph.parent.name, extra_vars))
        return True, f"candidate:{graph.parent.name}"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls == [("good", None)]
    assert "invalid composition.json" in failed_reason(tmp_path, "bad")
    assert "failed_recorded: bad:" in capsys.readouterr().err
    assert (tmp_path / "outputs" / f"{DATE}-good.md").exists()


def test_non_utf8_manifest_records_failure_but_unrelated_feature_runs(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "bad")
    (tmp_path / "features" / "bad" / "composition.json").write_bytes(b"\xff")
    add_feature(tmp_path, "good")
    calls = []

    def fake_run(graph, date, extra_vars=None):
        calls.append(graph.parent.name)
        return True, "ok"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls == ["good"]
    assert "invalid composition.json" in failed_reason(tmp_path, "bad")


def test_symlink_manifest_is_rejected(tmp_path):
    graph = add_feature(tmp_path, "composer")
    outside = tmp_path / "outside.json"
    outside.write_text('{"version":1,"dependencies":["source"]}')
    (graph.parent / "composition.json").symlink_to(outside)
    with pytest.raises(cron_run.ManifestError, match="regular file"):
        cron_run.load_manifest(graph.parent)


def test_dangling_symlink_manifest_is_rejected(tmp_path):
    graph = add_feature(tmp_path, "composer")
    (graph.parent / "composition.json").symlink_to(tmp_path / "missing.json")
    with pytest.raises(cron_run.ManifestError, match="regular file"):
        cron_run.load_manifest(graph.parent)


def test_oversize_manifest_is_rejected_before_read(tmp_path):
    graph = add_feature(tmp_path, "composer")
    (graph.parent / "composition.json").write_bytes(
        b"x" * (cron_run.MAX_MANIFEST_BYTES + 1)
    )
    with pytest.raises(cron_run.ManifestError, match="manifest exceeds"):
        cron_run.load_manifest(graph.parent)


def test_missing_dependency_blocks_dependents_not_unrelated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "composer", ["missing"])
    add_feature(tmp_path, "downstream", ["composer"])
    add_feature(tmp_path, "good")
    calls = []

    def fake_run(graph, date, extra_vars=None):
        calls.append(graph.parent.name)
        return True, "ok"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls == ["good"]
    assert "missing dependency: missing" in failed_reason(tmp_path, "composer")
    assert "unavailable dependency: composer" in failed_reason(tmp_path, "downstream")


def test_self_dependency_fails_closed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "selfish", ["selfish"])
    monkeypatch.setattr(
        cron_run, "run_feature", lambda graph, date, extra_vars=None: (True, "wrong")
    )
    assert cron_run.main(DATE) == 1
    assert "self-dependency" in failed_reason(tmp_path, "selfish")


def test_cycle_has_deterministic_path_and_blocks_dependent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "alpha", ["bravo"])
    add_feature(tmp_path, "bravo", ["charlie"])
    add_feature(tmp_path, "charlie", ["alpha"])
    add_feature(tmp_path, "downstream", ["bravo"])
    add_feature(tmp_path, "free")
    calls = []

    def fake_run(graph, date, extra_vars=None):
        calls.append(graph.parent.name)
        return True, "ok"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls == ["free"]
    expected = "dependency cycle: alpha -> bravo -> charlie -> alpha"
    assert failed_reason(tmp_path, "alpha") == expected
    assert failed_reason(tmp_path, "bravo") == expected
    assert failed_reason(tmp_path, "charlie") == expected
    assert "unavailable dependency: bravo" in failed_reason(tmp_path, "downstream")


def test_deep_acyclic_graph_is_scheduled_without_recursion(tmp_path):
    count = 1100
    for index in range(count):
        dependencies = None if index == 0 else [f"feature-{index - 1}"]
        add_feature(tmp_path, f"feature-{index}", dependencies)
    graphs = {
        graph.parent.name: graph
        for graph in sorted((tmp_path / "features").glob("*/graph.yaml"))
    }
    dependencies, errors = cron_run._validate_features(graphs)
    assert errors == {}
    order = cron_run._execution_order(dependencies, errors)
    assert order == [f"feature-{index}" for index in range(count)]


def test_dependency_order_cache_and_manifest_order_envelope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "source-a")
    add_feature(tmp_path, "source-b")
    add_feature(tmp_path, "composer-one", ["source-b", "source-a"])
    add_feature(tmp_path, "composer-two", ["source-a"])
    calls = []

    def fake_run(graph, date, extra_vars=None):
        name = graph.parent.name
        calls.append((name, extra_vars))
        return True, f"candidate:{name}\nUnicode: Oulu ä"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 0
    assert [name for name, _ in calls] == [
        "source-a",
        "source-b",
        "composer-one",
        "composer-two",
    ]
    one_vars = calls[2][1]
    assert list(one_vars) == ["source_snapshots"]
    assert json.loads(one_vars["source_snapshots"]) == [
        {
            "feature": "source-b",
            "status": "succeeded",
            "candidate": "candidate:source-b\nUnicode: Oulu ä",
        },
        {
            "feature": "source-a",
            "status": "succeeded",
            "candidate": "candidate:source-a\nUnicode: Oulu ä",
        },
    ]
    assert calls[3][1] == {
        "source_snapshots": json.dumps(
            [
                {
                    "feature": "source-a",
                    "status": "succeeded",
                    "candidate": "candidate:source-a\nUnicode: Oulu ä",
                }
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    }


@pytest.mark.parametrize("failed_sources", [{"source-b"}, {"source-a", "source-b"}])
def test_composer_runs_on_partial_and_all_dependency_failure(
    tmp_path, monkeypatch, failed_sources
):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "source-a")
    add_feature(tmp_path, "source-b")
    add_feature(tmp_path, "composer", ["source-a", "source-b"])
    calls = []

    def fake_run(graph, date, extra_vars=None):
        name = graph.parent.name
        calls.append((name, extra_vars))
        if name in failed_sources:
            return False, f"failed:{name}"
        return True, f"candidate:{name}"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls[-1][0] == "composer"
    envelope = json.loads(calls[-1][1]["source_snapshots"])
    for entry in envelope:
        if entry["feature"] in failed_sources:
            assert entry == {
                "feature": entry["feature"],
                "status": "failed",
                "reason": f"failed:{entry['feature']}",
            }
        else:
            assert entry["status"] == "succeeded"


def test_oversize_candidate_becomes_failure_without_truncation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    add_feature(tmp_path, "source")
    add_feature(tmp_path, "composer", ["source"])
    calls = []
    huge = "ä" * (cron_run.MAX_CANDIDATE_BYTES // 2 + 1)

    def fake_run(graph, date, extra_vars=None):
        calls.append((graph.parent.name, extra_vars))
        return True, huge if graph.parent.name == "source" else "composed"

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert "candidate exceeds 32768 UTF-8 bytes" == failed_reason(tmp_path, "source")
    envelope = json.loads(calls[-1][1]["source_snapshots"])
    assert envelope == [
        {
            "feature": "source",
            "status": "failed",
            "reason": "candidate exceeds 32768 UTF-8 bytes",
        }
    ]
    assert huge not in json.dumps(envelope)


def test_oversize_envelope_fails_composer_without_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dependency_count = 4
    for index in range(dependency_count):
        add_feature(tmp_path, f"source-{index}")
    add_feature(
        tmp_path,
        "composer",
        [f"source-{index}" for index in range(dependency_count)],
    )
    calls = []
    candidate = "x" * (cron_run.MAX_CANDIDATE_BYTES - 100)

    def fake_run(graph, date, extra_vars=None):
        calls.append(graph.parent.name)
        return True, candidate

    monkeypatch.setattr(cron_run, "run_feature", fake_run)
    assert cron_run.main(DATE) == 1
    assert calls == [f"source-{index}" for index in range(dependency_count)]
    assert "source_snapshots exceeds 98304 UTF-8 bytes" == failed_reason(
        tmp_path, "composer"
    )


def test_envelope_limit_stays_below_linux_single_argument_limit():
    assert cron_run.MAX_ENVELOPE_BYTES <= 96 * 1024


def test_run_feature_injects_only_explicit_extra_variables(tmp_path, monkeypatch):
    graph = add_feature(tmp_path, "composer")
    captured = {}

    def fake_process(command, timeout=600):
        captured["command"] = command
        return (
            0,
            json.dumps({"candidate": {"candidate": "done"}}).encode(),
            b"",
            None,
        )

    monkeypatch.setattr(cron_run, "_run_bounded", fake_process)
    assert cron_run.run_feature(
        graph,
        DATE,
        {"source_snapshots": '[{"feature":"source","status":"failed","reason":"x"}]'},
    ) == (True, "done")
    assert captured["command"] == [
        "yamlgraph",
        "graph",
        "run",
        str(graph),
        "--var",
        f"date={DATE}",
        "--var",
        'source_snapshots=[{"feature":"source","status":"failed","reason":"x"}]',
        "--json",
    ]


def test_three_plain_source_states_compose_in_order(tmp_path, monkeypatch):
    declared = ("source-c", "source-a", "source-b")
    candidates = {name: f"candidate:{name}\nUnicode: Oulu ä" for name in declared}
    captured_envelope = []

    def fake_process(command, timeout=600):
        graph = Path(command[3])
        name = graph.parent.name
        if name == "composer":
            value = command[command.index("--var", 6) + 1]
            captured_envelope.append(value.removeprefix("source_snapshots="))
            candidate = "assembled"
        else:
            candidate = candidates[name]
        state = {
            "date": DATE,
            "source_snapshots": "must not become output",
            "candidate": candidate,
        }
        return 0, json.dumps(state).encode(), b"", None

    monkeypatch.setattr(cron_run, "_run_bounded", fake_process)
    results = {}
    for name in declared:
        graph = add_feature(tmp_path, name)
        results[name] = cron_run.run_feature(graph, DATE)
        assert results[name] == (True, candidates[name])

    envelope_ok, envelope = cron_run._source_envelope(declared, results)
    assert envelope_ok is True
    composer = add_feature(tmp_path, "composer", list(declared))
    assert cron_run.run_feature(composer, DATE, {"source_snapshots": envelope}) == (
        True,
        "assembled",
    )
    assert captured_envelope == [envelope]
    assert json.loads(envelope) == [
        {
            "feature": name,
            "status": "succeeded",
            "candidate": candidates[name],
        }
        for name in declared
    ]


def test_run_feature_rejects_oversize_process_stdout(tmp_path, monkeypatch):
    graph = add_feature(tmp_path, "noisy")

    monkeypatch.setattr(
        cron_run,
        "_run_bounded",
        lambda command, timeout=600: (
            -9,
            b"",
            b"",
            f"stdout exceeds {cron_run.MAX_PROCESS_STDOUT_BYTES} bytes",
        ),
    )
    assert cron_run.run_feature(graph, DATE) == (
        False,
        f"stdout exceeds {cron_run.MAX_PROCESS_STDOUT_BYTES} bytes",
    )


def test_run_feature_spawn_error_is_recorded(tmp_path, monkeypatch):
    graph = add_feature(tmp_path, "composer")

    def fail_spawn(*args, **kwargs):
        raise OSError(7, "Argument list too long")

    monkeypatch.setattr(cron_run.subprocess, "Popen", fail_spawn)
    ok, reason = cron_run.run_feature(graph, DATE, {"source_snapshots": "x"})
    assert ok is False
    assert "spawn failed" in reason
    assert "Argument list too long" in reason
