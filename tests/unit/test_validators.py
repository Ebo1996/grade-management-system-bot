"""Unit tests for input validators."""
import pytest

from app.utils.validators import (
    validate_employee_id,
    validate_exam_name,
    validate_full_name,
    validate_grade,
    validate_photo_size,
    validate_score,
    validate_student_id,
    validate_subject_name,
)


# ------------------------------------------------------------------ #
# Student ID                                                           #
# ------------------------------------------------------------------ #

class TestValidateStudentId:
    def test_valid_id(self):
        ok, result = validate_student_id("STU-2026-00125")
        assert ok is True
        assert result == "STU-2026-00125"

    def test_valid_id_lowercase_normalised(self):
        ok, result = validate_student_id("stu-2026-00125")
        assert ok is True
        assert result == "STU-2026-00125"

    def test_valid_id_with_spaces_stripped(self):
        ok, result = validate_student_id("  STU-2026-00001  ")
        assert ok is True
        assert result == "STU-2026-00001"

    def test_invalid_missing_prefix(self):
        ok, _ = validate_student_id("2026-00125")
        assert ok is False

    def test_invalid_wrong_number_of_digits(self):
        ok, _ = validate_student_id("STU-2026-125")
        assert ok is False

    def test_invalid_empty_string(self):
        ok, _ = validate_student_id("")
        assert ok is False

    def test_invalid_none(self):
        ok, _ = validate_student_id(None)  # type: ignore[arg-type]
        assert ok is False

    def test_invalid_extra_characters(self):
        ok, _ = validate_student_id("STU-2026-00125-EXTRA")
        assert ok is False


# ------------------------------------------------------------------ #
# Score                                                                 #
# ------------------------------------------------------------------ #

class TestValidateScore:
    def test_valid_integer(self):
        ok, result = validate_score("85")
        assert ok is True
        assert float(result) == 85.0  # type: ignore[arg-type]

    def test_valid_decimal(self):
        ok, result = validate_score("85.5")
        assert ok is True

    def test_valid_zero(self):
        ok, result = validate_score("0")
        assert ok is True

    def test_valid_hundred(self):
        ok, result = validate_score("100")
        assert ok is True

    def test_valid_with_percent_suffix(self):
        ok, result = validate_score("85%")
        assert ok is True

    def test_invalid_above_100(self):
        ok, _ = validate_score("101")
        assert ok is False

    def test_invalid_negative(self):
        ok, _ = validate_score("-1")
        assert ok is False

    def test_invalid_text(self):
        ok, _ = validate_score("abc")
        assert ok is False

    def test_invalid_empty(self):
        ok, _ = validate_score("")
        assert ok is False


# ------------------------------------------------------------------ #
# Grade                                                                 #
# ------------------------------------------------------------------ #

class TestValidateGrade:
    def test_valid_grades(self):
        for grade in ["A+", "A", "A-", "B+", "B", "C", "F", "PASS", "FAIL"]:
            ok, result = validate_grade(grade)
            assert ok is True, f"Expected {grade} to be valid"

    def test_lowercase_normalised(self):
        ok, result = validate_grade("a+")
        assert ok is True
        assert result == "A+"

    def test_invalid_grade(self):
        ok, _ = validate_grade("Z")
        assert ok is False

    def test_invalid_empty(self):
        ok, _ = validate_grade("")
        assert ok is False

    def test_invalid_number(self):
        ok, _ = validate_grade("95")
        assert ok is False


# ------------------------------------------------------------------ #
# Subject name                                                          #
# ------------------------------------------------------------------ #

class TestValidateSubjectName:
    def test_valid_simple(self):
        ok, result = validate_subject_name("Mathematics")
        assert ok is True
        assert result == "Mathematics"

    def test_valid_with_ampersand(self):
        ok, _ = validate_subject_name("Science & Technology")
        assert ok is True

    def test_too_short(self):
        ok, _ = validate_subject_name("X")
        assert ok is False

    def test_too_long(self):
        ok, _ = validate_subject_name("A" * 101)
        assert ok is False

    def test_invalid_special_chars(self):
        ok, _ = validate_subject_name("Math@School!")
        assert ok is False


# ------------------------------------------------------------------ #
# Full name                                                             #
# ------------------------------------------------------------------ #

class TestValidateFullName:
    def test_valid(self):
        ok, result = validate_full_name("John Doe")
        assert ok is True
        assert result == "John Doe"

    def test_strips_whitespace(self):
        ok, result = validate_full_name("  Jane Smith  ")
        assert ok is True
        assert result == "Jane Smith"

    def test_too_short(self):
        ok, _ = validate_full_name("A")
        assert ok is False

    def test_too_long(self):
        ok, _ = validate_full_name("A" * 151)
        assert ok is False


# ------------------------------------------------------------------ #
# Employee ID                                                           #
# ------------------------------------------------------------------ #

class TestValidateEmployeeId:
    def test_valid(self):
        ok, result = validate_employee_id("EMP-001")
        assert ok is True
        assert result == "EMP-001"

    def test_normalised_to_uppercase(self):
        ok, result = validate_employee_id("emp-001")
        assert ok is True
        assert result == "EMP-001"

    def test_too_short(self):
        ok, _ = validate_employee_id("A")
        assert ok is False

    def test_invalid_space(self):
        ok, _ = validate_employee_id("EMP 001")
        assert ok is False


# ------------------------------------------------------------------ #
# Photo size                                                            #
# ------------------------------------------------------------------ #

class TestValidatePhotoSize:
    def test_within_limit(self):
        ok, _ = validate_photo_size(5 * 1024 * 1024, 10 * 1024 * 1024)
        assert ok is True

    def test_exactly_at_limit(self):
        ok, _ = validate_photo_size(10 * 1024 * 1024, 10 * 1024 * 1024)
        assert ok is True

    def test_exceeds_limit(self):
        ok, msg = validate_photo_size(11 * 1024 * 1024, 10 * 1024 * 1024)
        assert ok is False
        assert "MB" in msg
