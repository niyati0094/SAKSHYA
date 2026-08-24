"""Test fixtures: an isolated in-memory database per test.

The environment is configured *before* importing the application so the app's
lifespan never touches the real development database.
"""

import os
import tempfile

os.environ.setdefault("SAKSHYA_ENVIRONMENT", "test")
os.environ["SAKSHYA_DATABASE_URL"] = (
    "sqlite:///" + os.path.join(tempfile.gettempdir(), "sakshya_test_lifespan.db")
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, import_models  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


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


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
