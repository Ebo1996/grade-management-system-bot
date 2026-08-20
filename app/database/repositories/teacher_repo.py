"""Teacher repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.teacher import Teacher
from app.database.models.user import User
from app.database.repositories.base_repo import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Teacher, session)

    async def get_by_user_id(self, user_id: int) -> Teacher | None:
        """Fetch a teacher linked to a users.id FK."""
        stmt = (
            select(Teacher)
            .where(Teacher.user_id == user_id)
            .options(selectinload(Teacher.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_user_id: int) -> Teacher | None:
        """Fetch the Teacher record for a given Telegram user ID (via User join)."""
        stmt = (
            select(Teacher)
            .join(Teacher.user)
            .where(User.telegram_user_id == telegram_user_id)
            .options(selectinload(Teacher.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: str) -> Teacher | None:
        """Fetch a teacher by their institutional employee ID."""
        stmt = select(Teacher).where(Teacher.employee_id == employee_id.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user_id: int, employee_id: str) -> Teacher:
        """Create and persist a new teacher record."""
        teacher = Teacher(
            user_id=user_id,
            employee_id=employee_id.upper(),
            is_active=True,
        )
        return await self.save(teacher)

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Teacher]:
        """Return paginated active teachers with their user data loaded."""
        stmt = (
            select(Teacher)
            .where(Teacher.is_active.is_(True))
            .options(selectinload(Teacher.user))
            .order_by(Teacher.employee_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        return await self.count(is_active=True)
