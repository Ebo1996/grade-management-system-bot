"""Admin-facing keyboards."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.student import Student
from app.database.models.teacher import Teacher


class AdminKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="👨‍🏫 Manage Teachers", callback_data="admin:teachers")
        builder.button(text="👨‍🎓 Manage Students", callback_data="admin:students")
        builder.button(text="📊 Manage Results", callback_data="admin:results")
        builder.button(text="📋 Audit Logs", callback_data="admin:audit:0")
        builder.button(text="📈 Statistics", callback_data="admin:stats")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def teacher_list(teachers: list[Teacher], page: int = 0) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Add Teacher", callback_data="admin:teacher:add")
        for t in teachers:
            name = t.user.display_name if t.user else "Unknown"
            builder.button(
                text=f"👤 {name} ({t.employee_id})",
                callback_data=f"admin:teacher:view:{t.id}",
            )
        builder.button(text="⬅️ Back", callback_data="admin:menu")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def teacher_actions(teacher_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🚫 Deactivate",
            callback_data=f"admin:teacher:deactivate:{teacher_id}",
        )
        builder.button(text="⬅️ Back", callback_data="admin:teachers")
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def student_list(students: list[Student], page: int = 0) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Add Student", callback_data="admin:student:add")
        for s in students:
            builder.button(
                text=f"🎓 {s.full_name} ({s.student_id})",
                callback_data=f"admin:student:view:{s.id}",
            )
        builder.button(text="⬅️ Back", callback_data="admin:menu")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def student_actions(student_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔗 Link Telegram",
            callback_data=f"admin:student:link:{student_id}",
        )
        builder.button(
            text="🚫 Deactivate",
            callback_data=f"admin:student:deactivate:{student_id}",
        )
        builder.button(text="⬅️ Back", callback_data="admin:students")
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def confirm_deactivate(entity: str, entity_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✅ Yes, Deactivate",
            callback_data=f"admin:{entity}:deactivate:confirm:{entity_id}",
        )
        builder.button(text="❌ Cancel", callback_data=f"admin:{entity}s")
        builder.adjust(2)
        return builder.as_markup()
