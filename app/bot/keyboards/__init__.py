"""Keyboard builders."""
from app.bot.keyboards.student import StudentKeyboards
from app.bot.keyboards.teacher import TeacherKeyboards
from app.bot.keyboards.admin import AdminKeyboards
from app.bot.keyboards.common import CommonKeyboards

__all__ = ["StudentKeyboards", "TeacherKeyboards", "AdminKeyboards", "CommonKeyboards"]
