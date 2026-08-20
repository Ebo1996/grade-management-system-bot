"""
Authentication and authorisation service.

Centralises all role/identity checks so that handlers never
implement access-control logic themselves.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models.user import User, UserRole
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.teacher_repo import TeacherRepository
from app.database.repositories.student_repo import StudentRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """
    Handles user registration / lookup and role verification.

    Every call into the bot goes through get_or_create_user() first
    so that a User record always exists before any other logic runs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._teachers = TeacherRepository(session)
        self._students = StudentRepository(session)
        self._settings = get_settings()

    async def get_or_create_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        """
        Ensure a User row exists for the given Telegram account.

        If the Telegram ID is in the ADMIN_TELEGRAM_IDS list and the
        user's current role is STUDENT, it is promoted to ADMIN.
        """
        admin_ids = self._settings.get_admin_telegram_ids()
        initial_role = (
            UserRole.ADMIN if telegram_user_id in admin_ids else UserRole.STUDENT
        )

        user, created = await self._users.get_or_create(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=initial_role,
        )

        # Promote to admin if ID appears in config and wasn't set yet
        if not created and telegram_user_id in admin_ids and user.role == UserRole.STUDENT:
            user = await self._users.set_role(user, UserRole.ADMIN)
            logger.info(
                "user_promoted_to_admin",
                telegram_user_id=telegram_user_id,
            )

        return user

    async def is_admin(self, user: User) -> bool:
        """Return True if the user has an active ADMIN role."""
        return user.role == UserRole.ADMIN and user.is_active

    async def is_teacher(self, user: User) -> bool:
        """
        Return True if the user has an active TEACHER role AND an active
        teacher profile record.
        """
        if user.role != UserRole.TEACHER or not user.is_active:
            return False
        teacher = await self._teachers.get_by_user_id(user.id)
        return teacher is not None and teacher.is_active

    async def is_student(self, user: User) -> bool:
        """Return True if the user has the STUDENT role and is active."""
        return user.role == UserRole.STUDENT and user.is_active

    async def get_teacher_profile(self, user: User):  # type: ignore[no-untyped-def]
        """Return the Teacher record for a teacher user, or None."""
        return await self._teachers.get_by_user_id(user.id)

    async def get_student_profile(self, user: User):  # type: ignore[no-untyped-def]
        """Return the Student record linked to this user, or None."""
        return await self._students.get_by_user_id(user.id)
