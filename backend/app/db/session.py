"""Database engine, session factory, and the FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs check_same_thread disabled because FastAPI serves requests from
# a threadpool. The flag is meaningless (and invalid) for PostgreSQL.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create the schema.

    The prototype uses SQLAlchemy metadata creation plus an idempotent seed
    rather than incremental migrations, because the demo database is rebuilt
    from seed data. Alembic is the documented path for production.
    """
    from app.db.base import Base, import_models

    import_models()
    Base.metadata.create_all(bind=engine)
