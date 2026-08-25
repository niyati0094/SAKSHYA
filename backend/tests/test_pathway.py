"""Gap detection, recommendation ranking, and the iGOT integration boundary."""

from datetime import datetime, timezone

import pytest

from app.catalog import get_catalog
from app.catalog.base import LearningCatalogAdapter, ResourceKind
from app.engines.competency import CompetencyResult, CompetencyStatus, calculate_competency
from app.engines.gap import calculate_gap, rank_gaps, severity_band
from app.engines.recommender import choose_stage
from tests.conftest import auth_header, login

NOW = datetime(2026, 8, 25, tzinfo=timezone.utc)


def result_with(status: str, level: int, confidence: float) -> CompetencyResult:
    return CompetencyResult(
        competency_id=1,
        status=status,
        mastery=0.5,
        level=level,
        level_label="x",
        confidence=confidence,
        confidence_breakdown=None,
        evidence_count=1,
        counted_evidence_count=1,
        effective_evidence=1.0,
    )


def gap_for(status=CompetencyStatus.ESTABLISHED, level=1, target=3, confidence=0.8,
            criticality="critical"):
    return calculate_gap(
        competency_id=1,
        competency_code="COMP-X",
        competency_name="X",
        target_level=target,
        criticality=criticality,
        result=result_with(status, level, confidence),
    )


# ---------------------------------------------------------------------------
# Gap engine
# ---------------------------------------------------------------------------


def test_no_gap_when_target_is_met():
    assert gap_for(level=3, target=3) is None
    assert gap_for(level=4, target=3) is None


def test_gap_is_reported_when_below_target():
    gap = gap_for(level=2, target=3)
    assert gap is not None
    assert gap.level_shortfall == 1
    assert gap.severity > 0


def test_unproven_competency_is_a_full_gap_not_a_pass():
    """Not knowing whether someone can do something is a training need."""
    gap = gap_for(status=CompetencyStatus.NO_EVIDENCE, level=0, target=3, confidence=0.0)
    assert gap is not None
    assert gap.current_level == 0
    assert gap.level_shortfall == 3
    assert gap.evidence_limited is True


def test_insufficient_evidence_is_a_gap_even_with_a_high_level_value():
    """The 95%-course case must still register as a gap."""
    gap = calculate_gap(
        competency_id=1,
        competency_code="COMP-NRES",
        competency_name="Non-response",
        target_level=3,
        criticality="critical",
        result=result_with(CompetencyStatus.INSUFFICIENT_EVIDENCE, level=0, confidence=0.41),
    )
    assert gap is not None
    assert gap.evidence_limited is True
    assert any("too thin" in reason for reason in gap.reasons)


def test_larger_shortfall_is_more_severe():
    assert gap_for(level=1, target=3).severity > gap_for(level=2, target=3).severity


def test_critical_competency_outranks_a_medium_one_at_equal_shortfall():
    critical = gap_for(criticality="critical")
    medium = gap_for(criticality="medium")
    assert critical.severity > medium.severity


def test_lower_confidence_increases_severity():
    assert gap_for(confidence=0.2).severity > gap_for(confidence=0.9).severity


def test_gap_reasons_are_never_empty():
    assert gap_for().reasons


def test_criticality_appears_in_the_reasons():
    assert any("critical" in r.lower() for r in gap_for(criticality="critical").reasons)


def test_gap_calculation_is_deterministic():
    assert gap_for() == gap_for()


def test_ranking_is_severity_ordered_and_ties_break_deterministically():
    a = calculate_gap(competency_id=1, competency_code="COMP-B", competency_name="B",
                      target_level=3, criticality="high",
                      result=result_with(CompetencyStatus.ESTABLISHED, 2, 0.8))
    b = calculate_gap(competency_id=2, competency_code="COMP-A", competency_name="A",
                      target_level=3, criticality="high",
                      result=result_with(CompetencyStatus.ESTABLISHED, 2, 0.8))

    ranked = rank_gaps([a, b])
    assert [g.competency_code for g in ranked] == ["COMP-A", "COMP-B"]
    assert rank_gaps([a, b]) == rank_gaps([b, a])


@pytest.mark.parametrize(
    "severity,band",
    [(0.9, "urgent"), (0.6, "urgent"), (0.4, "significant"), (0.2, "moderate"), (0.05, "minor")],
)
def test_severity_bands(severity, band):
    assert severity_band(severity) == band


# ---------------------------------------------------------------------------
# Stage selection
# ---------------------------------------------------------------------------


def test_no_evidence_starts_with_learn():
    result = calculate_competency(1, [], NOW)
    assert choose_stage(result, set()) == ResourceKind.LEARN


def test_only_passive_evidence_leads_to_practice():
    """A course completion alone means read, not done."""
    result = result_with(CompetencyStatus.INSUFFICIENT_EVIDENCE, 0, 0.4)
    assert choose_stage(result, {"course_completion"}) == ResourceKind.PRACTICE


