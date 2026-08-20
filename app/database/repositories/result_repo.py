"""Result repository."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.result import Result
from app.database.repositories.base_repo import BaseRepository


class ResultRepository(BaseRepository[Result]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Result, session)

    def _with_relations(self):  # type: ignore[no-untyped-def]
        """Return a select statement pre-loaded with all relations."""
        return (
            select(Result)
            .options(
                selectinload(Result.student),
                selectinload(Result.subject),
                selectinload(Result.examination),
            )
        )

    async def get_for_student(
        self, student_id: int, limit: int = 50, offset: int = 0
    ) -> list[Result]:
        """Return paginated results for a student, newest first."""
        stmt = (
            self._with_relations()
            .where(Result.student_id == student_id)
            .order_by(Result.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_student_subject_exam(
        self,
        student_id: int,
        subject_id: int,
        examination_id: int,
    ) -> Result | None:
        """Look up the unique result for (student, subject, exam)."""
        stmt = (
            self._with_relations()
            .where(
                Result.student_id == student_id,
                Result.subject_id == subject_id,
                Result.examination_id == examination_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, result_id: int) -> Result | None:
        """Fetch a result and eagerly load its relations."""
        stmt = self._with_relations().where(Result.id == result_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        student_id: int,
        subject_id: int,
        examination_id: int,
        uploaded_by: int,
        score: Decimal | None = None,
        grade: str | None = None,
        remarks: str | None = None,
        photo_file_id: str | None = None,
        photo_unique_id: str | None = None,
    ) -> Result:
        """Create and persist a new result."""
        result = Result(
            student_id=student_id,
            subject_id=subject_id,
            examination_id=examination_id,
            uploaded_by=uploaded_by,
            score=score,
            grade=grade,
            remarks=remarks,
            photo_file_id=photo_file_id,
            photo_unique_id=photo_unique_id,
        )
        return await self.save(result)

    async def get_uploaded_by_teacher(
        self,
        uploader_user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Result]:
        """Return results uploaded by a specific teacher."""
        stmt = (
            self._with_relations()
            .where(Result.uploaded_by == uploader_user_id)
            .order_by(Result.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_student(self, student_id: int) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Result)
            .where(Result.student_id == student_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_total(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Result)
        result = await self.session.execute(stmt)
        return result.scalar_one()
