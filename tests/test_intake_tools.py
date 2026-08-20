"""Slug + cron extraction + intake gate exit codes — RED specs."""

from pathlib import Path

from tools import cron_run, ledger, slug


def test_slug_kebab():
    assert (
        slug.make("Daily haiku about the weather in Oulu")
        == "daily-haiku-about-the-weather-in-oulu"
    )


def test_slug_strips_injection_chars():
    assert slug.make("evil; rm -rf / && $(curl x)|`y`") == "evil-rm-rf-curl-x-y"


def test_slug_bounded_and_nonempty():
    assert len(slug.make("x " * 100)) <= 40
    assert slug.make("!!! ???") == "feature"


def test_slug_unique_no_collision(tmp_path):
    assert slug.unique("Daily haiku", 7, root=tmp_path) == "daily-haiku"


def test_slug_unique_collision_appends_issue(tmp_path):
    # two similar titles must not share features/<name>/
    (tmp_path / "daily-haiku").mkdir()
    assert slug.unique("Daily haiku", 7, root=tmp_path) == "daily-haiku-7"


def test_slug_unique_collision_stays_bounded(tmp_path):
    long_title = "x " * 100
    (tmp_path / slug.make(long_title)).mkdir()
    s = slug.unique(long_title, 12345, root=tmp_path)
    assert len(s) <= 40 and s.endswith("-12345")


def test_run_feature_timeout_recorded(tmp_path, monkeypatch):
    # a hung feature must be recorded as failed, not crash the loop
    monkeypatch.setattr(
        cron_run,
        "_run_bounded",
        lambda command, timeout=600: (None, b"", b"", "timeout after 600s"),
    )
    ok, reason = cron_run.run_feature(
        tmp_path / "features" / "slow" / "graph.yaml", "2026-08-20"
    )
    assert ok is False and "timeout" in reason


def test_extract_output_nested_dict():
    # inline-schema LLM nodes nest: state.haiku == {'haiku': text}
    state = {"date": "2026-08-20", "haiku": {"haiku": "text here"}}
    assert cron_run.extract_output(state, "haiku") == "text here"


def test_extract_output_plain_str():
    assert cron_run.extract_output({"horoscope": "sunny"}, "horoscope") == "sunny"


def test_extract_output_plain_candidate_key():
    state = {
        "date": "2026-08-20",
        "run_instant": "2026-08-20T08:00:00Z",
        "source_snapshots": '[{"status":"failed"}]',
        "candidate": "source snapshot",
    }
    assert cron_run.extract_output(state, "different-feature-slug") == (
        "source snapshot"
    )


def test_extract_output_nested_candidate_key():
    state = {"date": "2026-08-20", "candidate": {"candidate": "snapshot"}}
    assert cron_run.extract_output(state, "different-feature-slug") == "snapshot"


def test_extract_output_single_value_dict():
    state = {"aphorism": {"result": "less is more"}}
    assert cron_run.extract_output(state, "aphorism") == "less is more"


def test_extract_output_missing_returns_none():
    # failed LLM nodes exit 0 with no state key — must not pass silently
    assert cron_run.extract_output({"date": "x", "errors": ["boom"]}, "haiku") is None


def test_extract_output_fallback_single_output_key():
    # generated graphs pick their own state_key (issue #3: 'aphorism'
    # inside dir daily-aphorism-about-software-craft)
    state = {"date": "2026-08-20", "aphorism": {"aphorism": "build less"}}
    assert (
        cron_run.extract_output(state, "daily-aphorism-about-software-craft")
        == "build less"
    )


def test_extract_output_ambiguous_fails_closed():
    state = {"date": "x", "a": {"a": "one"}, "b": {"b": "two"}}
    assert cron_run.extract_output(state, "no-such-key") is None


def test_extract_output_invalid_candidate_does_not_select_metadata():
    state = {
        "date": "2026-08-20",
        "run_instant": "2026-08-20T08:00:00Z",
        "source_snapshots": "input envelope",
        "candidate": {"first": "one", "second": "two"},
    }
    assert cron_run.extract_output(state, "different-feature-slug") is None


def test_extract_output_candidate_dict_requires_exact_self_key():
    assert (
        cron_run.extract_output(
            {"candidate": {"wrong": "leak"}}, "different-feature-slug"
        )
        is None
    )
    assert (
        cron_run.extract_output(
            {"candidate": {"candidate": "leak", "extra": "also"}},
            "different-feature-slug",
        )
        is None
    )


