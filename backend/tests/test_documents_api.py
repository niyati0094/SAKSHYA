"""Document upload, retrieval, question generation and SME review endpoints."""

import io

import pytest

from tests.conftest import auth_header, login

SAMPLE = b"""# Survey Methods

## 1. Sampling Frames

A sampling frame is the list or procedure that identifies every unit in the
target population. Undercoverage occurs when eligible units are absent from
the frame, so they have zero probability of selection and cannot be recovered
by any weighting adjustment applied later.

A frame with more than 5 percent undercoverage requires documented remedial
action before it is used in a production survey of any kind.

## 2. Imputation

Imputation replaces a missing item value with a constructed value so that the
analysis can proceed on a complete dataset without dropping records.
Hot-deck imputation copies a value from a similar responding unit called the
donor, preserving the shape of the distribution.
"""


def upload(client, token: str, *, name: str = "methods.md", data: bytes = SAMPLE):
    return client.post(
        "/api/v1/documents",
        headers=auth_header(token),
        files={"file": (name, io.BytesIO(data), "text/markdown")},
        data={"title": "Survey Methods (test)"},
    )


@pytest.fixture
def sme_token(client, seeded_learner):
    return login(client, "sme@sakshya.dev", seeded_learner)


@pytest.fixture
def uploaded(client, sme_token):
    response = upload(client, sme_token)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Upload and ingestion
# ---------------------------------------------------------------------------


def test_upload_runs_the_full_ingestion_pipeline(uploaded):
    """A 201 must mean the document is genuinely searchable, not just stored."""
    assert uploaded["status"] == "ready"
    assert uploaded["chunk_count"] > 0
    assert uploaded["is_prototype_data"] is True


def test_upload_rejects_an_empty_file(client, sme_token):
    response = upload(client, sme_token, data=b"")
    assert response.status_code == 400


def test_upload_rejects_an_unsupported_type(client, sme_token):
    response = client.post(
        "/api/v1/documents",
        headers=auth_header(sme_token),
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x00binary"), "application/x-msdownload")},
    )
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_text_with_no_readable_content(client, sme_token):
    response = upload(client, sme_token, data=b"   \n\n  \n")
    assert response.status_code in (400, 422)


def test_learners_may_not_upload(client, seeded_learner):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    assert upload(client, token).status_code == 403


def test_upload_requires_authentication(client):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("a.md", io.BytesIO(SAMPLE), "text/markdown")},
    )
    assert response.status_code == 401


def test_a_crafted_filename_cannot_escape_the_upload_directory(client, sme_token, db_session):
    """Path traversal in the filename must not decide where the file lands."""
    from pathlib import Path

    from app.models.document import Document
    from app.services.document_service import storage_dir

    response = upload(client, sme_token, name="../../../../evil.md")
    assert response.status_code == 201
    assert "stored_path" not in response.json(), "internal paths must never be exposed"

    document = db_session.get(Document, response.json()["id"])
    stored = Path(document.stored_path).resolve()

    assert stored.parent == storage_dir().resolve(), "file escaped the upload directory"
    assert ".." not in stored.name
    stored.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Chunks and retrieval
# ---------------------------------------------------------------------------


def test_chunks_carry_section_titles(client, sme_token, uploaded):
    response = client.get(
        f"/api/v1/documents/{uploaded['id']}/chunks", headers=auth_header(sme_token)
    )
    assert response.status_code == 200
    sections = {chunk["section_title"] for chunk in response.json()}
    assert "1. Sampling Frames" in sections


def test_search_returns_the_relevant_passage(client, sme_token, uploaded):
    response = client.get(
        f"/api/v1/documents/{uploaded['id']}/search",
        params={"q": "What is hot-deck imputation?"},
        headers=auth_header(sme_token),
    )
    assert response.status_code == 200

    hits = response.json()
    assert hits, "retrieval returned nothing"
    assert "imputation" in hits[0]["chunk"]["content"].lower()
    assert hits[0]["score"] > 0
    # Results must be ordered best-first.
    assert [hit["score"] for hit in hits] == sorted(
        (hit["score"] for hit in hits), reverse=True
    )


