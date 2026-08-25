"""Competency gaps and the personalised Learn -> Practice -> Prove pathway."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.catalog import get_catalog
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.competency import StatisticalRoleOut
from app.services import pathway_service

router = APIRouter(tags=["pathway"])


class GapOut(BaseModel):
    competency_id: int
    competency_code: str
    competency_name: str
    current_level: int
    target_level: int
    level_shortfall: int
    status: str
    confidence: float
    criticality: str
    severity: float
    severity_band: str
    evidence_limited: bool
    reasons: list[str]


class ResourceOut(BaseModel):
    external_id: str
    title: str
    description: str
    kind: str
    competency_code: str
    target_level: int
    estimated_minutes: int
    provider: str
    prerequisites: list[str]
    url: str | None
    is_prototype_data: bool


class RecommendationOut(BaseModel):
    rank: int
    competency_code: str
    competency_name: str
    stage: str
    resource: ResourceOut
    severity: float
    severity_band: str
    reasons: list[str]
    unmet_prerequisites: list[str]
    blocked: bool


class CatalogMetaOut(BaseModel):
    adapter: str
    is_live_integration: bool
    notice: str


class PathwayOut(BaseModel):
    role: StatisticalRoleOut | None
    gaps: list[GapOut]
    recommendations: list[RecommendationOut]
    catalog: CatalogMetaOut
    calculated_at: datetime
    method_note: str


METHOD_NOTE = (
    "Gap severity combines the level shortfall, the evidence deficit and the "
    "role's criticality, then scales by criticality. Recommendations are ranked "
    "by that severity and staged Learn -> Practice -> Prove from the kinds of "
    "evidence already held. Both calculations are deterministic; no language "
    "model selects or orders anything shown here."
)


def _resource_out(resource) -> ResourceOut:
    return ResourceOut(
        external_id=resource.external_id,
        title=resource.title,
        description=resource.description,
        kind=resource.kind,
        competency_code=resource.competency_code,
        target_level=resource.target_level,
        estimated_minutes=resource.estimated_minutes,
        provider=resource.provider,
        prerequisites=list(resource.prerequisites),
        url=resource.url,
        is_prototype_data=resource.is_prototype_data,
    )


@router.get("/me/pathway", response_model=PathwayOut)
def my_pathway(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PathwayOut:
    """The learner's gaps and what to do about them, recomputed from evidence."""
    data = pathway_service.build_pathway(db, current_user.id, limit=limit)

    return PathwayOut(
        role=(
            StatisticalRoleOut.model_validate(data["role"]) if data["role"] else None
        ),
        gaps=[GapOut(**gap.__dict__) for gap in data["gaps"]],
        recommendations=[
            RecommendationOut(
                rank=item.rank,
                competency_code=item.competency_code,
                competency_name=item.competency_name,
                stage=item.stage,
                resource=_resource_out(item.resource),
                severity=item.severity,
                severity_band=item.severity_band,
                reasons=item.reasons,
                unmet_prerequisites=item.unmet_prerequisites,
                blocked=item.blocked,
            )
            for item in data["recommendations"]
        ],
        catalog=CatalogMetaOut(**data["catalog"]),
        calculated_at=data["calculated_at"],
        method_note=METHOD_NOTE,
    )


@router.get("/catalog", response_model=list[ResourceOut])
def list_catalog(_: User = Depends(get_current_user)) -> list[ResourceOut]:
    """The full prototype learning catalogue behind the adapter boundary."""
    return [_resource_out(item) for item in get_catalog().all_resources()]
