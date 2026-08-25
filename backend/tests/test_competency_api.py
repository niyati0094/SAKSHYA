"""Competency profile, evidence ledger and explainability endpoints."""

import pytest

from tests.conftest import auth_header, login


def learner_token(client, password: str) -> str:
    return login(client, "learner@sakshya.dev", password)


def get_profile(client, password: str) -> dict:
    response = client.get(
        "/api/v1/me/competency-profile", headers=auth_header(learner_token(client, password))
    )
    assert response.status_code == 200, response.text
    return response.json()


def find(profile: dict, code: str) -> dict:
    return next(
        entry for entry in profile["competencies"] if entry["competency"]["code"] == code
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_profile_returns_the_full_role_competency_map(client, seeded_learner):
    profile = get_profile(client, seeded_learner)

    assert profile["role"]["code"] == "JSO-PROTO"
    assert profile["role"]["is_prototype_data"] is True
    assert len(profile["competencies"]) == 6
    assert profile["summary"]["total_competencies"] == 6


def test_profile_includes_competencies_with_no_evidence(client, seeded_learner):
    """A competency with no evidence is information, not a row to hide."""
    profile = get_profile(client, seeded_learner)
    entry = find(profile, "COMP-ADMIN")

    assert entry["result"]["status"] == "no_evidence"
    assert entry["result"]["mastery"] is None


def test_sampling_design_is_below_target(client, seeded_learner):
    """The seeded gap the demo turns on."""
    entry = find(get_profile(client, seeded_learner), "COMP-SAMP")

    assert entry["target_level"] == 3
    assert entry["criticality"] == "critical"
    assert entry["meets_target"] is False
    assert entry["result"]["level"] < entry["target_level"]


def test_course_completion_alone_yields_insufficient_evidence(client, seeded_learner):
    """95% on a course must not establish competency."""
    entry = find(get_profile(client, seeded_learner), "COMP-NRES")

    assert entry["result"]["status"] == "insufficient_evidence"
    assert entry["result"]["level"] == 0
    assert entry["meets_target"] is False


def test_competencies_with_strong_evidence_meet_target(client, seeded_learner):
    profile = get_profile(client, seeded_learner)

    for code in ("COMP-QDES", "COMP-DQA", "COMP-SDC"):
        entry = find(profile, code)
        assert entry["meets_target"] is True, code
        assert entry["result"]["status"] == "established", code


def test_summary_counts_are_consistent_with_entries(client, seeded_learner):
    profile = get_profile(client, seeded_learner)
    summary = profile["summary"]

    meeting = sum(1 for e in profile["competencies"] if e["meets_target"])
    assert summary["meeting_target"] == meeting
    assert summary["below_target"] == len(profile["competencies"]) - meeting
    assert summary["meeting_target"] + summary["below_target"] == summary["total_competencies"]


# ---------------------------------------------------------------------------
# Explainability - the point of the whole system
# ---------------------------------------------------------------------------


def test_detail_explains_why_the_level_was_assigned(client, seeded_learner):
    token = learner_token(client, seeded_learner)
    profile = get_profile(client, seeded_learner)
    competency_id = find(profile, "COMP-SAMP")["competency"]["id"]

    response = client.get(f"/api/v1/me/competencies/{competency_id}", headers=auth_header(token))
    assert response.status_code == 200

    body = response.json()
    assert body["result"]["explanation"], "a level must always be explained"
    assert body["contributions"], "the evidence contributions must be itemised"
    assert body["evidence"], "the underlying evidence must be returned"
    assert body["method"]["evidence_type_weights"]["course_completion"] < 1.0


def test_contributions_let_the_mastery_be_recomputed_by_hand(client, seeded_learner):
    """The response must contain enough detail to verify the number independently."""
    token = learner_token(client, seeded_learner)
    profile = get_profile(client, seeded_learner)
    entry = find(profile, "COMP-SAMP")

    response = client.get(
        f"/api/v1/me/competencies/{entry['competency']['id']}", headers=auth_header(token)
    )
    body = response.json()

    counted = [c for c in body["contributions"] if c["counted"]]
    recomputed = sum(c["score"] * c["contribution_share"] for c in counted)

    # Shares are rounded to 4dp in the response, so allow only that much drift.
    assert recomputed == pytest.approx(body["result"]["mastery"], abs=1e-3)


def test_pending_evidence_is_visible_but_excluded(client, seeded_learner):
    """The audit trail shows unreviewed evidence and states why it did not count."""
    token = learner_token(client, seeded_learner)
    profile = get_profile(client, seeded_learner)
    competency_id = find(profile, "COMP-ADMIN")["competency"]["id"]

    body = client.get(
        f"/api/v1/me/competencies/{competency_id}", headers=auth_header(token)
    ).json()

    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["review_status"] == "pending"
    assert body["contributions"][0]["counted"] is False
    assert "not accepted" in body["contributions"][0]["excluded_reason"]


def test_method_endpoint_publishes_the_scoring_rules(client, seeded_learner):
    token = learner_token(client, seeded_learner)
    body = client.get("/api/v1/competency-method", headers=auth_header(token)).json()

    assert body["sufficiency_thresholds"]["min_effective_evidence"] > 0
    assert body["confidence_weights"]
    weights = body["evidence_type_weights"]
    assert weights["course_completion"] == min(weights.values())


def test_unknown_competency_returns_404(client, seeded_learner):
    token = learner_token(client, seeded_learner)
    response = client.get("/api/v1/me/competencies/99999", headers=auth_header(token))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Evidence ledger
# ---------------------------------------------------------------------------


def test_evidence_ledger_returns_all_records_newest_first(client, seeded_learner):
    token = learner_token(client, seeded_learner)
    response = client.get("/api/v1/me/evidence", headers=auth_header(token))

    assert response.status_code == 200
    ledger = response.json()
    assert len(ledger) == 11

    timestamps = [item["observed_at"] for item in ledger]
    assert timestamps == sorted(timestamps, reverse=True)
    assert all(item["is_prototype_data"] for item in ledger)


def test_evidence_ledger_can_be_filtered_by_competency(client, seeded_learner):
    token = learner_token(client, seeded_learner)
    profile = get_profile(client, seeded_learner)
    competency_id = find(profile, "COMP-SAMP")["competency"]["id"]

    ledger = client.get(
        f"/api/v1/me/evidence?competency_id={competency_id}", headers=auth_header(token)
    ).json()

    assert len(ledger) == 2
    assert all(item["competency_id"] == competency_id for item in ledger)


def test_learners_only_ever_see_their_own_evidence(client, seeded_learner):
    """The SME has no seeded evidence; the endpoint is scoped to the caller."""
    sme_token = login(client, "sme@sakshya.dev", seeded_learner)
    ledger = client.get("/api/v1/me/evidence", headers=auth_header(sme_token)).json()
    assert ledger == []


def test_competency_endpoints_require_authentication(client, seeded_learner):
    for path in ("/api/v1/me/competency-profile", "/api/v1/me/evidence", "/api/v1/competencies"):
        assert client.get(path).status_code == 401, path