def test_extract_output_reserved_nested_metadata_is_not_output():
    for key in (
        "_agent_iterations",
        "_agent_limit_reached",
        "_loop_counts",
        "_loop_limit_reached",
        "date",
        "run_instant",
        "source_snapshots",
        "errors",
        "messages",
        "current_step",
    ):
        assert (
            cron_run.extract_output({key: {key: "leak"}}, "different-feature-slug")
            is None
        )


def test_extract_output_precedence_is_feature_then_candidate_then_legacy():
    state = {
        "feature": "feature output",
        "candidate": "candidate output",
        "legacy": {"legacy": "legacy output"},
    }
    assert cron_run.extract_output(state, "feature") == "feature output"
    assert cron_run.extract_output(state, "missing-feature") == "candidate output"


def test_extract_output_ignores_arbitrary_plain_state_strings():
    state = {"date": "2026-08-20", "unrelated": "must not publish"}
    assert cron_run.extract_output(state, "missing-feature") is None


def test_cron_main_exit_codes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("good", "poison"):
        (tmp_path / "features" / name).mkdir(parents=True)
        (tmp_path / "features" / name / "graph.yaml").touch()
    monkeypatch.setattr(
        cron_run,
        "run_feature",
        lambda g, d: (g.parent.name == "good", "text"),
    )
    assert cron_run.main("2026-08-20") == 1  # poison recorded, exit 1
    assert (tmp_path / "outputs" / "2026-08-20-good.md").exists()
    assert (tmp_path / "outputs" / "2026-08-20-poison.failed.json").exists()


def test_cron_output_carries_attribution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "features" / "good").mkdir(parents=True)
    (tmp_path / "features" / "good" / "graph.yaml").touch()
    monkeypatch.setattr(cron_run, "run_feature", lambda g, d: (True, "text"))
    assert cron_run.main("2026-08-20") == 0
    out = (tmp_path / "outputs" / "2026-08-20-good.md").read_text()
    assert out.startswith("text\n")
    assert "github.com/sheikkinen/gitclaw" in out
    assert "github.com/sheikkinen/yamlgraph" in out


def test_intake_gate_exit_codes(tmp_path):
    path = tmp_path / "issues.jsonl"
    repository = "sheikkinen/gitclaw"
    assert ledger.gate_code(path, repository, 5) == 0  # fresh: run
    ledger.record(path, repository, 5, "seen")
    ledger.record(path, repository, 5, "planned")
    assert ledger.gate_code(path, repository, 5) == 65  # interrupted
    ledger.record(path, repository, 5, "judged_rejected")
    assert ledger.gate_code(path, repository, 5) == 78  # terminal skip


ROOT = Path(__file__).parents[1]


def test_graph_carries_request_hash_not_owner_text():
    graph = (ROOT / "gitclaw.yaml").read_text()
    state_block = graph.split("state:")[1].split("tools:")[0]
    assert "request_sha256: str" in state_block
    assert "issue_title" not in state_block
    assert "issue_body" not in state_block
    for stage in ("plan", "judge", "enforce", "review"):
        assert f"from: {stage}\n    to: verify_request_after_{stage}" in graph


def test_graph_keeps_three_verdicts_and_gates_push_on_exact_approved():
    graph = (ROOT / "gitclaw.yaml").read_text()
    # judge vocabulary unchanged
    assert (
        "judge_verdict == 'APPROVED' or judge_verdict == 'APPROVED WITH REVISIONS'"
        in graph
    )
    # push gate is exact APPROVED only
    assert (
        "review_verdict == 'APPROVED' or review_verdict == 'APPROVED WITH REVISIONS'"
        not in graph
    )
    assert "condition: \"review_verdict == 'APPROVED'\"" in graph
    # FR-843: exactly one remediation lap, flat conditions only
    for verdict in ("REJECTED", "APPROVED WITH REVISIONS"):
        assert f"review_verdict == '{verdict}' and _loop_counts.enforce == null" in graph
        assert f"review_verdict == '{verdict}' and _loop_counts.enforce >= 1" in graph
        assert f"review_verdict == '{verdict}' and _loop_counts.enforce < 2" not in graph
    for line in graph.splitlines():
        if "condition:" in line:
            assert "(" not in line, line
    # unknown review verdicts still fail closed
    assert (
        "review_verdict != 'APPROVED' and review_verdict != 'REJECTED' "
        "and review_verdict != 'APPROVED WITH REVISIONS'" in graph
    )


