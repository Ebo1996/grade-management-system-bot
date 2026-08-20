"""Teacher-facing keyboards."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.result import Result


class TeacherKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Upload Result", callback_data="teacher:upload")
        builder.button(text="📋 My Uploads", callback_data="teacher:my_results:0")
        builder.button(text="🔎 Search Student", callback_data="teacher:search")
        builder.button(text="❓ Help", callback_data="teacher:help")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def upload_confirm(
        confirm_data: str = "teacher:upload:confirm",
        edit_data: str = "teacher:upload:edit",
        cancel_data: str = "teacher:upload:cancel",
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Confirm", callback_data=confirm_data)
        builder.button(text="✏️ Edit", callback_data=edit_data)
        builder.button(text="❌ Cancel", callback_data=cancel_data)
        builder.adjust(3)
        return builder.as_markup()

    @staticmethod
    def result_list(results: list[Result]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for result in results:
            subject = result.subject.name if result.subject else "?"
            exam = result.examination.name if result.examination else "?"
            student_id = result.student.student_id if result.student else "?"
            builder.button(
                text=f"📄 {student_id} | {subject}",
                callback_data=f"teacher:result:{result.id}",
            )
        builder.button(text="🏠 Menu", callback_data="teacher:menu")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def result_actions(result_id: int, can_edit: bool = True, can_delete: bool = True) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if can_edit:
            builder.button(text="✏️ Update", callback_data=f"teacher:result:update:{result_id}")
        if can_delete:
            builder.button(text="🗑 Delete", callback_data=f"teacher:result:delete:{result_id}")
        builder.button(text="⬅️ Back", callback_data="teacher:my_results:0")
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def duplicate_result_options(existing_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✏️ Update Existing",
            callback_data=f"teacher:result:update:{existing_id}",
        )
        builder.button(text="❌ Cancel", callback_data="teacher:upload:cancel")
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def cancel_upload() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Cancel Upload", callback_data="teacher:upload:cancel")
        return builder.as_markup()
