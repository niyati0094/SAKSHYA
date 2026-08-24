"""Role-based access control across the three dashboard roots."""

import pytest

from tests.conftest import auth_header, login

DASHBOARDS = {
    "learner": "/api/v1/dashboard/learner",
    "sme": "/api/v1/dashboard/sme",
    "admin": "/api/v1/dashboard/admin",
}

ACCOUNTS = {
    "learner": "learner@sakshya.dev",
    "sme": "sme@sakshya.dev",
    "admin": "admin@sakshya.dev",
}


@pytest.mark.parametrize("role", list(ACCOUNTS))
def test_each_role_reaches_its_own_dashboard(client, demo_password, role):
    token = login(client, ACCOUNTS[role], demo_password)
    response = client.get(DASHBOARDS[role], headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == role
    assert body["capabilities"], "every role must expose its capability list"


@pytest.mark.parametrize(
    "role,forbidden_role",
    [
        ("learner", "sme"),
        ("learner", "admin"),
        ("sme", "learner"),
        ("sme", "admin"),
        ("admin", "learner"),
        ("admin", "sme"),
    ],
)
def test_roles_are_denied_other_dashboards(client, demo_password, role, forbidden_role):
    """The core RBAC guarantee: no role may cross into another's dashboard."""
    token = login(client, ACCOUNTS[role], demo_password)
    response = client.get(DASHBOARDS[forbidden_role], headers=auth_header(token))
    assert response.status_code == 403


@pytest.mark.parametrize("path", list(DASHBOARDS.values()))
def test_dashboards_reject_anonymous_access(client, path):
    assert client.get(path).status_code == 401


def test_deactivated_user_is_locked_out(client, db_session, demo_password):
    """A token stays valid but authorisation is re-checked against the database."""
    from sqlalchemy import select

    from app.models.user import User

    token = login(client, ACCOUNTS["learner"], demo_password)
    assert client.get(DASHBOARDS["learner"], headers=auth_header(token)).status_code == 200

    user = db_session.scalar(select(User).where(User.email == ACCOUNTS["learner"]))
    user.is_active = False
    db_session.commit()

    response = client.get(DASHBOARDS["learner"], headers=auth_header(token))
    assert response.status_code == 403


def test_role_change_takes_effect_without_reissuing_token(client, db_session, demo_password):
    """Authorisation reads the live role, not the (now stale) JWT claim."""
    from sqlalchemy import select

    from app.models.user import User, UserRole

    token = login(client, ACCOUNTS["learner"], demo_password)
    assert client.get(DASHBOARDS["admin"], headers=auth_header(token)).status_code == 403

    user = db_session.scalar(select(User).where(User.email == ACCOUNTS["learner"]))
    user.role = UserRole.ADMIN
    db_session.commit()

    assert client.get(DASHBOARDS["admin"], headers=auth_header(token)).status_code == 200
