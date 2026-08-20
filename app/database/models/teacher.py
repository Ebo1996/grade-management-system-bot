"""Teacher model — extends a User with teacher-specific attributes."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # FK to users table — every teacher must have a User record
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    employee_id: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
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
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="teacher_profile"
    )
    uploaded_results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]
        "Result",
        back_populates="uploader",
        primaryjoin="Teacher.user_id == foreign(Result.uploaded_by)",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return (
            f"<Teacher id={self.id} employee_id={self.employee_id!r} "
            f"active={self.is_active}>"
        )