def test_having_practised_leads_to_prove():
    result = result_with(CompetencyStatus.ESTABLISHED, 2, 0.5)
    assert choose_stage(result, {"simulation"}) == ResourceKind.PROVE


# ---------------------------------------------------------------------------
# Catalogue / iGOT boundary
# ---------------------------------------------------------------------------


def test_local_adapter_satisfies_the_catalog_protocol():
    assert isinstance(get_catalog(), LearningCatalogAdapter)


def test_no_live_integration_is_claimed():
    """The boundary must never assert an iGOT integration that does not exist."""
    catalog = get_catalog()
    assert catalog.is_live_integration is False
    assert all(resource.is_prototype_data for resource in catalog.all_resources())


def test_catalog_resources_never_claim_to_be_igot():
    for resource in get_catalog().all_resources():
        assert "igot" not in resource.provider.lower()
        assert "karmayogi" not in resource.provider.lower()


def test_catalog_covers_every_seeded_competency():
    codes = {resource.competency_code for resource in get_catalog().all_resources()}
    assert {"COMP-SAMP", "COMP-NRES", "COMP-DQA", "COMP-ADMIN", "COMP-SDC"} <= codes


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.fixture
def learner(client, seeded_learner):
    return login(client, "learner@sakshya.dev", seeded_learner)


def pathway(client, token) -> dict:
    response = client.get("/api/v1/me/pathway", headers=auth_header(token))
    assert response.status_code == 200, response.text
    return response.json()


def test_pathway_reports_the_seeded_gaps(client, learner):
    body = pathway(client, learner)
    codes = {gap["competency_code"] for gap in body["gaps"]}

    # Below target, insufficient evidence, and no evidence respectively.
    assert {"COMP-SAMP", "COMP-NRES", "COMP-ADMIN"} <= codes
    # Competencies meeting target must not appear as gaps.
    assert "COMP-QDES" not in codes


def test_gaps_are_returned_most_severe_first(client, learner):
    severities = [gap["severity"] for gap in pathway(client, learner)["gaps"]]
    assert severities == sorted(severities, reverse=True)


def test_every_recommendation_explains_itself(client, learner):
    for item in pathway(client, learner)["recommendations"]:
        assert item["reasons"], item["competency_code"]
        assert len(item["reasons"]) >= 2
        assert item["stage"] in {"learn", "practice", "prove"}


def test_recommendations_follow_gap_ranking(client, learner):
    body = pathway(client, learner)
    ranks = [item["rank"] for item in body["recommendations"]]
    assert ranks == list(range(1, len(ranks) + 1))

    severities = [item["severity"] for item in body["recommendations"]]
    assert severities == sorted(severities, reverse=True)


def test_course_only_competency_is_told_to_practise_not_relearn(client, learner):
    """The learner passed the non-response course; the next step is doing, not reading."""
    body = pathway(client, learner)
    item = next(
        (r for r in body["recommendations"] if r["competency_code"] == "COMP-NRES"), None
    )
    assert item is not None
    assert item["stage"] in {"practice", "prove"}
    assert any("passive" in reason.lower() for reason in item["reasons"])


def test_competency_with_no_evidence_starts_at_learn(client, learner):
    body = pathway(client, learner)
    item = next(
        (r for r in body["recommendations"] if r["competency_code"] == "COMP-ADMIN"), None
    )
    if item is not None:
        assert item["stage"] == "learn"


def test_pathway_states_no_live_igot_integration(client, learner):
    catalog = pathway(client, learner)["catalog"]
    assert catalog["is_live_integration"] is False
    assert "no live igot" in catalog["notice"].lower()


def test_method_note_states_no_model_ranks_recommendations(client, learner):
    assert "no language model" in pathway(client, learner)["method_note"].lower()


def test_pathway_updates_after_a_simulation(client, learner):
    """Closing the loop: new evidence must change what is recommended."""
    before = pathway(client, learner)
    nres_before = next(g for g in before["gaps"] if g["competency_code"] == "COMP-NRES")

    from app.simulations.catalog import get_scenario

    scenario = get_scenario("SIM-NRES")
    client.post(
        "/api/v1/simulations/SIM-NRES/submit",
        headers=auth_header(learner),
        json={"answers": {d.key: d.best_option.key for d in scenario.decisions}},
    )

    after = pathway(client, learner)
    nres_after = next(
        (g for g in after["gaps"] if g["competency_code"] == "COMP-NRES"), None
    )

    assert nres_after is None or nres_after["severity"] < nres_before["severity"]


def test_catalog_endpoint_lists_prototype_resources(client, learner):
    resources = client.get("/api/v1/catalog", headers=auth_header(learner)).json()
    assert resources
    assert all(item["is_prototype_data"] for item in resources)


def test_pathway_requires_authentication(client):
    assert client.get("/api/v1/me/pathway").status_code == 401
    assert client.get("/api/v1/catalog").status_code == 401
