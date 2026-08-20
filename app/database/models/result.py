"""
Result model.

Central table of the system.  Each row represents one student's
result for one subject in one examination.

The combination (student_id, subject_id, examination_id) must be
unique to prevent duplicate entries.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Result(Base):
    __tablename__ = "results"

    # Uniqueness constraint: one result per (student, subject, exam)
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "examination_id",
            name="uq_result_student_subject_exam",
        ),
        Index("ix_result_student_id", "student_id"),
        Index("ix_result_subject_id", "subject_id"),
        Index("ix_result_examination_id", "examination_id"),
        Index("ix_result_uploaded_by", "uploaded_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    examination_id: Mapped[int] = mapped_column(
        ForeignKey("examinations.id", ondelete="RESTRICT"), nullable=False
    )

    # Score stored as numeric(5,2) — allows values from 0.00 to 100.00
    score: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True
    )
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Telegram photo storage
    # We store the file_id returned by Telegram; this is sufficient to
    # re-send the photo without storing the raw bytes.
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_unique_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    # The user (teacher) who uploaded this result
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

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
    student: Mapped["Student"] = relationship(  # type: ignore[name-defined]
        "Student", back_populates="results"
    )
    subject: Mapped["Subject"] = relationship(  # type: ignore[name-defined]
        "Subject", back_populates="results"
    )
    examination: Mapped["Examination"] = relationship(  # type: ignore[name-defined]
        "Examination", back_populates="results"
    )
    uploader: Mapped["Teacher"] = relationship(  # type: ignore[name-defined]
        "Teacher",
        back_populates="uploaded_results",
        primaryjoin="Result.uploaded_by == Teacher.user_id",
        foreign_keys="[Result.uploaded_by]",
    )

    def __repr__(self) -> str:
        return (
            f"<Result id={self.id} student_id={self.student_id} "
            f"subject_id={self.subject_id} exam_id={self.examination_id} "
            f"score={self.score} grade={self.grade!r}>"
        )
