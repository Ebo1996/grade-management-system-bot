"""
Admin handlers.

Covers:
- Admin panel navigation
- Add / deactivate teachers
- Add / deactivate students
- Manage results (view / delete)
- Audit log viewer
- Statistics
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import AdminKeyboards
from app.bot.keyboards.teacher import TeacherKeyboards
from app.bot.states.admin_states import AddStudentStates, AddTeacherStates, LinkStudentStates
from app.database.models.user import User, UserRole
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.teacher_repo import TeacherRepository
from app.services.admin_service import AdminService
from app.services.result_service import ResultNotFoundError, ResultService
from app.utils.logger import get_logger
from app.utils.validators import validate_employee_id, validate_full_name, validate_student_id

logger = get_logger(__name__)
router = Router(name="admin")

PAGE_SIZE = 10


# ------------------------------------------------------------------ #
# Guards                                                               #
# ------------------------------------------------------------------ #

def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN and user.is_active


# ------------------------------------------------------------------ #
# Admin main menu                                                       #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery, current_user: User) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"🔐 <b>Admin Panel</b>\n\nWelcome, {current_user.display_name}!",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Teachers                                                              #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "admin:teachers")
async def admin_teachers(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    svc = AdminService(db_session)
    teachers = await svc.list_teachers(limit=PAGE_SIZE)

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👨‍🏫 <b>Teachers</b> ({len(teachers)} active)",
        reply_markup=AdminKeyboards.teacher_list(teachers),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:teacher:view:"))
async def admin_teacher_view(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    teacher_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    repo = TeacherRepository(db_session)
    teacher = await repo.get_by_id(teacher_id)

    if not teacher:
        await callback.message.answer("❌ Teacher not found.")  # type: ignore[union-attr]
        return

    user = teacher.user
    name = user.display_name if user else "Unknown"
    tg_id = user.telegram_user_id if user else "—"
    status = "✅ Active" if teacher.is_active else "🚫 Inactive"

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👨‍🏫 <b>Teacher Details</b>\n\n"
        f"👤 Name: <b>{name}</b>\n"
        f"🪪 Employee ID: <code>{teacher.employee_id}</code>\n"
        f"📱 Telegram ID: <code>{tg_id}</code>\n"
        f"📊 Status: {status}",
        reply_markup=AdminKeyboards.teacher_actions(teacher_id),
        parse_mode="HTML",
    )


# ---------- Add Teacher FSM ----------

@router.callback_query(F.data == "admin:teacher:add")
async def admin_add_teacher_start(
    callback: CallbackQuery, state: FSMContext, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AddTeacherStates.waiting_telegram_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "➕ <b>Add Teacher — Step 1/3</b>\n\n"
        "Enter the teacher's <b>Telegram user ID</b>.\n\n"
        "The teacher can find their ID using @userinfobot.\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )


@router.message(AddTeacherStates.waiting_telegram_id, F.text)
async def admin_add_teacher_telegram_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    if not raw.isdigit():
        await message.answer("⚠️ Telegram user ID must be a number. Please try again.")
        return

    await state.update_data(teacher_telegram_id=int(raw))
    await state.set_state(AddTeacherStates.waiting_employee_id)

    await message.answer(
        "➕ <b>Add Teacher — Step 2/3</b>\n\n"
        "Enter the teacher's <b>Employee ID</b>:\n"
        "Example: <code>EMP-001</code>",
        parse_mode="HTML",
    )


@router.message(AddTeacherStates.waiting_employee_id, F.text)
async def admin_add_teacher_employee_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    ok, result = validate_employee_id(raw)
    if not ok:
        await message.answer(f"⚠️ {result}\n\nPlease try again.")
        return

    await state.update_data(employee_id=result)
    await state.set_state(AddTeacherStates.waiting_first_name)

    await message.answer(
        "➕ <b>Add Teacher — Step 3/3</b>\n\n"
        "Enter the teacher's <b>full name</b>:\n"
        "Example: <code>John Smith</code>",
        parse_mode="HTML",
    )


@router.message(AddTeacherStates.waiting_first_name, F.text)
async def admin_add_teacher_name(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    ok, result = validate_full_name(raw)
    if not ok:
        await message.answer(f"⚠️ {result}\n\nPlease try again.")
        return

    await state.update_data(teacher_name=result)
    data = await state.get_data()
    await state.set_state(AddTeacherStates.confirm)

    from app.bot.keyboards.common import CommonKeyboards
    await message.answer(
        f"📋 <b>Confirm new teacher:</b>\n\n"
        f"👤 Name: <b>{data['teacher_name']}</b>\n"
        f"🪪 Employee ID: <code>{data['employee_id']}</code>\n"
        f"📱 Telegram ID: <code>{data['teacher_telegram_id']}</code>",
        reply_markup=CommonKeyboards.confirm_cancel(
            confirm_data="admin:teacher:add:confirm",
            cancel_data="admin:teacher:add:cancel",
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:teacher:add:confirm", AddTeacherStates.confirm)
async def admin_add_teacher_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        await state.clear()
        return

    await callback.answer()
    data = await state.get_data()
    await state.clear()

    name_parts = data["teacher_name"].split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else None

    svc = AdminService(db_session)
    try:
        teacher = await svc.add_teacher(
            admin=current_user,
            telegram_user_id=data["teacher_telegram_id"],
            employee_id=data["employee_id"],
            first_name=first_name,
            last_name=last_name,
        )
    except ValueError as exc:
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"❌ {exc}",
            reply_markup=AdminKeyboards.main_menu(),
        )
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"✅ <b>Teacher added successfully!</b>\n\n"
        f"Employee ID: <code>{teacher.employee_id}</code>\n"
        f"Name: <b>{data['teacher_name']}</b>",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:teacher:add:cancel")
async def admin_add_teacher_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Cancelled.", reply_markup=AdminKeyboards.main_menu())


# ---------- Deactivate Teacher ----------

@router.callback_query(F.data.startswith("admin:teacher:deactivate:") & ~F.data.contains("confirm"))
async def admin_deactivate_teacher_prompt(
    callback: CallbackQuery, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    teacher_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    await callback.message.edit_text(  # type: ignore[union-attr]
        "⚠️ Are you sure you want to deactivate this teacher?\n"
        "They will lose access immediately.",
        reply_markup=AdminKeyboards.confirm_deactivate("teacher", teacher_id),
    )


@router.callback_query(F.data.startswith("admin:teacher:deactivate:confirm:"))
async def admin_deactivate_teacher_confirm(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    teacher_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    repo = TeacherRepository(db_session)
    teacher = await repo.get_by_id(teacher_id)
    if not teacher:
        await callback.message.answer("❌ Teacher not found.")  # type: ignore[union-attr]
        return

    svc = AdminService(db_session)
    await svc.deactivate_teacher(current_user, teacher)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "🚫 Teacher deactivated successfully.",
        reply_markup=AdminKeyboards.main_menu(),
    )


# ------------------------------------------------------------------ #
# Students                                                              #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "admin:students")
async def admin_students(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    svc = AdminService(db_session)
    students = await svc.list_students(limit=PAGE_SIZE)

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👨‍🎓 <b>Students</b> ({len(students)} shown)",
        reply_markup=AdminKeyboards.student_list(students),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:student:view:"))
async def admin_student_view(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    student_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    repo = StudentRepository(db_session)
    student = await repo.get_by_id(student_id)

    if not student:
        await callback.message.answer("❌ Student not found.")  # type: ignore[union-attr]
        return

    status = "✅ Active" if student.is_active else "🚫 Inactive"
    link = f"<code>{student.telegram_user_id}</code>" if student.telegram_user_id else "⚠️ Not linked"

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👨‍🎓 <b>Student Details</b>\n\n"
        f"👤 Name: <b>{student.full_name}</b>\n"
        f"🪪 Student ID: <code>{student.student_id}</code>\n"
        f"📱 Telegram: {link}\n"
        f"📊 Status: {status}",
        reply_markup=AdminKeyboards.student_actions(student_id),
        parse_mode="HTML",
    )


# ---------- Add Student FSM ----------

@router.callback_query(F.data == "admin:student:add")
async def admin_add_student_start(
    callback: CallbackQuery, state: FSMContext, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AddStudentStates.waiting_student_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "➕ <b>Add Student — Step 1/3</b>\n\n"
        "Enter the student's <b>Student ID</b>:\n"
        "Example: <code>STU-2026-00125</code>\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )


@router.message(AddStudentStates.waiting_student_id, F.text)
async def admin_add_student_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    ok, result = validate_student_id(raw)
    if not ok:
        await message.answer(f"⚠️ {result}\n\nPlease try again.")
        return

    await state.update_data(student_id=result)
    await state.set_state(AddStudentStates.waiting_full_name)

    await message.answer(
        "➕ <b>Add Student — Step 2/3</b>\n\n"
        "Enter the student's <b>full name</b>:",
        parse_mode="HTML",
    )


@router.message(AddStudentStates.waiting_full_name, F.text)
async def admin_add_student_name(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    ok, result = validate_full_name(raw)
    if not ok:
        await message.answer(f"⚠️ {result}\n\nPlease try again.")
        return

    await state.update_data(full_name=result)
    await state.set_state(AddStudentStates.waiting_telegram_id)

    await message.answer(
        "➕ <b>Add Student — Step 3/3</b>\n\n"
        "Enter the student's <b>Telegram user ID</b> to link their account.\n\n"
        "Send <code>skip</code> to register without linking.",
        parse_mode="HTML",
    )


@router.message(AddStudentStates.waiting_telegram_id, F.text)
async def admin_add_student_telegram_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    telegram_user_id: int | None = None
    if raw.lower() != "skip":
        if not raw.isdigit():
            await message.answer("⚠️ Telegram user ID must be a number. Try again or send <code>skip</code>.", parse_mode="HTML")
            return
        telegram_user_id = int(raw)

    await state.update_data(telegram_user_id=telegram_user_id)
    data = await state.get_data()
    await state.set_state(AddStudentStates.confirm)

    tg_display = f"<code>{telegram_user_id}</code>" if telegram_user_id else "Not linked"
    from app.bot.keyboards.common import CommonKeyboards
    await message.answer(
        f"📋 <b>Confirm new student:</b>\n\n"
        f"👤 Name: <b>{data['full_name']}</b>\n"
        f"🪪 Student ID: <code>{data['student_id']}</code>\n"
        f"📱 Telegram: {tg_display}",
        reply_markup=CommonKeyboards.confirm_cancel(
            confirm_data="admin:student:add:confirm",
            cancel_data="admin:student:add:cancel",
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:student:add:confirm", AddStudentStates.confirm)
async def admin_add_student_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        await state.clear()
        return

    await callback.answer()
    data = await state.get_data()
    await state.clear()

    svc = AdminService(db_session)
    try:
        student = await svc.add_student(
            admin=current_user,
            student_id=data["student_id"],
            full_name=data["full_name"],
            telegram_user_id=data.get("telegram_user_id"),
        )
    except ValueError as exc:
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"❌ {exc}",
            reply_markup=AdminKeyboards.main_menu(),
        )
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"✅ <b>Student added successfully!</b>\n\n"
        f"Student ID: <code>{student.student_id}</code>\n"
        f"Name: <b>{student.full_name}</b>",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:student:add:cancel")
async def admin_add_student_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Cancelled.", reply_markup=AdminKeyboards.main_menu())


# ---------- Deactivate Student ----------

@router.callback_query(F.data.startswith("admin:student:deactivate:") & ~F.data.contains("confirm"))
async def admin_deactivate_student_prompt(
    callback: CallbackQuery, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    student_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    await callback.message.edit_text(  # type: ignore[union-attr]
        "⚠️ Are you sure you want to deactivate this student?",
        reply_markup=AdminKeyboards.confirm_deactivate("student", student_id),
    )


@router.callback_query(F.data.startswith("admin:student:deactivate:confirm:"))
async def admin_deactivate_student_confirm(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    student_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    repo = StudentRepository(db_session)
    student = await repo.get_by_id(student_id)
    if not student:
        await callback.message.answer("❌ Student not found.")  # type: ignore[union-attr]
        return

    svc = AdminService(db_session)
    await svc.deactivate_student(current_user, student)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "🚫 Student deactivated successfully.",
        reply_markup=AdminKeyboards.main_menu(),
    )


# ------------------------------------------------------------------ #
# Results management                                                    #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("admin:results"))
async def admin_results(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    """Show paginated list of all results for admin management."""
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    # Parse page from callback: admin:results or admin:results:N
    parts = (callback.data or "").split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    offset = page * PAGE_SIZE

    repo = ResultRepository(db_session)
    results = await repo.get_all(limit=PAGE_SIZE, offset=offset)
    total = await repo.count_total()

    if not results:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "📭 No results found in the system.",
            reply_markup=AdminKeyboards.main_menu(),
        )
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as _select
    from app.database.models.result import Result as _Result
    stmt = (
        _select(_Result)
        .options(
            selectinload(_Result.student),
            selectinload(_Result.subject),
            selectinload(_Result.examination),
        )
        .order_by(_Result.created_at.desc())
        .limit(PAGE_SIZE)
        .offset(offset)
    )
    res = await db_session.execute(stmt)
    results = list(res.scalars().all())

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for r in results:
        student_id = r.student.student_id if r.student else "?"
        subject = r.subject.name if r.subject else "?"
        label = f"📄 {student_id} | {subject}"
        builder.button(text=label, callback_data=f"admin:result:view:{r.id}")
    if page > 0:
        builder.button(text="⬅️ Prev", callback_data=f"admin:results:{page - 1}")
    if page < total_pages - 1:
        builder.button(text="Next ➡️", callback_data=f"admin:results:{page + 1}")
    builder.button(text="⬅️ Back", callback_data="admin:menu")
    builder.adjust(1)

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📊 <b>All Results</b> — Page {page + 1}/{total_pages}\n"
        f"Total: <b>{total}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:result:view:"))
async def admin_result_view(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    """Show a single result with admin actions."""
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    svc = ResultService(db_session)
    try:
        result = await svc.get_by_id(result_id)
    except ResultNotFoundError:
        await callback.message.answer("❌ Result not found.")  # type: ignore[union-attr]
        return

    subject = result.subject.name if result.subject else "N/A"
    exam = result.examination.name if result.examination else "N/A"
    student_id = result.student.student_id if result.student else "—"
    student_name = result.student.full_name if result.student else "—"
    score = f"{result.score}%" if result.score is not None else "—"
    grade = result.grade or "—"
    date = result.created_at.strftime("%Y-%m-%d") if result.created_at else "—"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Delete", callback_data=f"admin:result:delete:{result_id}")
    builder.button(text="⬅️ Back", callback_data="admin:results")
    builder.adjust(2)

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📊 <b>Result</b> #{result_id}\n\n"
        f"🪪 Student: <b>{student_name}</b> (<code>{student_id}</code>)\n"
        f"📚 Subject: <b>{subject}</b>\n"
        f"📝 Exam: <b>{exam}</b>\n"
        f"🎯 Score: <b>{score}</b>\n"
        f"🏅 Grade: <b>{grade}</b>\n"
        f"📅 Date: {date}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:result:delete:") & ~F.data.contains("confirm"))
async def admin_result_delete_prompt(
    callback: CallbackQuery, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes, Delete", callback_data=f"admin:result:delete:confirm:{result_id}")
    builder.button(text="❌ Cancel", callback_data=f"admin:result:view:{result_id}")
    builder.adjust(2)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "⚠️ Are you sure you want to permanently delete this result?\n"
        "This action cannot be undone.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:result:delete:confirm:"))
async def admin_result_delete_confirm(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    svc = ResultService(db_session)
    try:
        await svc.delete_result(current_user, result_id)
    except ResultNotFoundError:
        await callback.message.answer("❌ Result not found.")  # type: ignore[union-attr]
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        "🗑 Result deleted successfully.",
        reply_markup=AdminKeyboards.main_menu(),
    )


# ------------------------------------------------------------------ #
# Link student Telegram                                                 #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("admin:student:link:"))
async def admin_student_link_start(
    callback: CallbackQuery, state: FSMContext, current_user: User
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    student_db_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    await state.update_data(link_student_db_id=student_db_id)
    await state.set_state(LinkStudentStates.waiting_telegram_id)

    await callback.message.answer(  # type: ignore[union-attr]
        "🔗 <b>Link Telegram Account</b>\n\n"
        "Enter the student's Telegram user ID.\n"
        "The student can find it via @userinfobot.\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )


@router.message(LinkStudentStates.waiting_telegram_id, F.text)
async def admin_student_link_receive(
    message: Message, state: FSMContext, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await state.clear()
        return

    raw = (message.text or "").strip()
    if raw.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=AdminKeyboards.main_menu())
        return

    if not raw.isdigit():
        await message.answer("⚠️ Telegram user ID must be a number. Try again or send /cancel.")
        return

    telegram_user_id = int(raw)
    data = await state.get_data()
    student_db_id = data.get("link_student_db_id")
    await state.clear()

    repo = StudentRepository(db_session)
    student = await repo.get_by_id(student_db_id)
    if not student:
        await message.answer("❌ Student not found.", reply_markup=AdminKeyboards.main_menu())
        return

    svc = AdminService(db_session)
    try:
        await svc.link_student_telegram(current_user, student, telegram_user_id)
    except Exception as exc:
        await message.answer(f"❌ Error: {exc}", reply_markup=AdminKeyboards.main_menu())
        return

    await message.answer(
        f"✅ Telegram account <code>{telegram_user_id}</code> linked to "
        f"<b>{student.full_name}</b>.",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Statistics                                                            #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "admin:stats")
async def admin_stats(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    svc = AdminService(db_session)
    stats = await svc.get_statistics()

    await callback.message.edit_text(  # type: ignore[union-attr]
        "📈 <b>System Statistics</b>\n\n"
        f"👨‍🎓 Active Students: <b>{stats['total_students']}</b>\n"
        f"👨‍🏫 Active Teachers: <b>{stats['total_teachers']}</b>\n"
        f"📊 Total Results: <b>{stats['total_results']}</b>",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Audit Logs                                                            #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("admin:audit:"))
async def admin_audit_logs(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_admin(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    page = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    offset = page * PAGE_SIZE

    svc = AdminService(db_session)
    logs = await svc.get_recent_audit_logs(limit=PAGE_SIZE, offset=offset)

    if not logs:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "📋 No audit log entries found.",
            reply_markup=AdminKeyboards.main_menu(),
        )
        return

    lines = [f"📋 <b>Audit Logs</b> — Page {page + 1}\n"]
    for log in logs:
        date = log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "—"
        lines.append(
            f"• [{date}] <b>{log.action}</b> on {log.entity_type}:{log.entity_id} "
            f"by user_id={log.user_id}"
        )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Prev", callback_data=f"admin:audit:{page - 1}")
    builder.button(text="Next ➡️", callback_data=f"admin:audit:{page + 1}")
    builder.button(text="⬅️ Back", callback_data="admin:menu")
    builder.adjust(2, 1)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
