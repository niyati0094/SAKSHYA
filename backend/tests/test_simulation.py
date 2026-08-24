"""Simulation lab: deterministic scoring and evidence generation."""

import pytest

from app.engines.simulation import band_for, score_attempt
from app.simulations.catalog import SCENARIOS, get_scenario
from tests.conftest import auth_header, login


def best_answers(scenario) -> dict[str, str]:
    return {d.key: d.best_option.key for d in scenario.decisions}


def worst_answers(scenario) -> dict[str, str]:
    return {
        d.key: min(d.options, key=lambda option: option.credit).key
        for d in scenario.decisions
    }


# ---------------------------------------------------------------------------
# Rubric integrity
# ---------------------------------------------------------------------------


def test_three_scenarios_are_defined():
    assert {s.code for s in SCENARIOS} == {"SIM-NRES", "SIM-ADMIN", "SIM-SAMP"}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_every_option_carries_a_credit_and_a_rationale(scenario):
    for decision in scenario.decisions:
        assert len(decision.options) >= 3, decision.key
        assert {o.key for o in decision.options}.__len__() == len(decision.options)
        for option in decision.options:
            assert 0.0 <= option.credit <= 1.0
            assert option.rationale.strip(), f"{decision.key}/{option.key}"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_each_decision_has_exactly_one_strongest_option(scenario):
    """An ambiguous rubric would make scoring arbitrary."""
    for decision in scenario.decisions:
        top = max(o.credit for o in decision.options)
        assert top == 1.0, decision.key
        assert sum(1 for o in decision.options if o.credit == top) == 1, decision.key


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_each_scenario_maps_to_a_competency(scenario):
    assert scenario.competency_code.startswith("COMP-")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_scoring_is_deterministic(scenario):
    answers = best_answers(scenario)
    first, second = score_attempt(scenario, answers), score_attempt(scenario, answers)
    assert first == second


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_perfect_attempt_scores_full_marks(scenario):
    result = score_attempt(scenario, best_answers(scenario))
    assert result.percentage == 1.0
    assert result.band == "Strong"
    assert all(outcome.is_best for outcome in result.outcomes)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.code)
def test_worst_attempt_scores_below_a_perfect_one(scenario):
    assert (
        score_attempt(scenario, worst_answers(scenario)).percentage
        < score_attempt(scenario, best_answers(scenario)).percentage
    )


def test_unanswered_decisions_score_zero_and_are_reported():
    scenario = get_scenario("SIM-NRES")
    result = score_attempt(scenario, {})

    assert result.percentage == 0.0
    assert result.answered_count == 0
    assert all(not outcome.answered for outcome in result.outcomes)
    assert any("unanswered" in line for line in result.explanation)


def test_partial_attempt_does_not_score_as_a_complete_one():
    """Skipping a decision must not shrink the denominator."""
    scenario = get_scenario("SIM-NRES")
    full = best_answers(scenario)
    partial = {k: v for i, (k, v) in enumerate(full.items()) if i == 0}

    assert score_attempt(scenario, partial).percentage < 1.0


def test_unknown_option_key_is_treated_as_unanswered():
    scenario = get_scenario("SIM-SAMP")
    result = score_attempt(scenario, {d.key: "not-a-real-option" for d in scenario.decisions})
    assert result.percentage == 0.0
    assert result.answered_count == 0


def test_score_matches_a_hand_computation():
    """Weighted mean, computed independently of the engine."""
    scenario = get_scenario("SIM-SAMP")
    answers = {"design": "srs", "allocation": "neyman", "estimation": "weights"}

    expected_earned = 0.2 * 1.3 + 0.8 * 1.3 + 1.0 * 1.2
    expected_available = 1.3 + 1.3 + 1.2

    result = score_attempt(scenario, answers)
    assert result.score == pytest.approx(expected_earned, abs=1e-4)
    assert result.percentage == pytest.approx(expected_earned / expected_available, abs=1e-4)


@pytest.mark.parametrize(
    "pct,band",
    [(1.0, "Strong"), (0.85, "Strong"), (0.7, "Competent"), (0.5, "Developing"), (0.1, "Needs support")],
)
def test_bands(pct, band):
    assert band_for(pct) == band


def test_explanation_states_the_scoring_is_not_a_model_judgement():
    result = score_attempt(get_scenario("SIM-ADMIN"), best_answers(get_scenario("SIM-ADMIN")))
    assert any("not a model judgement" in line for line in result.explanation)


# ---------------------------------------------------------------------------
# API and evidence generation
# ---------------------------------------------------------------------------


