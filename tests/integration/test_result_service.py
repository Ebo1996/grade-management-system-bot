"""
Integration tests for the ResultService.

Tests result creation, duplicate detection, update, and deletion.
"""
from decimal import Decimal

import pytest
import pytest_asyncio

from app.database.models.user import User, UserRole
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.user_repo import UserRepository
from app.services.result_service import DuplicateResultError, ResultNotFoundError, ResultService


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest_asyncio.fixture
async def teacher_user(db_session):
    repo = UserRepository(db_session)
    user, _ = await repo.get_or_create(
        telegram_user_id=999001,
        username="teacher1",
        first_name="Mr",
        last_name="Teacher",
        role=UserRole.TEACHER,
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def student(db_session):
    repo = StudentRepository(db_session)
    s = await repo.create(
        student_id="STU-2026-00100",
        full_name="Test Student",
    )
    await db_session.commit()
    return s


# ------------------------------------------------------------------ #
# Tests                                                                 #
# ------------------------------------------------------------------ #

class TestCreateResult:
    async def test_creates_result_successfully(self, db_session, teacher_user, student):
        svc = ResultService(db_session)
        result = await svc.create_result(
            uploader=teacher_user,
            student_id_str="STU-2026-00100",
            subject_name="Mathematics",
            exam_name="Final Exam 2026",
            score=Decimal("85"),
            grade="A",
            remarks=None,
            photo_file_id="AgACAgItest123",
            photo_unique_id="unique123",
        )
        await db_session.commit()

        assert result.id is not None
        assert result.score == Decimal("85")
        assert result.grade == "A"
        assert result.photo_file_id == "AgACAgItest123"

    async def test_raises_if_student_not_found(self, db_session, teacher_user):
        svc = ResultService(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.create_result(
                uploader=teacher_user,
                student_id_str="STU-9999-00000",
                subject_name="Physics",
                exam_name="Midterm",
                score=None,
                grade=None,
                remarks=None,
                photo_file_id=None,
                photo_unique_id=None,
            )

    async def test_raises_duplicate_on_second_upload(self, db_session, teacher_user, student):
        svc = ResultService(db_session)

        await svc.create_result(
            uploader=teacher_user,
            student_id_str="STU-2026-00100",
            subject_name="Chemistry",
            exam_name="Final Exam 2026",
            score=Decimal("72"),
            grade="B",
            remarks=None,
            photo_file_id=None,
            photo_unique_id=None,
        )
        await db_session.commit()

        with pytest.raises(DuplicateResultError) as exc_info:
            await svc.create_result(
                uploader=teacher_user,
                student_id_str="STU-2026-00100",
                subject_name="Chemistry",
                exam_name="Final Exam 2026",
                score=Decimal("80"),
                grade="A",
                remarks=None,
                photo_file_id=None,
                photo_unique_id=None,
            )

        assert exc_info.value.existing_result is not None


class TestUpdateResult:
    async def test_updates_score_and_grade(self, db_session, teacher_user, student):
        svc = ResultService(db_session)
        result = await svc.create_result(
            uploader=teacher_user,
            student_id_str="STU-2026-00100",
            subject_name="English",
            exam_name="Midterm 2026",
            score=Decimal("60"),
            grade="C",
            remarks=None,
            photo_file_id=None,
            photo_unique_id=None,
        )
        await db_session.commit()

        updated = await svc.update_result(
            uploader=teacher_user,
            result_id=result.id,
            score=Decimal("75"),
            grade="B",
        )
        await db_session.commit()

        assert updated.score == Decimal("75")
        assert updated.grade == "B"


class TestDeleteResult:
    async def test_deletes_result(self, db_session, teacher_user, student):
        svc = ResultService(db_session)
        result = await svc.create_result(
            uploader=teacher_user,
            student_id_str="STU-2026-00100",
            subject_name="History",
            exam_name="Quiz 1",
            score=Decimal("90"),
            grade="A+",
            remarks=None,
            photo_file_id=None,
            photo_unique_id=None,
        )
        await db_session.commit()
        result_id = result.id

        await svc.delete_result(teacher_user, result_id)
        await db_session.commit()

        with pytest.raises(ResultNotFoundError):
            await svc.get_by_id(result_id)
