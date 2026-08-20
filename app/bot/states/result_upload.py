"""
FSM states for the teacher result-upload workflow.

Flow:
    WAITING_STUDENT_ID
        → WAITING_SUBJECT
        → WAITING_EXAM
        → WAITING_SCORE
        → WAITING_GRADE
        → WAITING_PHOTO
        → CONFIRM_RESULT
        → (saved or cancelled)
"""
from aiogram.fsm.state import State, StatesGroup


class ResultUploadStates(StatesGroup):
    waiting_student_id = State()
    waiting_subject = State()
    waiting_exam = State()
    waiting_score = State()
    waiting_grade = State()
    waiting_photo = State()
    confirm_result = State()
