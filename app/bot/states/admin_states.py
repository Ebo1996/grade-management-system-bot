"""FSM states for admin workflows."""
from aiogram.fsm.state import State, StatesGroup


class AddTeacherStates(StatesGroup):
    waiting_telegram_id = State()
    waiting_employee_id = State()
    waiting_first_name = State()
    confirm = State()


class AddStudentStates(StatesGroup):
    waiting_student_id = State()
    waiting_full_name = State()
    waiting_telegram_id = State()
    confirm = State()


class LinkStudentStates(StatesGroup):
    waiting_telegram_id = State()


class StudentLookupStates(StatesGroup):
    waiting_student_id = State()


class TeacherSearchStates(StatesGroup):
    waiting_query = State()


class UpdateResultStates(StatesGroup):
    waiting_score = State()
    waiting_grade = State()
