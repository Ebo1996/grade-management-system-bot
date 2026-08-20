"""
Teacher handlers.

Covers:
- Teacher main menu
- Multi-step result upload FSM
- My uploads list / detail
- Student search
- Result update / delete (own results only)
"""
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.teacher import TeacherKeyboards
from app.bot.states.result_upload import ResultUploadStates
from app.bot.states.admin_states import TeacherSearchStates, UpdateResultStates
from app.config import get_settings
from app.database.models.user import User, UserRole
from app.schemas.result import ResultUploadData
from app.services.result_service import DuplicateResultError, ResultService
from app.services.teacher_service import TeacherNotFoundError, TeacherService
from app.utils.logger import get_logger
from app.utils.validators import (
    validate_exam_name,
    validate_grade,
    validate_photo_size,
    validate_score,
    validate_student_id,
    validate_subject_name,
)

logger = get_logger(__name__)
router = Router(name="teacher")
_settings = get_settings()

PAGE_SIZE = 10

# FSM data keys
_KEY_UPLOAD = "upload_data"


# ------------------------------------------------------------------ #
# Guards                                                               #
# ------------------------------------------------------------------ #

def _is_teacher(user: User) -> bool:
    return user.role == UserRole.TEACHER and user.is_active


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _confirm_summary(data: ResultUploadData) -> str:
    score_str = f"{data.score}%" if data.score is not None else "—"
    grade_str = data.grade or "—"
    photo_str = "✅ Uploaded" if data.photo_file_id else "❌ Missing"
    return (
        "📋 <b>Please confirm the following result:</b>\n\n"
        f"🪪 Student ID: <code>{data.student_id}</code>\n"
        f"📚 Subject: <b>{data.subject_name}</b>\n"
        f"📝 Exam: <b>{data.exam_name}</b>\n"
        f"🎯 Score: <b>{score_str}</b>\n"
        f"🏅 Grade: <b>{grade_str}</b>\n"
        f"📄 Photo: {photo_str}"
    )


def _format_result(result) -> str:  # type: ignore[no-untyped-def]
    subject = result.subject.name if result.subject else "N/A"
    exam = result.examination.name if result.examination else "N/A"
    score = f"{result.score}%" if result.score is not None else "—"
    grade = result.grade or "—"
    student_id = result.student.student_id if result.student else "—"
    student_name = result.student.full_name if result.student else "—"
    date = result.created_at.strftime("%B %d, %Y") if result.created_at else "—"
    return (
        f"📊 <b>Result</b> #{result.id}\n\n"
        f"🪪 Student: <b>{student_name}</b> (<code>{student_id}</code>)\n"
        f"📚 Subject: <b>{subject}</b>\n"
        f"📝 Exam: <b>{exam}</b>\n"
        f"🎯 Score: <b>{score}</b>\n"
        f"🏅 Grade: <b>{grade}</b>\n"
        f"📅 Uploaded: {date}"
    )


# ------------------------------------------------------------------ #
# Main menu                                                             #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "teacher:menu")
async def teacher_menu(callback: CallbackQuery, current_user: User) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"👨‍🏫 <b>Teacher Panel</b>\n\nWelcome, {current_user.display_name}!",
        reply_markup=TeacherKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Upload result — FSM                                                   #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "teacher:upload")
async def upload_start(
    callback: CallbackQuery, state: FSMContext, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return

    # Verify active teacher profile
    svc = TeacherService(db_session)
    try:
        await svc.get_teacher_profile(current_user)
    except TeacherNotFoundError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer()
    await state.set_state(ResultUploadStates.waiting_student_id)
    await state.update_data({_KEY_UPLOAD: {}})

    await callback.message.answer(  # type: ignore[union-attr]
        "➕ <b>Upload Result — Step 1/6</b>\n\n"
        "Enter the student ID:\n"
        "Example: <code>STU-2026-00125</code>",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_student_id, F.text)
async def upload_receive_student_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    ok, result = validate_student_id(raw)
    if not ok:
        await message.answer(
            f"⚠️ {result}\n\nPlease try again.",
            reply_markup=TeacherKeyboards.cancel_upload(),
        )
        return

    data = await state.get_data()
    upload: dict = data.get(_KEY_UPLOAD, {})
    upload["student_id"] = result  # validated & normalised
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.waiting_subject)

    await message.answer(
        "📚 <b>Step 2/6</b>\n\nEnter the subject name:\n"
        "Example: <code>Mathematics</code>",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_subject, F.text)
