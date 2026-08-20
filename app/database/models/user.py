"""
User model.

Every Telegram user who interacts with the bot gets a User record.
The role field enforces access control at the service layer.
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Telegram user ID — the primary external identifier.
    # BigInteger because Telegram IDs can exceed 32-bit range.
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.STUDENT,
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
    student_profile: Mapped["Student | None"] = relationship(  # type: ignore[name-defined]
        "Student", back_populates="user", uselist=False
    )
    teacher_profile: Mapped["Teacher | None"] = relationship(  # type: ignore[name-defined]
        "Teacher", back_populates="user", uselist=False
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # type: ignore[name-defined]
        "AuditLog", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} telegram_id={self.telegram_user_id} "
            f"role={self.role} active={self.is_active}>"
        )

    @property
    def display_name(self) -> str:
        """Human-readable name for Telegram messages."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        if parts:
            return " ".join(parts)
        return self.username or f"User {self.telegram_user_id}"
