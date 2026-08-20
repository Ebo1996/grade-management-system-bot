"""
Integration tests for the StudentService.

Uses an in-memory SQLite database.
"""
import pytest
import pytest_asyncio

from app.database.models.user import User, UserRole
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.user_repo import UserRepository
from app.services.student_service import (
    StudentAccessError,
    StudentInactiveError,
    StudentNotFoundError,
    StudentService,
)


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest_asyncio.fixture
async def student_user(db_session):
    """Create and return a basic student User."""
    repo = UserRepository(db_session)
    user, _ = await repo.get_or_create(
        telegram_user_id=111111,
        username="student_user",
        first_name="Alice",
        last_name="Smith",
        role=UserRole.STUDENT,
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def other_student_user(db_session):
    """Create a second student User (for cross-access tests)."""
    repo = UserRepository(db_session)
    user, _ = await repo.get_or_create(
        telegram_user_id=222222,
        username="student_user2",
        first_name="Bob",
        last_name="Jones",
        role=UserRole.STUDENT,
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def linked_student(db_session, student_user):
    """Create a Student record linked to student_user."""
    repo = StudentRepository(db_session)
    student = await repo.create(
        student_id="STU-2026-00001",
        full_name="Alice Smith",
        telegram_user_id=student_user.telegram_user_id,
        user_id=student_user.id,
    )
    await db_session.commit()
    return student


@pytest_asyncio.fixture
async def other_linked_student(db_session, other_student_user):
    """Create a Student record linked to other_student_user."""
    repo = StudentRepository(db_session)
    student = await repo.create(
        student_id="STU-2026-00002",
        full_name="Bob Jones",
        telegram_user_id=other_student_user.telegram_user_id,
        user_id=other_student_user.id,
    )
    await db_session.commit()
    return student


# ------------------------------------------------------------------ #
# Tests                                                                 #
# ------------------------------------------------------------------ #

class TestGetStudentForUser:
    async def test_returns_linked_student(self, db_session, student_user, linked_student):
        svc = StudentService(db_session)
        result = await svc.get_student_for_user(student_user)
        assert result.id == linked_student.id
        assert result.student_id == "STU-2026-00001"

    async def test_raises_if_no_profile(self, db_session, other_student_user):
        svc = StudentService(db_session)
        with pytest.raises(StudentNotFoundError):
            await svc.get_student_for_user(other_student_user)

    async def test_raises_if_student_inactive(self, db_session, student_user, linked_student):
        linked_student.is_active = False
        await db_session.commit()

        svc = StudentService(db_session)
        with pytest.raises(StudentInactiveError):
            await svc.get_student_for_user(student_user)


class TestLookupStudentSecure:
    async def test_linked_mode_allows_own_lookup(
        self, db_session, student_user, linked_student, monkeypatch
    ):
        from app.config import settings as settings_module
        # Patch settings to use linked mode
        monkeypatch.setattr(
            "app.services.student_service.get_settings",
            lambda: type("S", (), {"student_lookup_mode": "linked"})(),
        )
        svc = StudentService(db_session)
        result = await svc.lookup_student_secure(student_user, "STU-2026-00001")
        assert result.id == linked_student.id

    async def test_linked_mode_blocks_cross_access(
        self, db_session, student_user, linked_student, other_linked_student, monkeypatch
    ):
        monkeypatch.setattr(
            "app.services.student_service.get_settings",
            lambda: type("S", (), {"student_lookup_mode": "linked"})(),
        )
        svc = StudentService(db_session)
        with pytest.raises(StudentAccessError):
            await svc.lookup_student_secure(student_user, "STU-2026-00002")

    async def test_raises_if_student_not_found(
        self, db_session, student_user, monkeypatch
    ):
        monkeypatch.setattr(
            "app.services.student_service.get_settings",
            lambda: type("S", (), {"student_lookup_mode": "linked"})(),
        )
        svc = StudentService(db_session)
        with pytest.raises(StudentNotFoundError):
            await svc.lookup_student_secure(student_user, "STU-9999-99999")