def test_search_on_a_missing_document_is_404(client, sme_token):
    response = client.get(
        "/api/v1/documents/99999/search",
        params={"q": "anything"},
        headers=auth_header(sme_token),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_generated_questions_cite_real_stored_chunks(client, sme_token, uploaded):
    response = client.post(
        f"/api/v1/documents/{uploaded['id']}/generate-questions",
        headers=auth_header(sme_token),
        json={"max_questions": 5},
    )
    assert response.status_code == 201

    questions = response.json()
    assert questions, "no questions were generated"

    chunk_ids = {
        chunk["id"]
        for chunk in client.get(
            f"/api/v1/documents/{uploaded['id']}/chunks", headers=auth_header(sme_token)
        ).json()
    }

    for question in questions:
        citation = question["citation"]
        assert citation["chunk_id"] in chunk_ids, "citation must point at a stored chunk"
        assert citation["quote"].strip()
        assert question["grounding_status"] == "grounded"
        assert question["options"]
        assert 0 <= question["correct_index"] < len(question["options"])
        assert question["review_status"] == "pending", "nothing is pre-approved"


def test_generation_is_idempotent(client, sme_token, uploaded):
    url = f"/api/v1/documents/{uploaded['id']}/generate-questions"
    first = client.post(url, headers=auth_header(sme_token), json={"max_questions": 5})
    second = client.post(url, headers=auth_header(sme_token), json={"max_questions": 5})

    assert first.status_code == second.status_code == 201
    assert second.json() == [], "chunks already covered must not be regenerated"


def test_learners_may_not_generate(client, seeded_learner, uploaded):
    token = login(client, "learner@sakshya.dev", seeded_learner)
    response = client.post(
        f"/api/v1/documents/{uploaded['id']}/generate-questions", headers=auth_header(token)
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# SME review
# ---------------------------------------------------------------------------


@pytest.fixture
def generated(client, sme_token, uploaded):
    response = client.post(
        f"/api/v1/documents/{uploaded['id']}/generate-questions",
        headers=auth_header(sme_token),
        json={"max_questions": 5},
    )
    return response.json()


def test_sme_can_approve_a_question(client, sme_token, generated):
    question = generated[0]
    response = client.post(
        f"/api/v1/questions/{question['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved", "note": "Checks out."},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["review_status"] == "approved"
    assert body["review_note"] == "Checks out."
    assert body["reviewed_at"] is not None


def test_sme_can_reject_a_question(client, sme_token, generated):
    response = client.post(
        f"/api/v1/questions/{generated[1]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "rejected", "note": "Ambiguous wording."},
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "rejected"


def test_editing_marks_the_question_edited(client, sme_token, generated):
    response = client.post(
        f"/api/v1/questions/{generated[0]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved", "stem": "Which statement is supported by the source?"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["edited"] is True
    assert body["stem"] == "Which statement is supported by the source?"


def test_an_edit_that_breaks_grounding_is_caught(client, sme_token, generated):
    """An expert may edit, but the grounding claim is re-verified, not assumed."""
    question = generated[0]
    options = list(question["options"])
    options[question["correct_index"]] = "A completely invented answer not in the source."

    response = client.post(
        f"/api/v1/questions/{question['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved", "options": options},
    )
    assert response.status_code == 200
    assert response.json()["grounding_status"] == "ungrounded"


def test_review_rejects_an_out_of_range_correct_index(client, sme_token, generated):
    response = client.post(
        f"/api/v1/questions/{generated[0]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved", "correct_index": 99},
    )
    assert response.status_code == 400


def test_review_rejects_an_unknown_decision(client, sme_token, generated):
    response = client.post(
        f"/api/v1/questions/{generated[0]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "maybe"},
    )
    assert response.status_code == 422


def test_only_smes_may_review(client, seeded_learner, generated):
    for email in ("learner@sakshya.dev", "admin@sakshya.dev"):
        token = login(client, email, seeded_learner)
        response = client.post(
            f"/api/v1/questions/{generated[0]['id']}/review",
            headers=auth_header(token),
            json={"decision": "approved"},
        )
        assert response.status_code == 403, email


def test_learners_only_see_approved_questions(client, sme_token, seeded_learner, generated):
    """An unreviewed question must never reach a learner."""
    learner_token = login(client, "learner@sakshya.dev", seeded_learner)

    before = client.get("/api/v1/questions", headers=auth_header(learner_token)).json()
    assert before == []

    client.post(
        f"/api/v1/questions/{generated[0]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved"},
    )

    after = client.get("/api/v1/questions", headers=auth_header(learner_token)).json()
    assert len(after) == 1
    assert after[0]["review_status"] == "approved"


def test_review_summary_counts_the_queue(client, sme_token, generated):
    client.post(
        f"/api/v1/questions/{generated[0]['id']}/review",
        headers=auth_header(sme_token),
        json={"decision": "approved"},
    )

    summary = client.get("/api/v1/questions/summary", headers=auth_header(sme_token)).json()
    assert summary["total"] == len(generated)
    assert summary["approved"] == 1
    assert summary["pending"] == len(generated) - 1
