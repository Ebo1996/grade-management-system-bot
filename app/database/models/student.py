"""
Student model.

The telegram_user_id link is the privacy enforcement mechanism:
a student can only see results for their own linked profile.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # The unique institutional student identifier, e.g. STU-2026-00125
    student_id: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Optional link to a Telegram account.
    # Set by an administrator when registering the student.
    # NULL means the student has not yet linked their account.
    telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True, index=True
    )

    # FK to the users table (only set when the student has a linked Telegram account)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

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
    user: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="student_profile"
    )
    results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]
        "Result", back_populates="student", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<Student id={self.id} student_id={self.student_id!r} "
            f"name={self.full_name!r} active={self.is_active}>"
        )
