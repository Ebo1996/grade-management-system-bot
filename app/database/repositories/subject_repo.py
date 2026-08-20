"""Subject repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.subject import Subject
from app.database.repositories.base_repo import BaseRepository


class SubjectRepository(BaseRepository[Subject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subject, session)

    async def get_by_name(self, name: str) -> Subject | None:
        stmt = select(Subject).where(Subject.name.ilike(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Subject | None:
        stmt = select(Subject).where(Subject.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, code: str | None = None) -> tuple[Subject, bool]:
        """
        Return an existing subject or create a new one.

        Matches by exact name (case-insensitive).
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False
        subject = Subject(name=name.strip(), code=code.upper() if code else None, is_active=True)
        saved = await self.save(subject)
        return saved, True

    async def list_active(self) -> list[Subject]:
        stmt = (
            select(Subject)
            .where(Subject.is_active.is_(True))
            .order_by(Subject.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
