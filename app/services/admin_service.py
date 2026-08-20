"""
Admin service.

Full management capabilities: teachers, students, results, audit logs,
statistics.  All mutations are audit-logged.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.student import Student
from app.database.models.teacher import Teacher
from app.database.models.user import User, UserRole
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.teacher_repo import TeacherRepository
from app.database.repositories.user_repo import UserRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._teachers = TeacherRepository(session)
        self._students = StudentRepository(session)
        self._results = ResultRepository(session)
        self._audit = AuditRepository(session)

    # ------------------------------------------------------------------ #
    # Teacher management                                                   #
    # ------------------------------------------------------------------ #

    async def add_teacher(
        self,
        admin: User,
        telegram_user_id: int,
        employee_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Teacher:
        """
        Register a new teacher.

        Creates (or updates) their User record with TEACHER role,
        then creates the Teacher profile.

        Raises:
            ValueError: If a teacher with this employee_id already exists.
        """
        existing_teacher = await self._teachers.get_by_employee_id(employee_id)
        if existing_teacher is not None:
            raise ValueError(
                f"A teacher with employee ID '{employee_id}' already exists."
            )

        # Upsert the user record
        user, _ = await self._users.get_or_create(
            telegram_user_id=telegram_user_id,
            username=None,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.TEACHER,
        )
        # Ensure role is TEACHER
        if user.role != UserRole.TEACHER:
            user = await self._users.set_role(user, UserRole.TEACHER)

        teacher = await self._teachers.create(
            user_id=user.id,
            employee_id=employee_id,
        )

        await self._audit.log(
            action="teacher_added",
            entity_type="teacher",
            entity_id=teacher.id,
            user_id=admin.id,
            telegram_user_id=admin.telegram_user_id,
            new_value={"employee_id": employee_id, "telegram_user_id": telegram_user_id},
        )

        logger.info(
            "teacher_added",
            employee_id=employee_id,
            by_admin=admin.telegram_user_id,
        )
        return teacher

    async def deactivate_teacher(self, admin: User, teacher: Teacher) -> Teacher:
        """Deactivate a teacher account."""
        # Load the user relation explicitly to avoid lazy-load outside async context
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select as _select
        from app.database.models.teacher import Teacher as _Teacher

        stmt = (
            _select(_Teacher)
            .where(_Teacher.id == teacher.id)
            .options(selectinload(_Teacher.user))
        )
        result = await self._session.execute(stmt)
        teacher = result.scalar_one()

        teacher.is_active = False
        teacher.user.is_active = False
        await self._session.flush()

        await self._audit.log(
            action="teacher_deactivated",
            entity_type="teacher",
            entity_id=teacher.id,
            user_id=admin.id,
            telegram_user_id=admin.telegram_user_id,
        )
        return teacher

    async def list_teachers(self, limit: int = 20, offset: int = 0) -> list[Teacher]:
        return await self._teachers.list_active(limit=limit, offset=offset)

    # ------------------------------------------------------------------ #
    # Student management                                                   #
    # ------------------------------------------------------------------ #

    async def add_student(
        self,
        admin: User,
        student_id: str,
        full_name: str,
        telegram_user_id: int | None = None,
    ) -> Student:
        """
        Register a new student.

        If telegram_user_id is provided, also links the Telegram account.

        Raises:
            ValueError: If the student ID is already taken.
        """
        existing = await self._students.get_by_student_id(student_id)
        if existing is not None:
            raise ValueError(
                f"Student ID '{student_id}' is already registered."
            )

        user_id: int | None = None
        if telegram_user_id is not None:
            user, _ = await self._users.get_or_create(
                telegram_user_id=telegram_user_id,
                username=None,
                first_name=None,
                last_name=None,
                role=UserRole.STUDENT,
            )
            user_id = user.id

        student = await self._students.create(
            student_id=student_id,
            full_name=full_name,
            telegram_user_id=telegram_user_id,
            user_id=user_id,
        )

        await self._audit.log(
            action="student_added",
            entity_type="student",
            entity_id=student.id,
            user_id=admin.id,
            telegram_user_id=admin.telegram_user_id,
            new_value={"student_id": student_id, "full_name": full_name},
        )

        logger.info(
            "student_added",
            student_id=student_id,
            by_admin=admin.telegram_user_id,
        )
        return student

    async def link_student_telegram(
        self,
        admin: User,
        student: Student,
        telegram_user_id: int,
    ) -> Student:
        """Link a student's profile to their Telegram account."""
        user, _ = await self._users.get_or_create(
            telegram_user_id=telegram_user_id,
            username=None,
            first_name=None,
            last_name=None,
            role=UserRole.STUDENT,
        )
        student = await self._students.link_telegram(
            student=student,
            telegram_user_id=telegram_user_id,
            user_id=user.id,
        )

        await self._audit.log(
            action="student_telegram_linked",
            entity_type="student",
            entity_id=student.id,
            user_id=admin.id,
            telegram_user_id=admin.telegram_user_id,
            new_value={"linked_telegram_id": telegram_user_id},
        )
        return student

    async def deactivate_student(self, admin: User, student: Student) -> Student:
        """Deactivate a student account."""
        student.is_active = False
        await self._session.flush()

        await self._audit.log(
            action="student_deactivated",
            entity_type="student",
            entity_id=student.id,
            user_id=admin.id,
            telegram_user_id=admin.telegram_user_id,
        )
        return student

    async def list_students(self, limit: int = 20, offset: int = 0) -> list[Student]:
        return await self._students.list_active(limit=limit, offset=offset)

    # ------------------------------------------------------------------ #
    # Statistics                                                           #
    # ------------------------------------------------------------------ #

    async def get_statistics(self) -> dict:  # type: ignore[type-arg]
        """Return a summary of system statistics for the admin panel."""
        total_students = await self._students.count_active()
        total_teachers = await self._teachers.count_active()
        total_results = await self._results.count_total()

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_results": total_results,
        }

    # ------------------------------------------------------------------ #
    # Audit logs                                                           #
    # ------------------------------------------------------------------ #

    async def get_recent_audit_logs(self, limit: int = 20, offset: int = 0):  # type: ignore[no-untyped-def]
        """Return recent audit log entries."""
        return await self._audit.get_recent(limit=limit, offset=offset)