def test_scenario_list_is_available(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    response = client.get("/api/v1/simulations", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_scenario_detail_hides_the_answer_key(client, seeded_learner):
    """Credits and rationales must not be readable before submitting."""
    token = login(client, "learner@sakshya.dev", seeded_learner)
    body = client.get("/api/v1/simulations/SIM-NRES", headers=auth_header(token)).json()

    payload = str(body)
    assert "credit" not in payload
    assert "rationale" not in payload
    assert body["decisions"][0]["options"]


def test_unknown_scenario_is_404(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    assert client.get("/api/v1/simulations/NOPE", headers=auth_header(token)).status_code == 404


def test_submitting_generates_evidence_and_moves_the_competency(client, seeded_learner):
    """The loop that matters: a simulation produces evidence that changes a level."""
    token = login(client, "learner@sakshya.dev", seeded_learner)
    scenario = get_scenario("SIM-NRES")

    def nres_entry():
        profile = client.get(
            "/api/v1/me/competency-profile", headers=auth_header(token)
        ).json()
        return next(
            e for e in profile["competencies"] if e["competency"]["code"] == "COMP-NRES"
        )

    before = nres_entry()
    assert before["result"]["status"] == "insufficient_evidence"

    response = client.post(
        f"/api/v1/simulations/{scenario.code}/submit",
        headers=auth_header(token),
        json={"answers": best_answers(scenario)},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["percentage"] == 1.0
    assert body["evidence_id"] is not None
    assert body["debrief"]

    after = nres_entry()
    assert after["result"]["status"] == "established", "evidence must establish the competency"
    assert after["result"]["counted_evidence_count"] > before["result"]["counted_evidence_count"]


def test_generated_evidence_is_a_simulation_record(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    scenario = get_scenario("SIM-SAMP")

    result = client.post(
        f"/api/v1/simulations/{scenario.code}/submit",
        headers=auth_header(token),
        json={"answers": best_answers(scenario)},
    ).json()

    ledger = client.get("/api/v1/me/evidence", headers=auth_header(token)).json()
    record = next(item for item in ledger if item["id"] == result["evidence_id"])

    assert record["evidence_type"] == "simulation"
    assert record["review_status"] == "accepted"
    assert record["is_prototype_data"] is True


def test_debrief_is_generated_after_scoring_and_does_not_change_it(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    scenario = get_scenario("SIM-ADMIN")
    answers = best_answers(scenario)

    body = client.post(
        f"/api/v1/simulations/{scenario.code}/submit",
        headers=auth_header(token),
        json={"answers": answers},
    ).json()

    # The API's score must equal the pure engine's score for the same answers.
    assert body["score"] == pytest.approx(score_attempt(scenario, answers).score, abs=1e-6)
    assert "did not influence the score" in body["debrief"]
    assert "not a model judgement" in " ".join(body["explanation"])


def test_attempt_can_be_retrieved_and_is_owner_scoped(client, seeded_learner):
    learner = login(client, "learner@sakshya.dev", seeded_learner)
    scenario = get_scenario("SIM-NRES")

    attempt_id = client.post(
        f"/api/v1/simulations/{scenario.code}/submit",
        headers=auth_header(learner),
        json={"answers": best_answers(scenario)},
    ).json()["attempt_id"]

    assert (
        client.get(
            f"/api/v1/simulations/attempts/{attempt_id}", headers=auth_header(learner)
        ).status_code
        == 200
    )

    sme = login(client, "sme@sakshya.dev", seeded_learner)
    assert (
        client.get(
            f"/api/v1/simulations/attempts/{attempt_id}", headers=auth_header(sme)
        ).status_code
        == 404
    ), "attempts must not be readable by another user"


def test_attempts_list_is_scoped_to_the_caller(client, seeded_learner):
    learner = login(client, "learner@sakshya.dev", seeded_learner)
    scenario = get_scenario("SIM-SAMP")
    client.post(
        f"/api/v1/simulations/{scenario.code}/submit",
        headers=auth_header(learner),
        json={"answers": best_answers(scenario)},
    )

    mine = client.get("/api/v1/simulations/attempts/mine", headers=auth_header(learner)).json()
    assert len(mine) == 1

    sme = login(client, "sme@sakshya.dev", seeded_learner)
    assert client.get(
        "/api/v1/simulations/attempts/mine", headers=auth_header(sme)
    ).json() == []


def test_simulation_requires_authentication(client):
    assert client.get("/api/v1/simulations").status_code == 401
    assert client.post("/api/v1/simulations/SIM-NRES/submit", json={"answers": {}}).status_code == 401
