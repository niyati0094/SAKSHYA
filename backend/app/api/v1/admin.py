"""Admin analytics and evidence export."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services import analytics_service, competency_service

router = APIRouter(tags=["admin"])

require_staff = require_roles(UserRole.ADMIN, UserRole.SME)


class RoleDistributionOut(BaseModel):
    role_name: str
    learner_count: int


class TrainingNeedOut(BaseModel):
    competency_code: str
    competency_name: str
    criticality: str
    target_level: int
    learners_with_gap: int
    learners_unproven: int
    average_severity: float
    share_of_learners: float


class OrganisationOverviewOut(BaseModel):
    learner_count: int
    learners_with_profile: int
    total_gaps: int
    urgent_gaps: int
    role_distribution: list[RoleDistributionOut]
    training_needs: list[TrainingNeedOut]
    calculated_at: datetime
    notice: str


@router.get("/admin/overview", response_model=OrganisationOverviewOut)
def organisation_overview(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrganisationOverviewOut:
    """Aggregate competency gaps and training needs across the cohort."""
    return OrganisationOverviewOut(**analytics_service.organisation_overview(db))


@router.get("/me/evidence/export")
def export_my_evidence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export the caller's evidence ledger as CSV.

    The export carries the prototype flag on every row, so an exported file
    cannot be mistaken for official record once it leaves the application.
    """
    evidence = competency_service.get_evidence(db, current_user.id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "evidence_id",
            "competency_code",
            "competency_name",
            "evidence_type",
            "activity_title",
            "source",
            "raw_score",
            "max_score",
            "normalised_score",
            "review_status",
            "reviewed_by",
            "observed_at",
            "is_prototype_data",
        ]
    )
    for item in evidence:
        writer.writerow(
            [
                item.id,
                item.competency.code,
                item.competency.name,
                item.evidence_type.value,
                item.activity_title,
                item.source or "",
                item.raw_score,
                item.max_score,
                round(item.normalized_score, 4),
                item.review_status.value,
                item.reviewed_by or "",
                item.observed_at.isoformat(),
                item.is_prototype_data,
            ]
        )

    buffer.seek(0)
    filename = f"sakshya-evidence-{current_user.id}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
