"""Idempotent demo seeding.

Run with:  python -m app.db.seed

Credentials defined here are DEVELOPMENT-ONLY fixtures for the hackathon
prototype. They are deliberately visible in source so the demo can be run by
anyone who clones the repository, and must never be used in a real deployment.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal, create_all
from app.models.user import User, UserRole


@dataclass(frozen=True)
class DemoUser:
    email: str
    password: str
    full_name: str
    role: UserRole
    designation: str
    organization: str


# Shared development password across demo accounts keeps the 2-minute demo
# fast. Development-only.
DEMO_PASSWORD = "Sakshya@2026"

DEMO_USERS: list[DemoUser] = [
    DemoUser(
        email="learner@sakshya.dev",
        password=DEMO_PASSWORD,
        full_name="Ananya Rao",
        role=UserRole.LEARNER,
        designation="Junior Statistical Officer (sample role)",
        organization="Sample State Directorate of Economics & Statistics",
    ),
    DemoUser(
        email="sme@sakshya.dev",
        password=DEMO_PASSWORD,
        full_name="Dr. Vikram Iyer",
        role=UserRole.SME,
        designation="Subject Matter Expert - Survey Methodology (sample role)",
        organization="Sample National Statistical Training Institute",
    ),
    DemoUser(
        email="admin@sakshya.dev",
        password=DEMO_PASSWORD,
        full_name="Meera Krishnan",
        role=UserRole.ADMIN,
        designation="Capacity Building Administrator (sample role)",
        organization="Sample National Statistical Office",
    ),
]


def seed_users(db: Session) -> tuple[int, int]:
    """Create demo users that do not already exist.

    Returns (created, skipped). Existing users are never overwritten, so
    re-running the seed is safe.
    """
    created = 0
    skipped = 0

    for demo in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == demo.email))
        if existing is not None:
            skipped += 1
            continue

        db.add(
            User(
                email=demo.email,
                full_name=demo.full_name,
                hashed_password=hash_password(demo.password),
                role=demo.role,
                designation=demo.designation,
                organization=demo.organization,
                is_active=True,
                is_prototype_data=True,
            )
        )
        created += 1

    db.commit()
    return created, skipped


def run() -> None:
    create_all()
    with SessionLocal() as db:
        created, skipped = seed_users(db)

        # Competency framework + demo learner evidence (Milestone 2).
        from sqlalchemy import select

        from app.db.seed_competency import seed_learner_evidence

        learner = db.scalar(select(User).where(User.email == "learner@sakshya.dev"))
        evidence_created = seed_learner_evidence(db, learner) if learner else 0

    print(f"[seed] users created={created} skipped(existing)={skipped}")
    print(f"[seed] evidence records created={evidence_created}")
    print("[seed] development-only demo credentials:")
    for demo in DEMO_USERS:
        print(f"        {demo.role.value:<8} {demo.email}  /  {demo.password}")


if __name__ == "__main__":
    run()
