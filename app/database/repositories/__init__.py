"""Repository package — data-access objects."""
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.teacher_repo import TeacherRepository
from app.database.repositories.subject_repo import SubjectRepository
from app.database.repositories.examination_repo import ExaminationRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.audit_repo import AuditRepository

__all__ = [
    "UserRepository",
    "StudentRepository",
    "TeacherRepository",
    "SubjectRepository",
    "ExaminationRepository",
    "ResultRepository",
    "AuditRepository",
]
