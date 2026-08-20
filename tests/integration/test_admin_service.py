"""Integration tests for the AdminService."""
import pytest
import pytest_asyncio

from app.database.models.user import UserRole
from app.database.repositories.teacher_repo import TeacherRepository
from app.database.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService


@pytest_asyncio.fixture
async def admin_user(db_session):
    repo = UserRepository(db_session)
    user, _ = await repo.get_or_create(
        telegram_user_id=800001,
        username="admin1",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
    )
    await db_session.commit()
    return user


class TestAddTeacher:
    async def test_adds_teacher_successfully(self, db_session, admin_user):
        svc = AdminService(db_session)
        teacher = await svc.add_teacher(
            admin=admin_user,
            telegram_user_id=700001,
            employee_id="EMP-001",
            first_name="John",
            last_name="Teacher",
        )
        await db_session.commit()

        assert teacher.id is not None
        assert teacher.employee_id == "EMP-001"
        assert teacher.is_active is True

    async def test_raises_on_duplicate_employee_id(self, db_session, admin_user):
        svc = AdminService(db_session)
        await svc.add_teacher(
            admin=admin_user,
            telegram_user_id=700002,
            employee_id="EMP-002",
        )
        await db_session.commit()

        with pytest.raises(ValueError, match="already exists"):
            await svc.add_teacher(
                admin=admin_user,
                telegram_user_id=700003,
                employee_id="EMP-002",
            )


class TestAddStudent:
    async def test_adds_student_successfully(self, db_session, admin_user):
        svc = AdminService(db_session)
        student = await svc.add_student(
            admin=admin_user,
            student_id="STU-2026-00200",
            full_name="Jane Doe",
        )
        await db_session.commit()

        assert student.id is not None
        assert student.student_id == "STU-2026-00200"

    async def test_raises_on_duplicate_student_id(self, db_session, admin_user):
        svc = AdminService(db_session)
        await svc.add_student(
            admin=admin_user,
            student_id="STU-2026-00201",
            full_name="Student One",
        )
        await db_session.commit()

        with pytest.raises(ValueError, match="already registered"):
            await svc.add_student(
                admin=admin_user,
                student_id="STU-2026-00201",
                full_name="Duplicate Student",
            )


class TestDeactivateTeacher:
    async def test_deactivates_teacher(self, db_session, admin_user):
        svc = AdminService(db_session)
        teacher = await svc.add_teacher(
            admin=admin_user,
            telegram_user_id=700010,
            employee_id="EMP-010",
        )
        await db_session.commit()

        await svc.deactivate_teacher(admin_user, teacher)
        await db_session.commit()

        repo = TeacherRepository(db_session)
        refreshed = await repo.get_by_id(teacher.id)
        assert refreshed is not None
        assert refreshed.is_active is False
