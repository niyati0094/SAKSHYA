"""Recorded simulation attempts."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SimulationAttempt(Base):
    __tablename__ = "simulation_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scenario_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    #: JSON: {decision_key: option_key}
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(32), nullable=False)

    #: Narrative debrief. Generated after scoring and never fed back into it.
    debrief: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: The evidence row this attempt produced, linking performance to competency.
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_prototype_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
