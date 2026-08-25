"""Declarative base and model registry.

Importing this module imports every model, so ``Base.metadata`` is complete
for table creation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    """Import all model modules so they register against ``Base.metadata``."""
    # Imported for their side effect: each module registers its tables against
    # Base.metadata. The unused-import warning is expected here, not an
    # oversight, so it is suppressed per name.
    from app.models import (  # noqa: F401
        competency,
        document,
        evidence,
        question,
        simulation,
        user,
    )
