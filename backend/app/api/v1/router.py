"""Aggregate v1 API router."""

from fastapi import APIRouter

from app.api.v1 import auth, competency, dashboard, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(competency.router)
