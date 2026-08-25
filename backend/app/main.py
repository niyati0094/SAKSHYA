"""SAKSHYA FastAPI application entrypoint.

In development the API runs alone and Vite serves the frontend on its own
port. In a deployment this same process also serves the built frontend, so
there is one service and one origin: no CORS, no reverse proxy, and no
separate API base URL for the client to get wrong.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal, create_all

logger = logging.getLogger(__name__)
settings = get_settings()

API_V1_PREFIX = "/api/v1"

#: Built frontend, produced by `npm run build`. Absent during local API-only
#: development, which is fine - Vite serves it instead.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _seed_if_empty() -> None:
    """Seed demo data when the database has no users yet.

    Deployment targets frequently have ephemeral disks, so a restart would
    otherwise leave the demo with an empty database and nothing to show. This
    only ever runs against an empty database - it never rewrites or resets
    existing data, so a real deployment with real users is untouched.
    """
    from sqlalchemy import select

    from app.models.user import User

    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return

    logger.info("Database is empty; seeding prototype demo data.")
    from app.db.seed import run as run_seed

    run_seed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the schema exists before serving traffic.
    create_all()

    if settings.auto_seed:
        try:
            _seed_if_empty()
        except Exception:  # pragma: no cover - seeding must never block boot
            logger.exception("Demo seeding failed; continuing without it.")

    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/api", tags=["meta"])
def api_root() -> dict:
    """Service metadata. Kept off `/` so the frontend can own the root path."""
    return {
        "name": settings.app_name,
        "description": settings.app_description,
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
        "frontend_bundled": FRONTEND_DIST.is_dir(),
    }


def _mount_frontend() -> None:
    """Serve the built single-page app, if it has been built.

    Registered last so it can never shadow an API route. Unknown paths fall
    back to index.html because the router is client-side - a deep link such as
    /learner/evidence must reach the app rather than 404.
    """
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        logger.info("No built frontend at %s; serving API only.", FRONTEND_DIST)

        @app.get("/", tags=["meta"], include_in_schema=False)
        def root() -> dict:
            return api_root()

        return

    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    def index_page() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        # An unknown API path must stay a JSON 404. Without this the catch-all
        # would answer it with the app shell, turning a broken endpoint into a
        # silent 200 that is far harder to diagnose.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        # A real file (favicon, manifest) is served as itself; anything else is
        # a client-side route and gets the app shell.
        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and FRONTEND_DIST.resolve() in candidate.parents
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(index)


_mount_frontend()
