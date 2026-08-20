"""Shared keyboard components used across multiple roles."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CommonKeyboards:
    @staticmethod
    def cancel_button(text: str = "❌ Cancel") -> InlineKeyboardMarkup:
        """Single cancel button."""
        builder = InlineKeyboardBuilder()
        builder.button(text=text, callback_data="action:cancel")
        return builder.as_markup()

    @staticmethod
    def confirm_cancel(
        confirm_data: str = "action:confirm",
        cancel_data: str = "action:cancel",
    ) -> InlineKeyboardMarkup:
        """Confirm / Cancel pair."""
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Confirm", callback_data=confirm_data)
        builder.button(text="❌ Cancel", callback_data=cancel_data)
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def paginator(
        current_page: int,
        total_pages: int,
        prefix: str,
    ) -> InlineKeyboardMarkup:
        """
        Generic prev/next paginator.

        Args:
            current_page: 0-indexed current page.
            total_pages: Total number of pages.
            prefix: Callback prefix, e.g. "student_results".
                    Generates callbacks like "student_results:page:1".
        """
        builder = InlineKeyboardBuilder()
        if current_page > 0:
            builder.button(
                text="⬅️ Prev",
                callback_data=f"{prefix}:page:{current_page - 1}",
            )
        if current_page < total_pages - 1:
            builder.button(
                text="Next ➡️",
                callback_data=f"{prefix}:page:{current_page + 1}",
            )
        builder.adjust(2)
        return builder.as_markup()
