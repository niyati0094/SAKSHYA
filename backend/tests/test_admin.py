"""Admin analytics and evidence export."""

import csv
import io

from tests.conftest import auth_header, login


def overview(client, token) -> dict:
    response = client.get("/api/v1/admin/overview", headers=auth_header(token))
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_sees_the_cohort_overview(client, seeded_learner):
    token = login(client, "admin@sakshya.dev", seeded_learner)
    body = overview(client, token)

    assert body["learner_count"] >= 1
    assert body["learners_with_profile"] >= 1
    assert body["training_needs"]


def test_training_needs_are_ranked_by_reach_then_severity(client, seeded_learner):
    token = login(client, "admin@sakshya.dev", seeded_learner)
    needs = overview(client, token)["training_needs"]

    keys = [(-n["learners_with_gap"], -n["average_severity"], n["competency_code"]) for n in needs]
    assert keys == sorted(keys)


def test_unproven_competencies_are_counted_separately(client, seeded_learner):
    """A gap from missing evidence is a different problem from a low score."""
    token = login(client, "admin@sakshya.dev", seeded_learner)
    needs = overview(client, token)["training_needs"]

    nres = next(n for n in needs if n["competency_code"] == "COMP-NRES")
    assert nres["learners_unproven"] == 1

    samp = next(n for n in needs if n["competency_code"] == "COMP-SAMP")
    assert samp["learners_unproven"] == 0, "a measured shortfall is not 'unproven'"


def test_aggregates_agree_with_the_individual_profile(client, seeded_learner):
    """An organisation figure must not contradict the records it is built from."""
    admin = login(client, "admin@sakshya.dev", seeded_learner)
    learner = login(client, "learner@sakshya.dev", seeded_learner)

    org_total = overview(client, admin)["total_gaps"]
    personal = client.get("/api/v1/me/pathway", headers=auth_header(learner)).json()

    assert org_total == len(personal["gaps"])


def test_role_distribution_is_reported(client, seeded_learner):
    token = login(client, "admin@sakshya.dev", seeded_learner)
    distribution = overview(client, token)["role_distribution"]
    assert distribution
    assert sum(item["learner_count"] for item in distribution) >= 1


def test_only_admins_see_the_overview(client, seeded_learner):
    for email in ("learner@sakshya.dev", "sme@sakshya.dev"):
        token = login(client, email, seeded_learner)
        response = client.get("/api/v1/admin/overview", headers=auth_header(token))
        assert response.status_code == 403, email


def test_overview_requires_authentication(client):
    assert client.get("/api/v1/admin/overview").status_code == 401


# ---------------------------------------------------------------------------
# Evidence export
# ---------------------------------------------------------------------------


def test_evidence_exports_as_csv(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    response = client.get("/api/v1/me/evidence/export", headers=auth_header(token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 11
    assert rows[0]["competency_code"].startswith("COMP-")


def test_every_exported_row_is_flagged_as_prototype_data(client, seeded_learner):
    """An exported file must not be mistakable for an official record."""
    token = login(client, "learner@sakshya.dev", seeded_learner)
    response = client.get("/api/v1/me/evidence/export", headers=auth_header(token))

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert all(row["is_prototype_data"] == "True" for row in rows)


def test_export_is_scoped_to_the_caller(client, seeded_learner):
    token = login(client, "sme@sakshya.dev", seeded_learner)
    response = client.get("/api/v1/me/evidence/export", headers=auth_header(token))

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows == []


def test_export_requires_authentication(client):
    assert client.get("/api/v1/me/evidence/export").status_code == 401