async def upload_receive_subject(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    ok, result = validate_subject_name(raw)
    if not ok:
        await message.answer(
            f"⚠️ {result}\n\nPlease try again.",
            reply_markup=TeacherKeyboards.cancel_upload(),
        )
        return

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["subject_name"] = result
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.waiting_exam)

    await message.answer(
        "📝 <b>Step 3/6</b>\n\nEnter the examination name:\n"
        "Example: <code>Final Examination 2026</code>",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_exam, F.text)
async def upload_receive_exam(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    ok, result = validate_exam_name(raw)
    if not ok:
        await message.answer(
            f"⚠️ {result}\n\nPlease try again.",
            reply_markup=TeacherKeyboards.cancel_upload(),
        )
        return

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["exam_name"] = result
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.waiting_score)

    await message.answer(
        "🎯 <b>Step 4/6</b>\n\nEnter the score (0–100):\n"
        "Example: <code>85</code>  or  <code>85.5</code>\n\n"
        "Send <code>skip</code> if no score applies.",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_score, F.text)
async def upload_receive_score(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()

    score: Decimal | None = None
    if raw.lower() != "skip":
        ok, result = validate_score(raw)
        if not ok:
            await message.answer(
                f"⚠️ {result}\n\nPlease try again or send <code>skip</code>.",
                reply_markup=TeacherKeyboards.cancel_upload(),
                parse_mode="HTML",
            )
            return
        score = result  # type: ignore[assignment]

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["score"] = str(score) if score is not None else None
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.waiting_grade)

    await message.answer(
        "🏅 <b>Step 5/6</b>\n\nEnter the grade:\n"
        "Examples: <code>A+</code>, <code>B</code>, <code>PASS</code>, <code>FAIL</code>\n\n"
        "Send <code>skip</code> if no grade applies.",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_grade, F.text)
async def upload_receive_grade(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()

    grade: str | None = None
    if raw.lower() != "skip":
        ok, result = validate_grade(raw)
        if not ok:
            await message.answer(
                f"⚠️ {result}\n\nPlease try again or send <code>skip</code>.",
                reply_markup=TeacherKeyboards.cancel_upload(),
                parse_mode="HTML",
            )
            return
        grade = result  # type: ignore[assignment]

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["grade"] = grade
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.waiting_photo)

    await message.answer(
        "📸 <b>Step 6/6</b>\n\n"
        "Please upload the examination/result sheet photo.\n\n"
        "Send <code>skip</code> to save without a photo.",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_photo, F.photo)
async def upload_receive_photo(message: Message, state: FSMContext) -> None:
    """Handle a photo message in the waiting_photo state."""
    photos: list[PhotoSize] = message.photo or []
    if not photos:
        await message.answer(
            "⚠️ No photo received. Please send a photo.",
            reply_markup=TeacherKeyboards.cancel_upload(),
        )
        return

    # Use the highest resolution version
    best = max(photos, key=lambda p: (p.width or 0) * (p.height or 0))

    # Size check
    if best.file_size:
        ok, err = validate_photo_size(best.file_size, _settings.max_photo_size_bytes)
        if not ok:
            await message.answer(
                f"⚠️ {err}\n\nPlease upload a smaller photo.",
                reply_markup=TeacherKeyboards.cancel_upload(),
            )
            return

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["photo_file_id"] = best.file_id
    upload["photo_unique_id"] = best.file_unique_id
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.confirm_result)

    # Build confirmation summary
    upload_data = ResultUploadData(
        student_id=upload["student_id"],
        subject_name=upload["subject_name"],
        exam_name=upload["exam_name"],
        score=Decimal(upload["score"]) if upload.get("score") else None,
        grade=upload.get("grade"),
        remarks=upload.get("remarks"),
        photo_file_id=upload.get("photo_file_id"),
        photo_unique_id=upload.get("photo_unique_id"),
    )

    await message.answer(
        _confirm_summary(upload_data),
        reply_markup=TeacherKeyboards.upload_confirm(),
        parse_mode="HTML",
    )


