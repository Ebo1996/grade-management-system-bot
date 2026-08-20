"""Student repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.student import Student
from app.database.repositories.base_repo import BaseRepository


class StudentRepository(BaseRepository[Student]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Student, session)

    async def get_by_student_id(self, student_id: str) -> Student | None:
        """Fetch a student by their institutional student ID string."""
        stmt = select(Student).where(Student.student_id == student_id.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_user_id: int) -> Student | None:
        """Fetch the student whose account is linked to a Telegram user ID."""
        stmt = select(Student).where(Student.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Student | None:
        """Fetch a student linked to a users.id FK."""
        stmt = select(Student).where(Student.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        student_id: str,
        full_name: str,
        telegram_user_id: int | None = None,
        user_id: int | None = None,
    ) -> Student:
        """Create and persist a new student record."""
        student = Student(
            student_id=student_id.upper(),
            full_name=full_name,
            telegram_user_id=telegram_user_id,
            user_id=user_id,
            is_active=True,
        )
        return await self.save(student)

    async def link_telegram(
        self, student: Student, telegram_user_id: int, user_id: int
    ) -> Student:
        """Link a Telegram account to a student profile."""
        student.telegram_user_id = telegram_user_id
        student.user_id = user_id
        await self.session.flush()
        return student

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Student]:
        """Return paginated active students."""
        stmt = (
            select(Student)
            .where(Student.is_active.is_(True))
            .order_by(Student.student_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_name(self, query: str, limit: int = 20) -> list[Student]:
        """Full name search (case-insensitive)."""
        stmt = (
            select(Student)
            .where(Student.full_name.ilike(f"%{query}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        return await self.count(is_active=True)
