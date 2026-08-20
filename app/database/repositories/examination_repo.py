"""Examination repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.examination import Examination, ExamType
from app.database.repositories.base_repo import BaseRepository


class ExaminationRepository(BaseRepository[Examination]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Examination, session)

    async def get_by_name(self, name: str) -> Examination | None:
        stmt = select(Examination).where(Examination.name.ilike(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        academic_year: str | None = None,
        exam_type: ExamType = ExamType.OTHER,
    ) -> tuple[Examination, bool]:
        """
        Return an existing examination by exact name or create one.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False
        exam = Examination(
            name=name.strip(),
            academic_year=academic_year,
            exam_type=exam_type,
            is_active=True,
        )
        saved = await self.save(exam)
        return saved, True

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Examination]:
        stmt = (
            select(Examination)
            .where(Examination.is_active.is_(True))
            .order_by(Examination.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
