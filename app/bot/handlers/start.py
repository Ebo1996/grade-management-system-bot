"""
Start / help handlers.

Routes users to the appropriate main menu based on their role.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.admin import AdminKeyboards
from app.bot.keyboards.student import StudentKeyboards
from app.bot.keyboards.teacher import TeacherKeyboards
from app.database.models.user import User, UserRole
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router(name="start")


def _welcome_text(user: User) -> str:
    name = user.display_name
    if user.role == UserRole.ADMIN:
        return (
            f"👋 Welcome back, {name}!\n\n"
            "🔐 You are logged in as an <b>Administrator</b>.\n"
            "Use the panel below to manage the system."
        )
    if user.role == UserRole.TEACHER:
        return (
            f"👋 Welcome back, {name}!\n\n"
            "👨‍🏫 You are logged in as a <b>Teacher</b>.\n"
            "Use the panel below to manage results."
        )
    return (
        f"👋 Welcome, {name}!\n\n"
        "🎓 This is the <b>Student Result Management System</b>.\n"
        "Use the menu below to check your examination results."
    )


def _menu_keyboard(user: User):  # type: ignore[no-untyped-def]
    if user.role == UserRole.ADMIN:
        return AdminKeyboards.main_menu()
    if user.role == UserRole.TEACHER:
        return TeacherKeyboards.main_menu()
    return StudentKeyboards.main_menu()


@router.message(Command("start"))
async def cmd_start(message: Message, current_user: User) -> None:
    """Handle /start — show the role-appropriate main menu."""
    if not current_user.is_active:
        await message.answer(
            "❌ Your account has been deactivated.\n"
            "Please contact the system administrator."
        )
        return

    logger.info(
        "user_started_bot",
        telegram_user_id=current_user.telegram_user_id,
        role=current_user.role,
    )

    await message.answer(
        _welcome_text(current_user),
        reply_markup=_menu_keyboard(current_user),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message, current_user: User) -> None:
    """Show role-appropriate help text."""
    if current_user.role == UserRole.ADMIN:
        text = (
            "🔐 <b>Admin Help</b>\n\n"
            "• Manage Teachers — add or deactivate teacher accounts\n"
            "• Manage Students — register students and link Telegram accounts\n"
            "• Manage Results — view or delete any result\n"
            "• Audit Logs — review all system actions\n"
            "• Statistics — see system-wide counts\n\n"
            "Use /start to return to the main menu at any time."
        )
    elif current_user.role == UserRole.TEACHER:
        text = (
            "👨‍🏫 <b>Teacher Help</b>\n\n"
            "• Upload Result — enter student ID, subject, exam, score/grade, "
            "and photo for a new result\n"
            "• My Uploads — view results you have uploaded\n"
            "• Search Student — find a student by name or ID\n\n"
            "Use /start to return to the main menu."
        )
    else:
        text = (
            "🎓 <b>Student Help</b>\n\n"
            "• Check My Results — enter your student ID to view results\n"
            "• My Result History — browse all your available results\n"
            "• My Profile — view your linked student account\n\n"
            "Your results are private — only you can view them.\n"
            "Use /start to return to the main menu."
        )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data in ("student:menu", "teacher:menu", "admin:menu"))
async def back_to_menu(callback: CallbackQuery, current_user: User) -> None:
    """Handle back-to-menu callbacks from any panel."""
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        _welcome_text(current_user),
        reply_markup=_menu_keyboard(current_user),
        parse_mode="HTML",
    )
