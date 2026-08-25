"""Role-scoped dashboard roots.

Establishes the RBAC boundary and returns each role's identity and capability
list. Capabilities are the authoritative record of what the server will
actually authorise, so the UI cannot drift from real authorisation rules.

``pending_modules`` lists functionality not yet wired. Every module that was
listed here during earlier milestones now exists, so the lists are empty - the
field is kept because reporting "nothing pending" honestly is better than
removing the mechanism that made incompleteness visible.
"""

from fastapi import APIRouter, Depends

from app.core.deps import require_admin, require_learner, require_sme
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Capabilities are the authoritative list of what each role may do. The
# frontend renders navigation from this, so the UI cannot drift from the
# server's actual authorisation rules.
ROLE_CAPABILITIES: dict[str, list[str]] = {
    "learner": [
        "view_own_competency_profile",
        "view_own_evidence_ledger",
        "take_assessments",
        "run_simulations",
        "view_recommendations",
    ],
    "sme": [
        "view_review_queue",
        "approve_generated_questions",
        "edit_generated_questions",
        "reject_generated_questions",
        "view_competency_mapping",
    ],
    "admin": [
        "view_aggregate_competency_gaps",
        "view_role_distribution",
        "view_training_needs",
        "manage_learning_catalog",
    ],
}


def _payload(user: User, pending: list[str]) -> dict:
    return {
        "user": UserOut.model_validate(user).model_dump(),
        "capabilities": ROLE_CAPABILITIES[user.role.value],
        "pending_modules": pending,
        "prototype_notice": (
            "Prototype environment. All seeded content is illustrative sample "
            "data and is not official Government of India competency data."
        ),
    }


@router.get("/learner")
def learner_dashboard(current_user: User = Depends(require_learner)) -> dict:
    return _payload(current_user, pending=[])


@router.get("/sme")
def sme_dashboard(current_user: User = Depends(require_sme)) -> dict:
    return _payload(current_user, pending=[])


@router.get("/admin")
def admin_dashboard(current_user: User = Depends(require_admin)) -> dict:
    return _payload(current_user, pending=[])
