"""
Student handlers.

Covers:
- Main menu navigation
- Secure result lookup by student ID
- Result list / detail views
- Profile view
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.student import StudentKeyboards
from app.database.models.user import User, UserRole
from app.bot.states.admin_states import StudentLookupStates
from app.services.student_service import (
    StudentAccessError,
    StudentInactiveError,
    StudentNotFoundError,
    StudentService,
)
from app.utils.logger import get_logger
from app.utils.validators import validate_student_id

logger = get_logger(__name__)
router = Router(name="student")

PAGE_SIZE = 10


# ------------------------------------------------------------------ #
# Guards                                                               #
# ------------------------------------------------------------------ #

def _is_student(user: User) -> bool:
    return user.role == UserRole.STUDENT and user.is_active


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _format_result_detail(result) -> str:  # type: ignore[no-untyped-def]
    subject = result.subject.name if result.subject else "N/A"
    exam = result.examination.name if result.examination else "N/A"
    score = f"{result.score}%" if result.score is not None else "—"
    grade = result.grade or "—"
    student = result.student
    student_id = student.student_id if student else "—"
    student_name = student.full_name if student else "—"
    date = result.created_at.strftime("%B %d, %Y") if result.created_at else "—"
    remarks = f"\n📝 Remarks: {result.remarks}" if result.remarks else ""

    return (
        "📊 <b>Result Details</b>\n\n"
        f"👤 Student: <b>{student_name}</b>\n"
        f"🪪 ID: <code>{student_id}</code>\n\n"
        f"📚 Subject: <b>{subject}</b>\n"
        f"📝 Exam: <b>{exam}</b>\n\n"
        f"🎯 Score: <b>{score}</b>\n"
        f"🏅 Grade: <b>{grade}</b>\n"
        f"📅 Uploaded: {date}"
        f"{remarks}"
    )


# ------------------------------------------------------------------ #
# Student main menu                                                    #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "student:menu")
async def student_menu(callback: CallbackQuery, current_user: User) -> None:
    if not _is_student(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👋 Hello, {current_user.display_name}!\n\nWhat would you like to do?",
        reply_markup=StudentKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Check results — ask for student ID                                   #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "student:check_results")
async def student_check_results_start(
    callback: CallbackQuery, state: FSMContext, current_user: User
) -> None:
    if not _is_student(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(StudentLookupStates.waiting_student_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "🔍 <b>Check My Results</b>\n\n"
        "Please enter your student ID.\n"
        "Example: <code>STU-2026-00125</code>\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )


@router.message(StudentLookupStates.waiting_student_id, F.text)
async def student_receive_id(
    message: Message,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:

    raw_id = (message.text or "").strip()

    # Cancel
    if raw_id.lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(
            "❌ Cancelled.",
            reply_markup=StudentKeyboards.main_menu(),
        )
        return

    # Validate format
    ok, result = validate_student_id(raw_id)
    if not ok:
        await message.answer(
            f"⚠️ {result}\n\nPlease try again or send /cancel."
        )
        return

    student_id_str: str = result  # type: ignore[assignment]

    # Secure lookup
    service = StudentService(db_session)
    try:
        student = await service.lookup_student_secure(current_user, student_id_str)
    except StudentNotFoundError as exc:
        await message.answer(f"❌ {exc}\n\nPlease check your student ID and try again.")
        return
    except StudentInactiveError as exc:
        await message.answer(f"⛔ {exc}")
        await state.clear()
        return
    except StudentAccessError as exc:
        await message.answer(f"🚫 {exc}")
        await state.clear()
        return

    # Fetch results
    results = await service.get_results(student, limit=PAGE_SIZE)
    await state.clear()

    if not results:
        await message.answer(
            f"📭 No results found for <b>{student.full_name}</b> "
            f"(<code>{student.student_id}</code>) yet.\n\n"
            "Results will appear here once uploaded by your teacher.",
            reply_markup=StudentKeyboards.main_menu(),
            parse_mode="HTML",
        )
        return

    count = await service.count_results(student)
    await message.answer(
        f"📚 Results for <b>{student.full_name}</b>\n"
        f"Found <b>{count}</b> result(s).\n\n"
        "Select a result to view details:",
        reply_markup=StudentKeyboards.result_list(results),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# My Results (paginated list)                                          #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("student:my_results:"))
async def student_my_results(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_student(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    page = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    offset = page * PAGE_SIZE

    service = StudentService(db_session)
    try:
        student = await service.get_student_for_user(current_user)
    except (StudentNotFoundError, StudentInactiveError) as exc:
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]
        return

    results = await service.get_results(student, limit=PAGE_SIZE, offset=offset)
    total = await service.count_results(student)

    if not results:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "📭 You have no results yet.\n"
            "Results will appear here once uploaded by your teacher.",
            reply_markup=StudentKeyboards.main_menu(),
        )
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📚 <b>My Results</b> — Page {page + 1}/{total_pages}\n\n"
        "Select a result to view details:",
        reply_markup=StudentKeyboards.result_list(results, page=page),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Result detail                                                         #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("student:result:"))
async def student_result_detail(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_student(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    service = StudentService(db_session)
    try:
        student = await service.get_student_for_user(current_user)
        result = await service.get_result_by_id(student, result_id)
    except (StudentNotFoundError, StudentInactiveError, StudentAccessError) as exc:
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]
        return

    detail_text = _format_result_detail(result)

    # Send detail text
    await callback.message.answer(  # type: ignore[union-attr]
        detail_text,
        reply_markup=StudentKeyboards.result_detail_back(),
        parse_mode="HTML",
    )

    # Send exam sheet photo if available
    if result.photo_file_id:
        await callback.message.answer_photo(  # type: ignore[union-attr]
            photo=result.photo_file_id,
            caption="📄 Examination Sheet",
        )
    else:
        await callback.message.answer("📎 No examination sheet photo available for this result.")  # type: ignore[union-attr]


# ------------------------------------------------------------------ #
# Profile                                                               #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "student:profile")
async def student_profile(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_student(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    service = StudentService(db_session)
    try:
        student = await service.get_student_for_user(current_user)
        total = await service.count_results(student)
    except StudentNotFoundError:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "👤 <b>My Profile</b>\n\n"
            "⚠️ No student profile is linked to your Telegram account.\n"
            "Please contact the school administrator to link your account.",
            reply_markup=StudentKeyboards.main_menu(),
            parse_mode="HTML",
        )
        return

    link_status = "✅ Linked" if student.telegram_user_id else "⚠️ Not linked"

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👤 <b>My Profile</b>\n\n"
        f"🪪 Student ID: <code>{student.student_id}</code>\n"
        f"👤 Full Name: <b>{student.full_name}</b>\n"
        f"📊 Total Results: <b>{total}</b>\n"
        f"🔗 Account Link: {link_status}",
        reply_markup=StudentKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Help                                                                  #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "student:help")
async def student_help(callback: CallbackQuery, current_user: User) -> None:
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        "❓ <b>Help</b>\n\n"
        "📊 <b>Check My Results</b> — Enter your student ID to find results\n"
        "📚 <b>My Result History</b> — Browse all your results\n"
        "👤 <b>My Profile</b> — View your linked student account\n\n"
        "Your results are private. Only you can see them.\n\n"
        "Having trouble? Contact your school administrator.",
        reply_markup=StudentKeyboards.main_menu(),
        parse_mode="HTML",
    )
