"""Student-facing keyboards."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.result import Result


class StudentKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="📊 Check My Results", callback_data="student:check_results")
        builder.button(text="📚 My Result History", callback_data="student:my_results:0")
        builder.button(text="👤 My Profile", callback_data="student:profile")
        builder.button(text="❓ Help", callback_data="student:help")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def result_list(results: list[Result], page: int = 0) -> InlineKeyboardMarkup:
        """
        Inline keyboard listing results.

        Each button shows subject + exam and carries the result ID.
        """
        builder = InlineKeyboardBuilder()
        for i, result in enumerate(results, start=1):
            subject = result.subject.name if result.subject else "Unknown"
            exam = result.examination.name if result.examination else "Unknown"
            label = f"{i}️⃣ {subject} — {exam}"
            builder.button(
                text=label,
                callback_data=f"student:result:{result.id}",
            )
        builder.button(text="🏠 Main Menu", callback_data="student:menu")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def result_detail_back() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Back to Results", callback_data="student:my_results:0")
        builder.button(text="🏠 Main Menu", callback_data="student:menu")
        builder.adjust(2)
        return builder.as_markup()
