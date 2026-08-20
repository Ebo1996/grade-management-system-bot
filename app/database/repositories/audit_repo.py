"""Audit log repository."""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.audit_log import AuditLog
from app.database.repositories.base_repo import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        user_id: int | None = None,
        telegram_user_id: int | None = None,
        old_value: Any = None,
        new_value: Any = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        old_value and new_value are serialised to JSON strings.
        Caller should NOT include sensitive fields (scores are OK;
        do not include tokens, passwords, etc.).
        """

        def _serialise(obj: Any) -> str | None:
            if obj is None:
                return None
            if isinstance(obj, str):
                return obj
            try:
                return json.dumps(obj, default=str)
            except (TypeError, ValueError):
                return str(obj)

        entry = AuditLog(
            user_id=user_id,
            telegram_user_id=telegram_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=_serialise(old_value),
            new_value=_serialise(new_value),
            ip_address=ip_address,
        )
        return await self.save(entry)

    async def get_for_entity(
        self, entity_type: str, entity_id: int, limit: int = 50
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 50, offset: int = 0) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
