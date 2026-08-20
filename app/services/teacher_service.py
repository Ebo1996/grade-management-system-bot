"""
Teacher service.

Handles teacher-specific operations: viewing their uploads,
searching students, and managing their own results.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.result import Result
from app.database.models.student import Student
from app.database.models.teacher import Teacher
from app.database.models.user import User
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.teacher_repo import TeacherRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TeacherNotFoundError(Exception):
    """Raised when a teacher profile is not found."""


class TeacherService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._teachers = TeacherRepository(session)
        self._students = StudentRepository(session)
        self._results = ResultRepository(session)

    async def get_teacher_profile(self, user: User) -> Teacher:
        """
        Return the teacher's profile.

        Raises:
            TeacherNotFoundError: If no teacher profile is linked.
        """
        teacher = await self._teachers.get_by_user_id(user.id)
        if teacher is None or not teacher.is_active:
            raise TeacherNotFoundError(
                "Your teacher account is not active. Contact an administrator."
            )
        return teacher

    async def get_uploaded_results(
        self, teacher: Teacher, limit: int = 20, offset: int = 0
    ) -> list[Result]:
        """Return results that this teacher uploaded."""
        return await self._results.get_uploaded_by_teacher(
            uploader_user_id=teacher.user_id,
            limit=limit,
            offset=offset,
        )

    async def search_student(self, query: str) -> list[Student]:
        """
        Search students by name or student ID.

        Returns matching active students (up to 10).
        """
        query = query.strip()
        if not query:
            return []

        # Try exact student ID match first
        if query.upper().startswith("STU-"):
            student = await self._students.get_by_student_id(query)
            return [student] if student else []

        # Fall back to name search
        return await self._students.search_by_name(query, limit=10)

    async def can_modify_result(self, teacher: Teacher, result: Result) -> bool:
        """
        Return True if this teacher is allowed to modify the given result.

        Currently, teachers can only modify results they uploaded themselves.
        Admins use admin_service for unrestricted access.
        """
        return result.uploaded_by == teacher.user_id
