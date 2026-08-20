"""User repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.database.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        """Fetch a user by their Telegram user ID."""
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        role: UserRole = UserRole.STUDENT,
    ) -> tuple[User, bool]:
        """
        Fetch an existing user or create a new one.

        Returns:
            (user, created) where `created` is True if a new record was made.
        """
        existing = await self.get_by_telegram_id(telegram_user_id)
        if existing:
            # Update display fields in case they changed on Telegram
            existing.username = username
            existing.first_name = first_name
            existing.last_name = last_name
            await self.session.flush()
            return existing, False

        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )
        saved = await self.save(user)
        return saved, True

    async def get_all_by_role(self, role: UserRole) -> list[User]:
        """Return all active users with a given role."""
        stmt = select(User).where(User.role == role, User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_role(self, user: User, role: UserRole) -> User:
        """Update a user's role."""
        user.role = role
        await self.session.flush()
        return user

    async def deactivate(self, user: User) -> User:
        """Soft-delete a user by deactivating them."""
        user.is_active = False
        await self.session.flush()
        return user
