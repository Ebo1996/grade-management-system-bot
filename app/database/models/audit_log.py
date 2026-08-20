"""
AuditLog model.

Records every significant write operation (create / update / delete)
for security review and dispute resolution.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # The user who performed the action (NULL for system actions)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # For Telegram-only operations, also record the raw Telegram user ID
    # in case the user row is later deleted.
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # The type of entity affected, e.g. "result", "student", "teacher"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # JSON snapshots of the record before/after the change.
    # Stored as text to avoid requiring a JSON column on all databases.
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Telegram does not expose client IP addresses, so this is NULL
    # for bot interactions but available if a REST API is added later.
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"entity={self.entity_type}:{self.entity_id} "
            f"user_id={self.user_id}>"
        )
