"""Examination model."""
import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class ExamType(str, enum.Enum):
    MIDTERM = "MIDTERM"
    FINAL = "FINAL"
    QUIZ = "QUIZ"
    ASSIGNMENT = "ASSIGNMENT"
    PRACTICAL = "PRACTICAL"
    OTHER = "OTHER"


class Examination(Base):
    __tablename__ = "examinations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    exam_type: Mapped[ExamType] = mapped_column(
        Enum(ExamType, name="exam_type"),
        nullable=False,
        default=ExamType.OTHER,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]
        "Result", back_populates="examination", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<Examination id={self.id} name={self.name!r} "
            f"year={self.academic_year} type={self.exam_type}>"
        )
