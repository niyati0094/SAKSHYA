"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness + dependency check.

    Actually round-trips a query to the database rather than reporting a
    hard-coded 'ok', so a broken database surfaces here.
    """
    settings = get_settings()

    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as exc:  # pragma: no cover - exercised only on real failure
        database_status = f"error: {type(exc).__name__}"

    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": database_status,
    }
