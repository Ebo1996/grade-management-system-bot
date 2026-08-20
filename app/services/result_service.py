"""
Result service.

Handles the creation, retrieval, update, and deletion of results.
Enforces duplicate detection and audit logging.
"""
import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.examination import ExamType
from app.database.models.result import Result
from app.database.models.user import User
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.examination_repo import ExaminationRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.subject_repo import SubjectRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DuplicateResultError(Exception):
    """Raised when a result already exists for (student, subject, exam)."""

    def __init__(self, existing_result: Result) -> None:
        self.existing_result = existing_result
        super().__init__(
            f"A result already exists for student_id={existing_result.student_id}, "
            f"subject_id={existing_result.subject_id}, "
            f"examination_id={existing_result.examination_id}."
        )


class ResultNotFoundError(Exception):
    """Raised when the requested result does not exist."""


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._results = ResultRepository(session)
        self._students = StudentRepository(session)
        self._subjects = SubjectRepository(session)
        self._exams = ExaminationRepository(session)
        self._audit = AuditRepository(session)

    async def create_result(
        self,
        uploader: User,
        student_id_str: str,
        subject_name: str,
        exam_name: str,
        score: Decimal | None,
        grade: str | None,
        remarks: str | None,
        photo_file_id: str | None,
        photo_unique_id: str | None,
    ) -> Result:
        """
        Create a new result after performing all validations.

        Args:
            uploader: The authenticated teacher User performing the upload.
            student_id_str: The institutional student ID string (e.g. STU-2026-00125).
            subject_name: Subject name; created if it doesn't exist.
            exam_name: Examination name; created if it doesn't exist.
            score: Numeric score (0-100).
            grade: Grade string (e.g. "A+").
            remarks: Optional free-text remarks.
            photo_file_id: Telegram file_id of the uploaded photo.
            photo_unique_id: Telegram file_unique_id.

        Returns:
            The newly created Result (with relations loaded).

        Raises:
            ValueError: If the student does not exist or is inactive.
            DuplicateResultError: If a result already exists for this combination.
        """
        # 1. Resolve student
        student = await self._students.get_by_student_id(student_id_str)
        if student is None:
            raise ValueError(f"Student '{student_id_str}' not found.")
        if not student.is_active:
            raise ValueError(f"Student '{student_id_str}' is deactivated.")

        # 2. Resolve or create subject
        subject, _ = await self._subjects.get_or_create(subject_name)

        # 3. Resolve or create examination
        exam, _ = await self._exams.get_or_create(
            name=exam_name, exam_type=ExamType.OTHER
        )

        # 4. Duplicate check
        existing = await self._results.get_by_student_subject_exam(
            student_id=student.id,
            subject_id=subject.id,
            examination_id=exam.id,
        )
        if existing is not None:
            raise DuplicateResultError(existing)

        # 5. Create
        result = await self._results.create(
            student_id=student.id,
            subject_id=subject.id,
            examination_id=exam.id,
            uploaded_by=uploader.id,
            score=score,
            grade=grade,
            remarks=remarks,
            photo_file_id=photo_file_id,
            photo_unique_id=photo_unique_id,
        )

        # 6. Audit
        await self._audit.log(
            action="result_created",
            entity_type="result",
            entity_id=result.id,
            user_id=uploader.id,
            telegram_user_id=uploader.telegram_user_id,
            new_value={
                "student_id": student_id_str,
                "subject": subject_name,
                "exam": exam_name,
                "score": str(score) if score else None,
                "grade": grade,
            },
        )

        logger.info(
            "result_created",
            result_id=result.id,
            student_id=student_id_str,
            uploader_telegram_id=uploader.telegram_user_id,
        )
        return result

    async def update_result(
        self,
        uploader: User,
        result_id: int,
        score: Decimal | None = None,
        grade: str | None = None,
        remarks: str | None = None,
        photo_file_id: str | None = None,
        photo_unique_id: str | None = None,
    ) -> Result:
        """
        Update an existing result.

        Only the teacher who uploaded the result (or an admin) should call this.
        Access control must be enforced by the caller.
        """
        result = await self._results.get_by_id_with_relations(result_id)
        if result is None:
            raise ResultNotFoundError(f"Result {result_id} not found.")

        old_snapshot = {
            "score": str(result.score),
            "grade": result.grade,
            "remarks": result.remarks,
            "photo_file_id": result.photo_file_id,
        }

        if score is not None:
            result.score = score
        if grade is not None:
            result.grade = grade
        if remarks is not None:
            result.remarks = remarks
        if photo_file_id is not None:
            result.photo_file_id = photo_file_id
            result.photo_unique_id = photo_unique_id

        await self._session.flush()
        await self._session.refresh(result)

        await self._audit.log(
            action="result_updated",
            entity_type="result",
            entity_id=result.id,
            user_id=uploader.id,
            telegram_user_id=uploader.telegram_user_id,
            old_value=old_snapshot,
            new_value={
                "score": str(result.score),
                "grade": result.grade,
                "remarks": result.remarks,
                "photo_file_id": result.photo_file_id,
            },
        )

        logger.info(
            "result_updated",
            result_id=result.id,
            uploader_telegram_id=uploader.telegram_user_id,
        )
        return result

    async def delete_result(self, deleter: User, result_id: int) -> None:
        """Delete a result permanently."""
        result = await self._results.get_by_id_with_relations(result_id)
        if result is None:
            raise ResultNotFoundError(f"Result {result_id} not found.")

        snapshot = {
            "student_id": result.student.student_id if result.student else None,
            "subject": result.subject.name if result.subject else None,
            "exam": result.examination.name if result.examination else None,
            "score": str(result.score),
            "grade": result.grade,
        }

        await self._results.delete(result)

        await self._audit.log(
            action="result_deleted",
            entity_type="result",
            entity_id=result_id,
            user_id=deleter.id,
            telegram_user_id=deleter.telegram_user_id,
            old_value=snapshot,
        )

        logger.info(
            "result_deleted",
            result_id=result_id,
            deleter_telegram_id=deleter.telegram_user_id,
        )

    async def get_by_id(self, result_id: int) -> Result:
        """Fetch a result by ID with relations."""
        result = await self._results.get_by_id_with_relations(result_id)
        if result is None:
            raise ResultNotFoundError(f"Result {result_id} not found.")
        return result