@router.message(ResultUploadStates.waiting_photo, F.text)
async def upload_skip_photo(message: Message, state: FSMContext) -> None:
    """Allow skipping the photo step."""
    if (message.text or "").strip().lower() != "skip":
        await message.answer(
            "Please send a photo, or send <code>skip</code> to proceed without one.",
            reply_markup=TeacherKeyboards.cancel_upload(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})
    upload["photo_file_id"] = None
    upload["photo_unique_id"] = None
    await state.update_data({_KEY_UPLOAD: upload})
    await state.set_state(ResultUploadStates.confirm_result)

    upload_data = ResultUploadData(
        student_id=upload["student_id"],
        subject_name=upload["subject_name"],
        exam_name=upload["exam_name"],
        score=Decimal(upload["score"]) if upload.get("score") else None,
        grade=upload.get("grade"),
        remarks=upload.get("remarks"),
        photo_file_id=None,
        photo_unique_id=None,
    )

    await message.answer(
        _confirm_summary(upload_data),
        reply_markup=TeacherKeyboards.upload_confirm(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Confirm / Edit / Cancel                                               #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "teacher:upload:confirm", ResultUploadStates.confirm_result)
async def upload_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        await state.clear()
        return

    await callback.answer()
    data = await state.get_data()
    upload = data.get(_KEY_UPLOAD, {})

    upload_data = ResultUploadData(
        student_id=upload["student_id"],
        subject_name=upload["subject_name"],
        exam_name=upload["exam_name"],
        score=Decimal(upload["score"]) if upload.get("score") else None,
        grade=upload.get("grade"),
        remarks=upload.get("remarks"),
        photo_file_id=upload.get("photo_file_id"),
        photo_unique_id=upload.get("photo_unique_id"),
    )

    service = ResultService(db_session)
    try:
        result = await service.create_result(
            uploader=current_user,
            student_id_str=upload_data.student_id,
            subject_name=upload_data.subject_name,
            exam_name=upload_data.exam_name,
            score=upload_data.score,
            grade=upload_data.grade,
            remarks=upload_data.remarks,
            photo_file_id=upload_data.photo_file_id,
            photo_unique_id=upload_data.photo_unique_id,
        )
    except DuplicateResultError as exc:
        await state.clear()
        await callback.message.edit_text(  # type: ignore[union-attr]
            "⚠️ <b>Duplicate Result Detected</b>\n\n"
            "A result already exists for this student, subject, and examination.\n"
            "Would you like to update it instead?",
            reply_markup=TeacherKeyboards.duplicate_result_options(exc.existing_result.id),
            parse_mode="HTML",
        )
        return
    except ValueError as exc:
        await state.clear()
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"❌ <b>Error:</b> {exc}\n\nPlease try again.",
            reply_markup=TeacherKeyboards.main_menu(),
            parse_mode="HTML",
        )
        return

    await state.clear()
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"✅ <b>Result saved successfully!</b>\n\n"
        f"Result ID: #{result.id}\n"
        f"Student: <code>{upload_data.student_id}</code>\n"
        f"Subject: <b>{upload_data.subject_name}</b>",
        reply_markup=TeacherKeyboards.main_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "teacher:upload:edit", ResultUploadStates.confirm_result)
async def upload_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Restart the upload from the beginning."""
    await callback.answer()
    await state.set_state(ResultUploadStates.waiting_student_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "✏️ Let's start over.\n\n"
        "➕ <b>Upload Result — Step 1/6</b>\n\n"
        "Enter the student ID:",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "teacher:upload:cancel")
async def upload_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the upload at any step."""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(  # type: ignore[union-attr]
        "❌ Upload cancelled.",
        reply_markup=TeacherKeyboards.main_menu(),
    )


