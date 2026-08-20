"""Student-related Pydantic schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    """Schema for creating a new student via admin panel."""

    student_id: str = Field(..., description="Institutional student ID, e.g. STU-2026-00125")
    full_name: str = Field(..., min_length=2, max_length=150)
    telegram_user_id: int | None = Field(None, description="Optional Telegram user ID to link")


class StudentProfile(BaseModel):
    """Public student profile returned to the student themselves."""

    id: int
    student_id: str
    full_name: str
    is_active: bool
    telegram_linked: bool
    created_at: datetime

    model_config = {"from_attributes": True}
