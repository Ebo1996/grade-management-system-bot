"""
Input validation utilities.

All validation is centralised here so that the same rules apply
whether the input comes from Telegram or future API endpoints.
"""
import re
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------------------
# Student ID
# ---------------------------------------------------------------------------

# Accepted format: STU-YYYY-NNNNN (e.g. STU-2026-00125)
STUDENT_ID_PATTERN = re.compile(r"^STU-\d{4}-\d{5}$", re.IGNORECASE)


def validate_student_id(value: str) -> tuple[bool, str]:
    """
    Validate a student ID string.

    Returns:
        (True, normalised_id) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Student ID must be a non-empty string."

    normalised = value.strip().upper()

    if not STUDENT_ID_PATTERN.match(normalised):
        return False, (
            "Invalid student ID format.\n"
            "Expected format: STU-YYYY-NNNNN\n"
            "Example: STU-2026-00125"
        )
    return True, normalised


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

def validate_score(value: str) -> tuple[bool, str | Decimal]:
    """
    Validate an examination score.

    Accepts values like "85", "85.5", "100", "0".
    Returns:
        (True, Decimal_value) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Score must be a non-empty string."

    cleaned = value.strip().rstrip("%")

    try:
        score = Decimal(cleaned)
    except InvalidOperation:
        return False, "Score must be a number (e.g. 85 or 85.5)."

    if score < 0 or score > 100:
        return False, "Score must be between 0 and 100."

    return True, score


# ---------------------------------------------------------------------------
# Grade
# ---------------------------------------------------------------------------

VALID_GRADES = frozenset(
    [
        "A+", "A", "A-",
        "B+", "B", "B-",
        "C+", "C", "C-",
        "D+", "D", "D-",
        "E", "F",
        "PASS", "FAIL",
        "DISTINCTION", "MERIT", "CREDIT",
        "ABSENT",
    ]
)


def validate_grade(value: str) -> tuple[bool, str]:
    """
    Validate an examination grade.

    Returns:
        (True, normalised_grade) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Grade must be a non-empty string."

    normalised = value.strip().upper()

    if normalised not in VALID_GRADES:
        return False, (
            f"'{value}' is not a recognised grade.\n"
            f"Accepted grades: {', '.join(sorted(VALID_GRADES))}"
        )
    return True, normalised


# ---------------------------------------------------------------------------
# Subject name
# ---------------------------------------------------------------------------

SUBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 &\-/().]{2,100}$")


def validate_subject_name(value: str) -> tuple[bool, str]:
    """
    Validate a subject name.

    Returns:
        (True, normalised_name) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Subject name must be a non-empty string."

    cleaned = value.strip()

    if len(cleaned) < 2:
        return False, "Subject name must be at least 2 characters."

    if len(cleaned) > 100:
        return False, "Subject name must not exceed 100 characters."

    if not SUBJECT_NAME_PATTERN.match(cleaned):
        return False, (
            "Subject name contains invalid characters. "
            "Only letters, digits, spaces, and & - / ( ) . are allowed."
        )
    return True, cleaned


# ---------------------------------------------------------------------------
# Examination name
# ---------------------------------------------------------------------------

def validate_exam_name(value: str) -> tuple[bool, str]:
    """
    Validate an examination name.

    Returns:
        (True, normalised_name) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Examination name must be a non-empty string."

    cleaned = value.strip()

    if len(cleaned) < 2:
        return False, "Examination name must be at least 2 characters."

    if len(cleaned) > 200:
        return False, "Examination name must not exceed 200 characters."

    return True, cleaned


# ---------------------------------------------------------------------------
# Name (student / teacher full name)
# ---------------------------------------------------------------------------

def validate_full_name(value: str) -> tuple[bool, str]:
    """
    Validate a person's full name.

    Returns:
        (True, cleaned_name) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Full name must be a non-empty string."

    cleaned = value.strip()

    if len(cleaned) < 2:
        return False, "Full name must be at least 2 characters."

    if len(cleaned) > 150:
        return False, "Full name must not exceed 150 characters."

    return True, cleaned


# ---------------------------------------------------------------------------
# Employee ID (teacher)
# ---------------------------------------------------------------------------

EMPLOYEE_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-_]{2,30}$")


def validate_employee_id(value: str) -> tuple[bool, str]:
    """
    Validate a teacher employee ID.

    Returns:
        (True, normalised_id) on success.
        (False, error_message) on failure.
    """
    if not value or not isinstance(value, str):
        return False, "Employee ID must be a non-empty string."

    cleaned = value.strip().upper()

    if not EMPLOYEE_ID_PATTERN.match(cleaned):
        return False, (
            "Employee ID must be 2-30 characters and contain only "
            "letters, digits, hyphens, or underscores."
        )
    return True, cleaned


# ---------------------------------------------------------------------------
# Photo validation helpers (size / MIME type checked separately via aiogram)
# ---------------------------------------------------------------------------

ALLOWED_PHOTO_MIME_TYPES = frozenset(
    ["image/jpeg", "image/png", "image/webp"]
)

ALLOWED_PHOTO_EXTENSIONS = frozenset([".jpg", ".jpeg", ".png", ".webp"])


def validate_photo_mime_type(mime_type: str | None) -> bool:
    """Return True if the MIME type is an acceptable photo format."""
    if mime_type is None:
        return True  # aiogram photo objects don't always expose MIME
    return mime_type.lower() in ALLOWED_PHOTO_MIME_TYPES


def validate_photo_size(file_size: int, max_bytes: int) -> tuple[bool, str]:
    """
    Validate photo file size.

    Returns:
        (True, "") on success.
        (False, error_message) if too large.
    """
    if file_size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, (
            f"Photo is too large ({actual_mb:.1f} MB). "
            f"Maximum allowed size is {max_mb:.0f} MB."
        )
    return True, ""
