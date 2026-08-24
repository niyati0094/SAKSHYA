"""Authentication: login, token issuance, and identity."""

import pytest

from app.core.security import hash_password, verify_password
from tests.conftest import auth_header, login


def test_login_succeeds_with_demo_credentials(client, demo_password):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "learner@sakshya.dev", "password": demo_password},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["role"] == "learner"
    assert body["user"]["is_prototype_data"] is True


def test_login_rejects_wrong_password(client, demo_password):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "learner@sakshya.dev", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_login_does_not_reveal_whether_account_exists(client, demo_password):
    """Unknown email and wrong password must be indistinguishable."""
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@sakshya.dev", "password": "whatever"},
    )
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "learner@sakshya.dev", "password": "whatever"},
    )
    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["detail"] == wrong_password.json()["detail"]


def test_me_returns_authenticated_identity(client, demo_password):
    token = login(client, "sme@sakshya.dev", demo_password)
    response = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["email"] == "sme@sakshya.dev"
    assert response.json()["role"] == "sme"


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers=auth_header("not-a-real-jwt"))
    assert response.status_code == 401


def test_password_hashing_roundtrip():
    hashed = hash_password("Sakshya@2026")
    assert hashed != "Sakshya@2026"
    assert verify_password("Sakshya@2026", hashed)
    assert not verify_password("wrong", hashed)


def test_password_hashing_rejects_oversized_input():
    """bcrypt truncates past 72 bytes; we must refuse rather than silently accept."""
    with pytest.raises(ValueError):
        hash_password("a" * 73)


def test_verify_password_survives_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_seed_is_idempotent(db_session):
    from app.db.seed import seed_users

    created_first, skipped_first = seed_users(db_session)
    created_second, skipped_second = seed_users(db_session)

    assert (created_first, skipped_first) == (3, 0)
    assert (created_second, skipped_second) == (0, 3)
