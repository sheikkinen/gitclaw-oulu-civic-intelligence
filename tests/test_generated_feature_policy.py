"""Generated-feature policy must stay aligned across all pipeline stages."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
POLICY_PATH = "policy/generated-features.md"
PROMPTS = {
    "plan": "prompts/plan.yaml",
    "judge": "prompts/judge.yaml",
    "enforce": "prompts/enforce.yaml",
    "review": "prompts/review.yaml",
}
BANNED_TOOL_EXCLUSIONS = (
    "YAMLGraph-only artifacts",
    "graph.yaml plus prompts/",
    "YAML-only implementation",
    "graph + prompts only",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_policy_defines_read_only_public_tool_boundary():
    policy = " ".join(read(POLICY_PATH).lower().split())
    required = (
        "issue-generated features",
        "pre-shipped fixtures",
        "optional contained artifacts",
        "get",
        "head",
        "public origins explicitly named",
        "finite connect and read timeouts",
        "bounded response",
        "must not read environment variables",
        "post",
        "delete",
        "external writes",
        "not a sandbox",
    )
    assert all(marker in policy for marker in required)


def test_all_stages_reference_shared_policy():
    for prompt in PROMPTS.values():
        assert POLICY_PATH in read(prompt)


def test_stages_state_distinct_policy_responsibilities():
    expected = {
        "plan": ("public origins", "failure semantics", "contained tools"),
        "judge": ("Permit", "read-only public tools", "Reject"),
        "enforce": ("optional contained tools", "frozen"),
        "review": ("every generated feature path", "tools and tests"),
    }
    for stage, markers in expected.items():
        prompt = read(PROMPTS[stage])
        assert all(marker in prompt for marker in markers)


def test_judge_and_enforce_do_not_exclude_tools():
    text = read(PROMPTS["judge"]) + read(PROMPTS["enforce"])
    assert not any(banned in text for banned in BANNED_TOOL_EXCLUSIONS)


def test_policy_defines_composition_as_the_only_cross_feature_channel():
    policy = " ".join(read(POLICY_PATH).lower().split())
    required = (
        "composition.json",
        "source_snapshots",
        "partial and all-dependency failure",
        "only cross-feature channel",
        "must not import or read another feature directory",
        "inspect prior `outputs/`",
    )
    assert all(marker in policy for marker in required)


def test_all_stages_apply_composition_boundary():
    for prompt in PROMPTS.values():
        text = read(prompt)
        assert "composition" in text.lower()
        assert "source_snapshots" in text
        assert "sibling" in text.lower()


def test_policy_and_all_stages_require_exact_candidate_output_key():
    policy = read(POLICY_PATH)
    assert "state_key: candidate" in policy
    assert "arbitrary state" in policy.lower()
    for prompt in PROMPTS.values():
        text = read(prompt)
        assert "state_key: candidate" in text
        assert "arbitrary state" in text.lower()


def test_policy_binds_immutable_owner_request():
    policy = " ".join(read(POLICY_PATH).lower().split())
    assert "request.json" in policy
    assert "immutable" in policy
    assert "untrusted data" in policy


def test_plan_judge_review_bind_request_artifact():
    for stage in ("plan", "judge", "review"):
        assert "request.json" in read(PROMPTS[stage])


def test_judge_and_review_keep_three_verdicts_with_rejection_boundary():
    for stage in ("judge", "review"):
        text = read(PROMPTS[stage])
        assert "**Verdict:** APPROVED" in text
        assert "**Verdict:** APPROVED WITH REVISIONS" in text
        assert "**Verdict:** REJECTED" in text
        assert "REJECTED" in " ".join(text.split())
        assert "owner" in text.lower()


def test_enforce_cannot_mutate_authority_and_consumes_review_findings():
    text = read(PROMPTS["enforce"])
    assert "fold every required revision" not in text
    normalized = " ".join(text.split())
    assert "must not" in normalized
    assert "request.json" in normalized
    assert (
        "review.md and treat its findings as additive implementation constraints"
        in normalized
    )


def test_judge_revisions_must_be_implementable_without_authority_edits():
    normalized = " ".join(read(PROMPTS["judge"]).split())
    assert "implementable without editing" in normalized
    assert "rewriting" in normalized or "rewrite" in normalized


def test_review_treats_judgement_revisions_as_controlling_over_frozen_prose():
    normalized = " ".join(read(PROMPTS["review"]).split())
    assert "as amended by" in normalized
    assert "not a defect" in normalized or "not a blocking finding" in normalized


def test_policy_binds_reference_assets_as_data_with_provenance():
    policy = " ".join(read(POLICY_PATH).lower().split())
    assert "reference" in policy
    assert "never executed" in policy
    assert "owner-committed" in policy


def test_all_stages_carry_reference_duties():
    markers = {
        "plan": ("reference/", "declare"),
        "judge": ("reference", "consistency"),
        "enforce": ("adapt the reference", "must not modify"),
        "review": ("reference", "undeclared divergence"),
    }
    for stage, needles in markers.items():
        normalized = " ".join(read(PROMPTS[stage]).split())
        for needle in needles:
            assert needle.lower() in normalized.lower(), (stage, needle)
