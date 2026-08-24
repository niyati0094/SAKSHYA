"""Statistical roles, competencies, the role-to-competency map, and learner profiles."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Criticality(str, enum.Enum):
    """How essential a competency is to a role.

    Consumed by the gap engine (Milestone 5) to prioritise interventions.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


class StatisticalRole(Base):
    """A role in the Official Statistical System.

    Prototype sample roles only - not an official Government of India role
    catalogue.
    """

    __tablename__ = "statistical_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competency_links: Mapped[list["RoleCompetency"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Competency(Base):
    """A discrete, assessable capability."""

    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_links: Mapped[list["RoleCompetency"]] = relationship(
        back_populates="competency", cascade="all, delete-orphan"
    )


class RoleCompetency(Base):
    """Maps a competency to a role, with the level that role requires."""

    __tablename__ = "role_competencies"
    __table_args__ = (UniqueConstraint("role_id", "competency_id", name="uq_role_competency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("statistical_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id", ondelete="CASCADE"), index=True, nullable=False
    )

    #: Level this role requires (1-4). See engines.constants.LEVEL_LABELS.
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    criticality: Mapped[Criticality] = mapped_column(
        Enum(Criticality), default=Criticality.MEDIUM, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    role: Mapped[StatisticalRole] = relationship(back_populates="competency_links")
    competency: Mapped[Competency] = relationship(back_populates="role_links")


class LearnerProfile(Base):
    """Links a user to the statistical role whose competencies they are held to."""

    __tablename__ = "learner_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    statistical_role_id: Mapped[int] = mapped_column(
        ForeignKey("statistical_roles.id"), index=True, nullable=False
    )
    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    statistical_role: Mapped[StatisticalRole] = relationship()
