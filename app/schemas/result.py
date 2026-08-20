"""Result-related Pydantic schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ResultUploadData(BaseModel):
    """Data collected during the teacher result-upload FSM conversation."""

    student_id: str = Field(..., description="Institutional student ID string")
    subject_name: str = Field(..., description="Subject name")
    exam_name: str = Field(..., description="Examination name")
    score: Decimal | None = Field(None, description="Score 0-100")
    grade: str | None = Field(None, description="Grade string")
    remarks: str | None = Field(None, description="Optional remarks")
    photo_file_id: str | None = Field(None, description="Telegram file_id")
    photo_unique_id: str | None = Field(None, description="Telegram file_unique_id")


class ResultSummary(BaseModel):
    """Lightweight result summary for list display."""

    id: int
    subject_name: str
    exam_name: str
    score: Decimal | None
    grade: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