def test_all_copilot_nodes_pin_sonnet_model():
    import yaml

    nodes = yaml.safe_load((ROOT / "gitclaw.yaml").read_text())["nodes"]
    for stage in ("plan", "judge", "enforce", "review"):
        assert nodes[stage]["cli_flags"]["model"] == "claude-sonnet-5", stage


def test_graph_verifies_reference_manifest_at_every_request_point():
    graph = (ROOT / "gitclaw.yaml").read_text()
    state_block = graph.split("state:")[1].split("tools:")[0]
    assert "reference_sha256: str" in state_block
    assert "reference_assets verify" in graph
    # the shared verify tool covers request and reference at the same points
    assert graph.count("request_contract verify") == graph.count(
        "reference_assets verify"
    )


def test_workflow_stages_reference_before_graph_and_passes_only_hash():
    workflow = (ROOT / ".github/workflows/intake.yml").read_text()
    assert "reference_assets select" in workflow
    assert "reference_assets stage" in workflow
    assert workflow.index("reference_assets") < workflow.index("yamlgraph graph run")
    assert 'reference_sha256="$REFERENCE_SHA256"' in workflow


def test_workflow_writes_request_before_graph_and_passes_only_hash():
    workflow = (ROOT / ".github/workflows/intake.yml").read_text()
    assert "request_contract" in workflow
    assert workflow.index("request_contract") < workflow.index("yamlgraph graph run")
    assert 'request_sha256="$REQUEST_SHA256"' in workflow
    assert "--var issue_title" not in workflow
    assert "--var issue_body" not in workflow


def test_workflow_never_inlines_owner_text_outside_env_blocks():
    lines = (ROOT / ".github/workflows/intake.yml").read_text().splitlines()
    for line in lines:
        if "github.event.issue.title" in line or "github.event.issue.body" in line:
            assert line.strip().startswith(("ISSUE_TITLE:", "ISSUE_BODY:")), line


def test_remediation_lap_re_verifies_request():
    limits = (ROOT / "gitclaw.yaml").read_text().split("loop_limits:")[1]
    assert "verify_request_after_enforce: 2" in limits
    assert "verify_request_after_review: 2" in limits


def _review_targets(verdict, enforce_count):
    import re
    import types

    graph = (ROOT / "gitclaw.yaml").read_text()
    edges = re.findall(
        r"- from: read_review_verdict\n"
        r"    to: (\S+)(?:\n    condition: \"([^\"]+)\")?",
        graph,
    )
    context = {
        "review_verdict": verdict,
        "_loop_counts": types.SimpleNamespace(enforce=enforce_count),
    }
    targets = []
    for target, condition in edges:
        if not condition:
            targets.append(target)
            continue
        try:
            if eval(condition.replace("null", "None"), {}, dict(context)):
                targets.append(target)
        except TypeError:
            continue  # e.g. None < 2: edge not taken
    return targets


def test_issue6_shaped_review_revisions_cannot_publish(tmp_path):
    # Issue-#6 shape: the owner request requires rejecting invalid input, a
    # generated review blesses fallback success as APPROVED WITH REVISIONS.
    # The artifact-extraction sed and the graph routing must send that run to
    # remediation or final rejection, never to publication.
    import subprocess

    review = tmp_path / "review.md"
    review.write_text(
        "# Review\n\n"
        "**Verdict:** APPROVED WITH REVISIONS - convert invalid\n"
        "source_snapshots into a successful unavailable candidate instead of\n"
        "rejecting, then publish.\n"
    )
    extracted = subprocess.run(
        [
            "/usr/bin/sed",
            "-n",
            r"s/^\*\*Verdict:\*\* \([A-Z][A-Z ]*[A-Z]\).*/\1/p",
            str(review),
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert extracted == "APPROVED WITH REVISIONS"
    # FR-843: remediation exactly once (enforce null/0 = no lap yet), then
    # visible terminal; 0-guard is the W803 defensive cover
    for verdict in (extracted, "REJECTED"):
        assert _review_targets(verdict, None) == ["ledger_reviewed_rejected"]
        assert _review_targets(verdict, 0) == ["ledger_reviewed_rejected"]
        assert _review_targets(verdict, 1) == ["reject_final"]
        assert _review_targets(verdict, 2) == ["reject_final"]
    assert _review_targets("APPROVED", None) == ["ledger_reviewed_approved"]
    assert _review_targets("GARBAGE VERDICT", None) == ["END"]
