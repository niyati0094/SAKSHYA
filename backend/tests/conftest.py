"""Test fixtures: an isolated in-memory database per test.

The environment is configured *before* importing the application so the app's
lifespan never touches the real development database.
"""

import os
import tempfile

os.environ.setdefault("SAKSHYA_ENVIRONMENT", "test")
# Tests seed their own isolated fixtures; startup seeding would be both slow
# and a source of state leaking between tests.
os.environ["SAKSHYA_AUTO_SEED"] = "false"
os.environ["SAKSHYA_DATABASE_URL"] = (
    "sqlite:///" + os.path.join(tempfile.gettempdir(), "sakshya_test_lifespan.db")
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, import_models
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db_session():
    # StaticPool keeps a single connection alive so the in-memory database
    # survives for the whole test, including across FastAPI's threadpool.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import_models()
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def demo_password(db_session: Session) -> str:
    """Seed the three demo users into the isolated test database."""
    from app.db.seed import DEMO_PASSWORD, seed_users

    seed_users(db_session)
    return DEMO_PASSWORD


@pytest.fixture
def seeded_learner(db_session: Session, demo_password: str) -> str:
    """Seed users plus the competency framework and demo evidence."""
    from sqlalchemy import select

    from app.db.seed_competency import seed_learner_evidence
    from app.models.user import User

    learner = db_session.scalar(select(User).where(User.email == "learner@sakshya.dev"))
    seed_learner_evidence(db_session, learner)
    return demo_password


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
