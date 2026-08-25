"""The five verification gates, and the zero-weight evidence rule."""

from datetime import datetime, timezone

import pytest

from app.ai.rag.anchors import check_anchor_preservation, required_anchors
from app.ai.rag.gates import GATE_NAMES, verify_item
from app.catalog.igot_adapter import IGotAdapter, IntegrationNotAuthorized
from app.engines.competency import CompetencyStatus, EvidenceInput, calculate_competency
from app.engines.constants import EVIDENCE_TYPE_WEIGHTS

NOW = datetime(2026, 8, 25, tzinfo=timezone.utc)

PASSAGE = (
    "Among rural households, average monthly per-capita expenditure in 2023-24 "
    "was 4,200 rupees, measured over a reference period of 30 days."
)


# ---------------------------------------------------------------------------
# G3 - anchor preservation (the statistics-specific gate)
# ---------------------------------------------------------------------------


def test_passage_with_a_quantitative_claim_requires_anchors():
    required = required_anchors(PASSAGE)
    assert "population" in required
    assert "reference_period" in required
    assert "unit_of_analysis" in required


def test_narrative_prose_requires_no_anchors():
    """Demanding a denominator from a narrative sentence would be noise."""
    assert required_anchors("Editing detects and resolves errors before estimation.") == []


def test_item_dropping_the_reference_period_is_rejected():
    """The headline failure mode: a correct passage, a wrong question."""
    result = check_anchor_preservation(
        passage=PASSAGE,
        item_text="What was average expenditure? 4,200 rupees",
    )

    assert result.passed is False
    assert "reference_period" in result.missing
    assert "not incomplete, it is wrong" in result.note


def test_item_preserving_every_anchor_passes():
    result = check_anchor_preservation(
        passage=PASSAGE,
        item_text=(
            "Among rural households, what was average monthly per-capita "
            "expenditure in 2023-24? 4,200 rupees"
        ),
    )
    assert result.passed is True
    assert result.missing == []


# ---------------------------------------------------------------------------
# The gate stack
# ---------------------------------------------------------------------------


def good_item() -> dict:
    return {
        "stem": (
            "Among rural households, complete the statement: average monthly "
            "per-capita expenditure in 2023-24 over a 30 day reference period "
            "was ______."
        ),
        "options": ["4,200 rupees", "8,400 rupees", "2,100 rupees", "6,300 rupees"],
        "correct_index": 0,
        "source_quote": PASSAGE,
        "chunk_text": PASSAGE,
    }


def test_a_well_formed_item_passes_every_gate():
    result = verify_item(**good_item())
    assert result.passed is True, result.note
    assert result.failed_gate is None
    assert {o.gate for o in result.outcomes} >= {"G1", "G2", "G3", "G4"}


def test_g1_rejects_an_invented_citation():
    item = good_item()
    item["source_quote"] = "The survey achieved a 92 percent response rate."
    result = verify_item(**item)

    assert result.passed is False
    assert result.failed_gate == "G1"


def test_g3_rejects_a_dropped_anchor_and_names_the_gate():
    """R3's demo moment: show the rejection bin with the failing gate named."""
    item = good_item()
    item["stem"] = "What was average expenditure?"
    result = verify_item(**item)

    assert result.passed is False
    assert result.failed_gate == "G3"
    assert result.failed_gate_name == "Anchor preservation"
    assert "G3" in result.note


def test_g4_rejects_all_of_the_above():
    item = good_item()
    item["options"] = [*item["options"][:3], "All of the above"]
    result = verify_item(**item)

    assert result.passed is False
    assert result.failed_gate == "G4"


def test_g4_rejects_duplicate_options():
    # Duplicated *distractors*, so G2 (a second grounded answer) does not fire
    # first and mask the structural problem.
    item = good_item()
    item["options"] = ["4,200 rupees", "9,900 rupees", "9,900 rupees", "6,300 rupees"]
    assert verify_item(**item).failed_gate == "G4"


def test_g2_rejects_a_second_defensible_answer():
    """Two options supported by the passage means two defensible answers."""
    item = good_item()
    item["options"] = [
        "4,200 rupees",
        "measured over a reference period of 30 days",  # also in the passage
        "2,100 rupees",
        "6,300 rupees",
    ]
    result = verify_item(**item)

    assert result.passed is False
    assert result.failed_gate == "G2"


def test_every_gate_has_a_readable_name():
    assert set(GATE_NAMES) == {"G1", "G2", "G3", "G4", "G5"}
    assert all(name for name in GATE_NAMES.values())


# ---------------------------------------------------------------------------
# Course completion carries zero weight
# ---------------------------------------------------------------------------