# ------------------------------------------------------------------ #
# My Uploads                                                            #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("teacher:my_results:"))
async def teacher_my_results(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    page = int(callback.data.split(":")[-1])  # type: ignore[union-attr]
    offset = page * PAGE_SIZE

    svc = TeacherService(db_session)
    try:
        teacher = await svc.get_teacher_profile(current_user)
    except TeacherNotFoundError as exc:
        await callback.message.answer(str(exc))  # type: ignore[union-attr]
        return

    results = await svc.get_uploaded_results(teacher, limit=PAGE_SIZE, offset=offset)

    if not results:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "📭 You have not uploaded any results yet.",
            reply_markup=TeacherKeyboards.main_menu(),
        )
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📋 <b>My Uploads</b> — Page {page + 1}\n\nSelect a result:",
        reply_markup=TeacherKeyboards.result_list(results),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Result detail (teacher view)                                          #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("teacher:result:") & ~F.data.contains("update") & ~F.data.contains("delete"))
async def teacher_result_detail(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    rs = ResultService(db_session)
    ts = TeacherService(db_session)
    try:
        result = await rs.get_by_id(result_id)
        teacher = await ts.get_teacher_profile(current_user)
        can_modify = await ts.can_modify_result(teacher, result)
    except Exception:
        await callback.message.answer("❌ Result not found.")  # type: ignore[union-attr]
        return

    await callback.message.answer(  # type: ignore[union-attr]
        _format_result(result),
        reply_markup=TeacherKeyboards.result_actions(
            result_id, can_edit=can_modify, can_delete=can_modify
        ),
        parse_mode="HTML",
    )

    if result.photo_file_id:
        await callback.message.answer_photo(  # type: ignore[union-attr]
            photo=result.photo_file_id,
            caption="📄 Examination Sheet",
        )


# ------------------------------------------------------------------ #
# Delete result                                                         #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("teacher:result:delete:"))
async def teacher_delete_result(
    callback: CallbackQuery, current_user: User, db_session: AsyncSession
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    rs = ResultService(db_session)
    ts = TeacherService(db_session)
    try:
        result = await rs.get_by_id(result_id)
        teacher = await ts.get_teacher_profile(current_user)
        if not await ts.can_modify_result(teacher, result):
            await callback.message.answer("🚫 You can only delete your own uploads.")  # type: ignore[union-attr]
            return
        await rs.delete_result(current_user, result_id)
    except Exception as exc:
        await callback.message.answer(f"❌ Error: {exc}")  # type: ignore[union-attr]
        return

    await callback.message.edit_text(  # type: ignore[union-attr]
        "🗑 Result deleted successfully.",
        reply_markup=TeacherKeyboards.main_menu(),
    )


# ------------------------------------------------------------------ #
# Update result FSM                                                     #
# ------------------------------------------------------------------ #

@router.callback_query(F.data.startswith("teacher:result:update:"))
async def teacher_update_result_start(
    callback: CallbackQuery,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    """Start the update-result flow — ask for new score."""
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return

    result_id = int(callback.data.split(":")[-1])  # type: ignore[union-attr]

    rs = ResultService(db_session)
    ts = TeacherService(db_session)
    try:
        result = await rs.get_by_id(result_id)
        teacher = await ts.get_teacher_profile(current_user)
        if not await ts.can_modify_result(teacher, result):
            await callback.answer("🚫 You can only update your own uploads.", show_alert=True)
            return
    except Exception as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer()
    await state.set_state(UpdateResultStates.waiting_score)
    await state.update_data(update_result_id=result_id)

    current_score = f"{result.score}%" if result.score is not None else "—"
    current_grade = result.grade or "—"

    await callback.message.answer(  # type: ignore[union-attr]
        f"✏️ <b>Update Result</b> #{result_id}\n\n"
        f"Current score: <b>{current_score}</b>\n"
        f"Current grade: <b>{current_grade}</b>\n\n"
        "Enter new score (0-100), or send <code>skip</code> to keep current:",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(UpdateResultStates.waiting_score, F.text)
async def teacher_update_receive_score(
    message: Message,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    """Receive new score for update flow."""
    from app.utils.validators import validate_score as _validate_score
    from decimal import Decimal

    if not _is_teacher(current_user):
        await state.clear()
        return

    raw = (message.text or "").strip()

    score: Decimal | None = None
    if raw.lower() != "skip":
        ok, result = _validate_score(raw)
        if not ok:
            await message.answer(
                f"⚠️ {result}\n\nPlease try again or send <code>skip</code>.",
                reply_markup=TeacherKeyboards.cancel_upload(),
                parse_mode="HTML",
            )
            return
        score = result  # type: ignore[assignment]

    await state.update_data(update_score=str(score) if score is not None else None)
    await state.set_state(UpdateResultStates.waiting_grade)

    await message.answer(
        "🏅 Enter new grade, or send <code>skip</code> to keep current:",
        reply_markup=TeacherKeyboards.cancel_upload(),
        parse_mode="HTML",
    )


@router.message(UpdateResultStates.waiting_grade, F.text)
async def teacher_update_receive_grade(
    message: Message,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    """Receive new grade and save the update."""
    from app.utils.validators import validate_grade as _validate_grade
    from decimal import Decimal

    if not _is_teacher(current_user):
        await state.clear()
        return

    raw = (message.text or "").strip()

    grade: str | None = None
    if raw.lower() != "skip":
        ok, result = _validate_grade(raw)
        if not ok:
            await message.answer(
                f"⚠️ {result}\n\nPlease try again or send <code>skip</code>.",
                reply_markup=TeacherKeyboards.cancel_upload(),
                parse_mode="HTML",
            )
            return
        grade = result  # type: ignore[assignment]

    data = await state.get_data()
    result_id = data.get("update_result_id")
    score_str = data.get("update_score")
    score = Decimal(score_str) if score_str else None
    await state.clear()

    rs = ResultService(db_session)
    try:
        updated = await rs.update_result(
            uploader=current_user,
            result_id=result_id,
            score=score,
            grade=grade,
        )
    except Exception as exc:
        await message.answer(
            f"❌ Error updating result: {exc}",
            reply_markup=TeacherKeyboards.main_menu(),
        )
        return

    new_score = f"{updated.score}%" if updated.score is not None else "—"
    new_grade = updated.grade or "—"

    await message.answer(
        f"✅ <b>Result updated!</b>\n\n"
        f"Result ID: #{updated.id}\n"
        f"New score: <b>{new_score}</b>\n"
        f"New grade: <b>{new_grade}</b>",
        reply_markup=TeacherKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Search                                                                #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "teacher:search")
async def teacher_search_start(
    callback: CallbackQuery, state: FSMContext, current_user: User
) -> None:
    if not _is_teacher(current_user):
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(TeacherSearchStates.waiting_query)
    await callback.message.answer(  # type: ignore[union-attr]
        "🔎 <b>Search Student</b>\n\n"
        "Enter a student name or student ID:",
        parse_mode="HTML",
    )


@router.message(TeacherSearchStates.waiting_query, F.text)
async def teacher_search_receive(
    message: Message,
    state: FSMContext,
    current_user: User,
    db_session: AsyncSession,
) -> None:
    if not _is_teacher(current_user):
        await state.clear()
        return

    query = (message.text or "").strip()
    await state.clear()

    svc = TeacherService(db_session)
    students = await svc.search_student(query)

    if not students:
        await message.answer(
            f"❌ No students found matching '<b>{query}</b>'.",
            reply_markup=TeacherKeyboards.main_menu(),
            parse_mode="HTML",
        )
        return

    lines = [f"🔎 Found <b>{len(students)}</b> student(s):\n"]
    for s in students:
        link = "✅ Linked" if s.telegram_user_id else "⚠️ Not linked"
        lines.append(f"• <b>{s.full_name}</b> — <code>{s.student_id}</code> ({link})")

    await message.answer(
        "\n".join(lines),
        reply_markup=TeacherKeyboards.main_menu(),
        parse_mode="HTML",
    )


# ------------------------------------------------------------------ #
# Help                                                                  #
# ------------------------------------------------------------------ #

@router.callback_query(F.data == "teacher:help")
async def teacher_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(  # type: ignore[union-attr]
        "❓ <b>Teacher Help</b>\n\n"
        "➕ <b>Upload Result</b> — Follow the steps to upload a result for a student\n"
        "📋 <b>My Uploads</b> — Browse results you have uploaded\n"
        "🔎 <b>Search Student</b> — Find a student by name or ID\n\n"
        "Use /start to return to the main menu.",
        reply_markup=TeacherKeyboards.main_menu(),
        parse_mode="HTML",
    )
