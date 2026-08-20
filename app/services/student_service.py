"""
Student service.

Handles student-facing result retrieval and profile management.
Privacy enforcement is the core responsibility of this service:
a student must only ever see their own results.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models.result import Result
from app.database.models.student import Student
from app.database.models.user import User
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.result_repo import ResultRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StudentAccessError(Exception):
    """Raised when a student tries to access another student's data."""


class StudentNotFoundError(Exception):
    """Raised when the requested student record does not exist."""


class StudentInactiveError(Exception):
    """Raised when the student account is deactivated."""


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._students = StudentRepository(session)
        self._results = ResultRepository(session)
        self._settings = get_settings()

    async def get_student_for_user(self, user: User) -> Student:
        """
        Return the student profile linked to the authenticated Telegram user.

        Raises:
            StudentNotFoundError: If no student is linked to this account.
            StudentInactiveError: If the student account is deactivated.
        """
        student = await self._students.get_by_user_id(user.id)
        if student is None:
            raise StudentNotFoundError(
                "No student profile is linked to your Telegram account. "
                "Please contact your school administrator."
            )
        if not student.is_active:
            raise StudentInactiveError(
                "Your student account has been deactivated. "
                "Please contact the administrator."
            )
        return student

    async def lookup_student_secure(
        self, requesting_user: User, student_id_str: str
    ) -> Student:
        """
        Look up a student by their student ID string.

        In "linked" mode (default):
            The requesting_user's linked student profile must match
            the requested student_id. Students cannot look up others.

        In "open" mode:
            Any authenticated user can look up a student by ID.
            This is less secure and should only be used when explicitly
            configured (e.g., for in-person kiosk systems).

        Raises:
            StudentNotFoundError, StudentInactiveError, StudentAccessError
        """
        target = await self._students.get_by_student_id(student_id_str)
        if target is None:
            raise StudentNotFoundError(
                f"Student ID '{student_id_str}' was not found in the system."
            )
        if not target.is_active:
            raise StudentInactiveError(
                "This student account is deactivated."
            )

        if self._settings.student_lookup_mode == "linked":
            # Privacy check: the requester must own this profile
            linked = await self._students.get_by_user_id(requesting_user.id)
            if linked is None or linked.id != target.id:
                logger.warning(
                    "student_unauthorized_access_attempt",
                    requesting_telegram_id=requesting_user.telegram_user_id,
                    requested_student_id=student_id_str,
                )
                raise StudentAccessError(
                    "You are not authorised to view results for that student ID.\n"
                    "You can only view your own results."
                )

        return target

    async def get_results(
        self, student: Student, limit: int = 20, offset: int = 0
    ) -> list[Result]:
        """Return paginated results for a student."""
        return await self._results.get_for_student(
            student_id=student.id, limit=limit, offset=offset
        )

    async def get_result_by_id(self, student: Student, result_id: int) -> Result:
        """
        Return a specific result, verifying it belongs to this student.

        Raises:
            StudentAccessError: if the result belongs to another student.
            StudentNotFoundError: if the result does not exist.
        """
        result = await self._results.get_by_id_with_relations(result_id)
        if result is None:
            raise StudentNotFoundError("Result not found.")
        if result.student_id != student.id:
            logger.warning(
                "student_cross_result_access_attempt",
                student_id=student.id,
                requested_result_id=result_id,
                result_owner_id=result.student_id,
            )
            raise StudentAccessError("You are not authorised to view this result.")
        return result

    async def count_results(self, student: Student) -> int:
        """Return the total number of results for a student."""
        return await self._results.count_for_student(student.id)