def test_course_completion_is_weighted_exactly_zero():
    """A stated design position, not a tuning choice."""
    assert EVIDENCE_TYPE_WEIGHTS["course_completion"] == 0.0


def test_simulation_is_the_heaviest_evidence_type():
    weights = EVIDENCE_TYPE_WEIGHTS
    assert weights["simulation"] == max(weights.values())


def test_a_perfect_course_score_establishes_nothing():
    """The demo's headline: 100% on a course, and still no competency."""
    result = calculate_competency(
        1,
        [EvidenceInput(1, "course_completion", 1.0, NOW, "accepted")],
        NOW,
    )

    assert result.status == CompetencyStatus.NO_EVIDENCE
    assert result.mastery is None
    assert result.level == 0
    assert result.effective_evidence == 0.0
    assert any("weighted 0.0 by design" in line for line in result.explanation)


def test_many_course_completions_still_establish_nothing():
    """No quantity of attendance adds up to demonstrated capability."""
    evidence = [
        EvidenceInput(i, "course_completion", 1.0, NOW, "accepted") for i in range(1, 21)
    ]
    assert calculate_competency(1, evidence, NOW).status == CompetencyStatus.NO_EVIDENCE


def test_zero_weight_evidence_does_not_crash_the_engine():
    """Weight 0.0 must not produce a divide-by-zero."""
    mixed = [
        EvidenceInput(1, "course_completion", 1.0, NOW, "accepted"),
        EvidenceInput(2, "assessment", 0.5, NOW, "accepted"),
    ]
    result = calculate_competency(1, mixed, NOW)

    # The assessment alone determines mastery; the course contributes nothing.
    assert result.mastery == pytest.approx(0.5, abs=1e-6)


# ---------------------------------------------------------------------------
# iGOT boundary
# ---------------------------------------------------------------------------


def test_igot_adapter_refuses_rather_than_faking_a_response():
    adapter = IGotAdapter()

    with pytest.raises(IntegrationNotAuthorized) as excinfo:
        adapter.find_for_competency("COMP-SAMP")

    message = str(excinfo.value)
    assert "not authorised" in message
    assert "does not fabricate" in message


def test_igot_adapter_never_claims_a_live_integration():
    assert IGotAdapter.is_live_integration is False
    assert IGotAdapter.authorisation_required


# ---------------------------------------------------------------------------
# Gate bench endpoint
# ---------------------------------------------------------------------------


def _bench_payload(stem: str) -> dict:
    return {
        "passage": PASSAGE,
        "stem": stem,
        "options": ["4,200 rupees", "8,400 rupees", "2,100 rupees", "6,300 rupees"],
        "correct_index": 0,
    }


def test_gate_bench_catches_a_dropped_reference_period(client, seeded_learner):
    """The demo moment: a correct passage, a question a generic AI would write."""
    from tests.conftest import auth_header, login

    token = login(client, "sme@sakshya.dev", seeded_learner)
    response = client.post(
        "/api/v1/questions/check-gates",
        headers=auth_header(token),
        json=_bench_payload("What was average expenditure?"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is False
    assert body["failed_gate"] == "G3"
    assert body["failed_gate_name"] == "Anchor preservation"
    assert len(body["outcomes"]) >= 4


def test_gate_bench_passes_a_context_preserving_item(client, seeded_learner):
    from tests.conftest import auth_header, login

    token = login(client, "sme@sakshya.dev", seeded_learner)
    response = client.post(
        "/api/v1/questions/check-gates",
        headers=auth_header(token),
        json=_bench_payload(
            "Among rural households, what was average monthly per-capita "
            "expenditure in 2023-24 over a 30 day reference period?"
        ),
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_gate_bench_stores_nothing(client, seeded_learner):
    from tests.conftest import auth_header, login

    token = login(client, "sme@sakshya.dev", seeded_learner)
    before = client.get("/api/v1/questions/summary", headers=auth_header(token)).json()

    client.post(
        "/api/v1/questions/check-gates",
        headers=auth_header(token),
        json=_bench_payload("What was average expenditure?"),
    )

    after = client.get("/api/v1/questions/summary", headers=auth_header(token)).json()
    assert after["total"] == before["total"]


def test_gate_bench_is_not_open_to_learners(client, seeded_learner):
    from tests.conftest import auth_header, login

    token = login(client, "learner@sakshya.dev", seeded_learner)
    response = client.post(
        "/api/v1/questions/check-gates",
        headers=auth_header(token),
        json=_bench_payload("What was average expenditure?"),
    )
    assert response.status_code == 403
