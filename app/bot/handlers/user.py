import html
import re
import datetime
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineQuery, InlineQueryResultArticle, InlineQueryResultCachedDocument, InputTextMessageContent
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update, func, delete
from ...database.session import async_session
from ...database.models import Document, User, Favorite, SearchLog, BookRating, BookComment
from ...services.search_engine import SQLiteSearchEngine
from ...config import settings
from ..keyboards import (
    get_main_menu_markup,
    build_search_results_keyboard,
    build_adv_search_results_keyboard,
    build_file_delivery_keyboard,
)

router = Router()

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()

class CommentStates(StatesGroup):
    waiting_for_comment = State()

def calculate_exam_percentage(correct: int, incorrect: int, total: int) -> dict | None:
    if total <= 0 or correct < 0 or incorrect < 0 or (correct + incorrect) > total:
        return None
    
    unanswered = total - (correct + incorrect)
    raw_score = (correct * 3) - incorrect
    max_score = total * 3
    percentage = (raw_score / max_score) * 100
    
    if percentage >= 80:
        evaluation = "🏆 فوق‌العاده و عالی! سطح تسلط بسیار بالا"
    elif percentage >= 60:
        evaluation = "👏 بسیار خوب! عملکرد قوی در آزمون"
    elif percentage >= 40:
        evaluation = "📈 خوب و متوسط! با مرور نقاط ضعف بهتر می‌شوی"
    elif percentage >= 20:
        evaluation = "⚠️ نیاز به تلاش و تمرین بیشتر"
    else:
        evaluation = "🛑 نیاز به بازخوانی کامل مبحث و تحلیل آزمون"

    return {
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "total": total,
        "raw_score": raw_score,
        "max_score": max_score,
        "percentage": round(percentage, 2),
        "evaluation": evaluation
    }

async def update_user_activity(user_id: int, first_name: str | None = None, username: str | None = None):
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        now = datetime.datetime.utcnow()
        if not user:
            user = User(
                telegram_id=user_id,
                first_name=first_name,
                username=username,
                last_active=now
            )
            session.add(user)
        else:
            user.last_active = now
            if first_name:
                user.first_name = first_name
            if username:
                user.username = username
        await session.commit()

async def get_doc_ratings(session, doc_id: int) -> tuple[int, int]:
    likes_stmt = select(func.count(BookRating.id)).where(BookRating.document_id == doc_id, BookRating.is_like == True)
    dislikes_stmt = select(func.count(BookRating.id)).where(BookRating.document_id == doc_id, BookRating.is_like == False)
    likes = (await session.execute(likes_stmt)).scalar() or 0
    dislikes = (await session.execute(dislikes_stmt)).scalar() or 0
    return likes, dislikes

def get_main_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 جستجوی پیشرفته (رشته و پایه)", callback_data="menu_adv_search")
    builder.button(text="🔍 راهنمای جستجوی کتاب", callback_data="menu_search")
    builder.button(text="📊 درصدگیر آزمون (با نمره منفی)", callback_data="menu_calc")
    builder.button(text="💡 انتقادات و پیشنهادات", callback_data="menu_feedback")
    builder.button(text="⚡ آموزش جستجوی اینلاین (@)", callback_data="menu_inline")
    builder.button(text="ℹ️ راهنمای استفاده و کپشن‌نویسی", callback_data="menu_help")
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()

# --- Cancel Command Handler ---
@router.message(Command("cancel"))
@router.message(F.text.in_(["لغو", "انصراف", "کنسل"]))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("عملیاتی برای لغو وجود ندارد.", reply_markup=get_main_menu_markup())
        return
    await state.clear()
    await message.answer("❌ عملیات با موفقیت لغو شد.", reply_markup=get_main_menu_markup())

# --- Check Force Join Callback ---
@router.callback_query(F.data == "check_join")
async def handle_check_join(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channel_user = settings.MAIN_CHANNEL_USERNAME
    try:
        member = await bot.get_chat_member(chat_id=channel_user, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            await callback.answer("✅ عضویت شما تایید شد! خوش آمدید.", show_alert=True)
            try:
                await callback.message.delete()
            except Exception:
                pass
            await cmd_start(callback.message, bot)
            return
    except Exception:
        pass

    await callback.answer("❌ شما هنوز در کانال عضو نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

# --- Command /start ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)

    welcome_text = (
        f"👋 <b>سلام {html.escape(message.from_user.first_name or 'کاربر')} عزیز!</b>\n\n"
        "به ربات هوشمند آرشیو کتب و منابع کنکوری خوش آمدید.\n\n"
        "🔍 <b>چگونه کتاب پیدا کنم؟</b>\n"
        "کافیست نام کتاب، درس، ناشر یا پایه مورد نظر خود را تایپ و ارسال کنید.\n"
        "📌 <i>مثال:</i> <code>ریاضی دهم</code> یا <code>خیلی سبز</code>\n\n"
        "🎯 <b>جستجوی پیشرفته:</b> برای فیلتر دقیق بر اساس رشته و پایه، دکمه «جستجوی پیشرفته» را بزنید.\n\n"
        "⚡ <b>قابلیت ویژه (جستجوی اینلاین):</b>\n"
        "در هر چت یا گروهی عبارت <code>@Akonkoribot نام کتاب</code> را تایپ کنید!"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Command /search ---
@router.message(Command("search"))
async def cmd_search_help(message: types.Message):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    text = (
        "🔍 <b>راهنمای جستجوی کتاب و منابع:</b>\n\n"
        "برای پیدا کردن منابع کافیست متن یا کلمات کلیدی را مستقیماً ارسال کنید:\n\n"
        "🔹 <b>بر اساس نام درس و پایه:</b> <code>شیمی دوازدهم</code>\n"
        "🔹 <b>بر اساس ناشر:</b> <code>خیلی سبز</code> یا <code>گاج</code>\n"
        "🔹 <b>بر اساس موضوع:</b> <code>حفظیات</code> یا <code>تست جامع</code>\n\n"
        "💡 <i>نکته:</i> هرچه کلمات کلیدی کوتاه و دقیق‌تر باشند، نتایج کامل‌تری دریافت می‌کنید."
    )
    await message.answer(text, reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Command /help ---
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    text = (
        "ℹ️ <b>راهنمای استفاده و کپشن‌نویسی کانال:</b>\n\n"
        "اگر ادمین کانال هستید و می‌خواهید فایل‌های کانال شما عالی ایندکس شوند، کپشن فایل را به یکی از روش‌های زیر بنویسید:\n\n"
        "1️⃣ <b>استفاده از علامت + (سریع‌ترین روش):</b>\n"
        "<code>+حسابان+ +خیلی سبز+ +دوازدهم+ +جامع+</code>\n\n"
        "2️⃣ <b>فرمت کلید و مقدار:</b>\n"
        "عنوان: حسابان جامع خیلی سبز\n"
        "ناشر: خیلی سبز\n"
        "پایه: دوازدهم\n"
        "درس: حسابان\n\n"
        "🆔 <b>پشتیبانی:</b> @STrekker"
    )
    await message.answer(text, reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Command /calc ---
@router.message(Command("calc"))
async def cmd_calc(message: types.Message):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    args = message.text.strip().split()[1:]
    if len(args) == 3 and all(a.isdigit() for a in args):
        c, i, t = int(args[0]), int(args[1]), int(args[2])
        res = calculate_exam_percentage(c, i, t)
        if res:
            text = (
                "📊 <b>کارنامه و نتیجه محاسبه درصد آزمون:</b>\n\n"
                f"✅ <b>تعداد پاسخ درست:</b> {res['correct']}\n"
                f"❌ <b>تعداد پاسخ نادرست:</b> {res['incorrect']}\n"
                f"⚪ <b>تعداد نزده:</b> {res['unanswered']}\n"
                f"📑 <b>تعداد کل سوالات:</b> {res['total']}\n\n"
                f"📉 <b>امتیاز منفی (جریمه):</b> {res['incorrect']}-\n"
                f"🏆 <b>درصد نهایی شما:</b> <code>{res['percentage']}%</code>\n\n"
                f"{res['evaluation']}"
            )
            await message.answer(text, parse_mode="HTML")
            return

    text = (
        "📊 <b>محاسبه‌گر آنلاین درصد آزمون (با قانون ۱/۳ نمره منفی):</b>\n\n"
        "برای محاسبه درصد آزمون خود، به یکی از فرمت‌های زیر پیام بفرستید:\n\n"
        "<b>روش اول (با دستور):</b>\n"
        "<code>/calc 15 3 20</code>\n"
        "(به ترتیب: تعداد درست، تعداد نادرست، تعداد کل سوالات)\n\n"
        "<b>روش دوم (ارسال سه عدد):</b>\n"
        "<code>درصد 15 3 20</code>\n\n"
        "⚖️ <i>فرمول محاسبه:</i> هر ۳ پاسخ غلط، ۱ پاسخ درست را از بین می‌برد."
    )
    await message.answer(text, parse_mode="HTML")

# --- TASK 2: Feedbacks & Suggestions (انتقادات و پیشنهادات) ---
@router.message(Command("feedback"))
@router.message(F.text == "💡 انتقادات و پیشنهادات")
@router.callback_query(F.data == "menu_feedback")
async def start_feedback(event: types.Message | types.CallbackQuery, state: FSMContext):
    user = event.from_user
    await update_user_activity(user.id, user.first_name, user.username)
    await state.set_state(FeedbackStates.waiting_for_feedback)

    prompt_text = (
        "💡 <b>بخش انتقادات و پیشنهادات</b>\n\n"
        "لطفاً نظرات، پیشنهادها یا گزارش مشکلات خود را در قالب یک پیام بنویسید و ارسال کنید.\n"
        "پیام شما مستقیم به مدیران مجموعه ارسال خواهد شد.\n\n"
        "<i>برای انصراف عبارت /cancel یا دکمه «لغو» را ارسال کنید.</i>"
    )

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.answer(prompt_text, parse_mode="HTML")
    else:
        await event.answer(prompt_text, parse_mode="HTML")

@router.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext, bot: Bot):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    
    user_id = message.from_user.id
    full_name = html.escape(message.from_user.full_name or message.from_user.first_name or "نامشخص")
    username = message.from_user.username
    user_feedback_text = html.escape(message.text or message.caption or "بدون متن (فایل/رسانه)")
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    formatted_feedback = (
        "📥 <b>انتقاد / پیشنهاد جدید دریافت شد!</b>\n\n"
        f"👤 <b>فرستنده:</b> <a href=\"tg://user?id={user_id}\">{full_name}</a> (ID: <code>{user_id}</code>)\n"
        f"Username: @{username if username else 'ندارد'}\n"
        f"🕒 <b>زمان ارسال:</b> {now_str}\n\n"
        f"💬 <b>متن پیام:</b>\n"
        f"{user_feedback_text}"
    )

    # Forward or send to CHANNEL_ID
    try:
        await bot.send_message(chat_id=settings.CHANNEL_ID, text=formatted_feedback, parse_mode="HTML")
    except Exception as e:
        # Fallback if parse mode or format error occurs
        await bot.send_message(chat_id=settings.CHANNEL_ID, text=f"📥 پیشنهاد جدید از {user_id}:\n\n{message.text}")

    await state.clear()
    await message.answer(
        "✅ پیام شما با موفقیت ثبت و به مدیران ارسال شد. با تشکر از همراهی شما!",
        reply_markup=get_main_menu_markup()
    )

# --- TASK 3: Advanced Book Search by Grade & Field ---
@router.callback_query(F.data == "menu_adv_search")
@router.message(Command("advanced"))
async def handle_adv_search_menu(event: types.Message | types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="📐 ریاضی (Math)", callback_data="adv_f_math")
    builder.button(text="🧪 تجربی (Experimental)", callback_data="adv_f_exp")
    builder.button(text="📖 انسانی و معارف (Humanities & Islamic)", callback_data="adv_f_hum")
    builder.button(text="🏠 بازگشت به منوی اصلی", callback_data="menu_main")
    builder.adjust(1)

    text = (
        "🎯 <b>جستجوی پیشرفته کتاب‌ها (رشته و پایه):</b>\n\n"
        "لطفاً ابتدا <b>رشته تحصیلی</b> مورد نظر خود را انتخاب کنید:"
    )

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("adv_f_"))
async def handle_adv_field_select(callback: types.CallbackQuery):
    await callback.answer()
    field_code = callback.data.split("_")[2]  # math, exp, hum

    field_names = {
        "math": "📐 ریاضی",
        "exp": "🧪 تجربی",
        "hum": "📖 انسانی و معارف"
    }

    builder = InlineKeyboardBuilder()
    builder.button(text="10️⃣ دهم", callback_data=f"adv_res_{field_code}_10_1")
    builder.button(text="11️⃣ یازدهم", callback_data=f"adv_res_{field_code}_11_1")
    builder.button(text="12️⃣ دوازدهم", callback_data=f"adv_res_{field_code}_12_1")
    builder.button(text="🔙 تغییر رشته", callback_data="menu_adv_search")
    builder.adjust(3, 1)

    text = (
        f"🎯 <b>جستجوی پیشرفته:</b> رشته <b>{field_names.get(field_code, 'انتخابی')}</b>\n\n"
        "اکنون <b>پایه تحصیلی</b> مورد نظر را انتخاب کنید:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("adv_res_"))
async def handle_adv_search_results(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    field_code = parts[2]
    grade_code = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 1

    field_names = {"math": "ریاضی", "exp": "تجربی", "hum": "انسانی و معارف"}
    grade_names = {"10": "دهم", "11": "یازدهم", "12": "دوازدهم"}

    async with async_session() as session:
        docs, total = await SQLiteSearchEngine.search_by_field_and_grade(
            session, field_code=field_code, grade_code=grade_code, page=page, page_size=5
        )

        if not docs and page == 1:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 تغییر پایه / رشته", callback_data=f"adv_f_{field_code}")
            await callback.message.edit_text(
                f"❌ هیچ کتابی برای رشته «<b>{field_names.get(field_code)}</b>» پایه «<b>{grade_names.get(grade_code)}</b>» یافت نشد.",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            return

        text = (
            f"🎯 <b>نتایج جستجوی پیشرفته:</b>\n"
            f"📚 رشته: <b>{field_names.get(field_code)}</b> | 🎓 پایه: <b>{grade_names.get(grade_code)}</b>\n"
            f"📊 کل موارد: {total} مورد (صفحه {page})\n\n"
        )

        for idx, doc in enumerate(docs, 1):
            title = html.escape(doc.title or "بدون عنوان")
            text += f"{idx}. 📖 <b>{title}</b>\n"
            if doc.publisher:
                text += f"🏢 ناشر: {html.escape(doc.publisher)}\n"
            text += f"👁 بازدید: {doc.views} | 📥 دانلود: {doc.downloads}\n\n"

        reply_markup = build_adv_search_results_keyboard(
            docs=docs,
            field_code=field_code,
            grade_code=grade_code,
            page=page,
            total=total
        )

        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")

# --- TASK 4: Book Ratings & Comments System ---
@router.callback_query(F.data.startswith("rate_"))
async def handle_book_rating(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    doc_id = int(parts[1])
    action = parts[2]  # like or dislike
    is_like = (action == "like")
    user_id = callback.from_user.id

    async with async_session() as session:
        # Check existing vote
        stmt = select(BookRating).where(BookRating.user_id == user_id, BookRating.document_id == doc_id)
        res = await session.execute(stmt)
        rating = res.scalar_one_or_none()

        if rating:
            if rating.is_like == is_like:
                # Toggle off
                await session.delete(rating)
                msg = "تغییر رای انجام شد."
            else:
                rating.is_like = is_like
                msg = "رای شما با موفقیت بروزرسانی شد."
        else:
            new_rating = BookRating(user_id=user_id, document_id=doc_id, is_like=is_like)
            session.add(new_rating)
            msg = "با تشکر! رای شما ثبت شد."

        await session.commit()
        likes, dislikes = await get_doc_ratings(session, doc_id)

    await callback.answer(f"{msg}\n👍 {likes} | 👎 {dislikes}", show_alert=False)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=build_file_delivery_keyboard(doc_id, likes, dislikes)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("cmts_"))
async def handle_view_comments(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    doc_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    async with async_session() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
        if not doc:
            await callback.answer("❌ فایل یافت نشد.", show_alert=True)
            return

        stmt = select(BookComment).where(BookComment.document_id == doc_id).order_by(BookComment.created_at.desc())
        all_comments = (await session.execute(stmt)).scalars().all()

        total = len(all_comments)
        page_size = 5
        start = (page - 1) * page_size
        paged = all_comments[start:start + page_size]

        title = html.escape(doc.title or "کتاب")
        text = f"💬 <b>نظرات و دیدگاه‌ها برای:</b> {title}\n📊 <b>تعداد کل نظرات:</b> {total}\n\n"

        if not paged:
            text += "<i>هنوز هیچ نظری برای این کتاب ثبت نشده است. اولین نفری باشید که نظر می‌دهید!</i>"
        else:
            for c in paged:
                date_str = c.created_at.strftime("%Y-%m-%d")
                text += f"👤 <b>{html.escape(c.user_full_name)}</b> ({date_str}):\n{html.escape(c.comment_text)}\n\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="✍️ ثبت نظر جدید", callback_data=f"addcmt_{doc_id}")

        nav = []
        if page > 1:
            nav.append(types.InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"cmts_{doc_id}_{page-1}"))
        if (page * page_size) < total:
            nav.append(types.InlineKeyboardButton(text="بعدی ➡️", callback_data=f"cmts_{doc_id}_{page+1}"))
        if nav:
            builder.row(*nav)

        builder.row(types.InlineKeyboardButton(text="📥 دریافت این فایل", callback_data=f"dl_{doc_id}"))

        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("addcmt_"))
async def handle_start_add_comment(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    doc_id = int(callback.data.split("_")[1])
    await state.set_state(CommentStates.waiting_for_comment)
    await state.update_data(doc_id=doc_id)

    await callback.message.answer(
        "✍️ <b>ثبت دیدگاه جدید:</b>\n\n"
        "لطفاً نظر کوتاه خود را درباره این کتاب بنویسید و ارسال کنید:\n"
        "<i>(برای انصراف عبارت /cancel را بفرستید)</i>",
        parse_mode="HTML"
    )

@router.message(CommentStates.waiting_for_comment)
async def process_add_comment(message: types.Message, state: FSMContext):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    data = await state.get_data()
    doc_id = data.get("doc_id")

    comment_text = message.text.strip() if message.text else ""
    if not comment_text or len(comment_text) < 3:
        await message.answer("⚠️ متن نظر بسیار کوتاه است. لطفاً حداقل چند کلمه بنویسید.")
        return

    user_name = message.from_user.full_name or message.from_user.first_name or "کاربر"

    async with async_session() as session:
        cmt = BookComment(
            user_id=message.from_user.id,
            document_id=doc_id,
            user_full_name=user_name,
            comment_text=comment_text
        )
        session.add(cmt)
        await session.commit()

    await state.clear()
    await message.answer("✅ نظر شما با موفقیت ثبت شد. با تشکر از دیدگاه شما!", reply_markup=get_main_menu_markup())

# --- Menu Callbacks ---
@router.callback_query(F.data == "menu_main")
async def handle_menu_main(callback: types.CallbackQuery, bot: Bot):
    await callback.answer()
    welcome_text = (
        f"👋 <b>سلام {html.escape(callback.from_user.first_name or 'کاربر')} عزیز!</b>\n\n"
        "به منوی اصلی ربات خوش آمدید. گزینه مورد نظر را انتخاب یا عبارت خود را جستجو کنید:"
    )
    await callback.message.edit_text(welcome_text, reply_markup=get_main_menu_markup(), parse_mode="HTML")

@router.callback_query(F.data == "menu_search")
async def handle_menu_search(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_search_help(callback.message)

@router.callback_query(F.data == "menu_calc")
async def handle_menu_calc(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_calc(callback.message)

@router.callback_query(F.data == "menu_help")
async def handle_menu_help(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)

@router.callback_query(F.data == "menu_inline")
async def handle_menu_inline(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "⚡ <b>راهنمای جستجوی اینلاین (@):</b>\n\n"
        "بدون اینکه وارد ربات شوید، در هر چت، گروه یا کانالی عبارت زیر را تایپ کنید:\n\n"
        "<code>@Akonkoribot نام کتاب</code>\n\n"
        "📌 <b>مثال:</b>\n"
        "<code>@Akonkoribot شیمی خیلی سبز</code>\n\n"
        "ربات به صورت لحظه‌ای لیست کتاب‌ها را پیشنهادی می‌آورد و با کلیک روی هر کتاب، فایل آن مستقیم در چت ارسال می‌شود!"
    )
    await callback.message.answer(text, parse_mode="HTML")

# --- Standard Text Search or Calc ---
@router.message(F.text & ~F.text.startswith("/"))
async def handle_search_or_calc(message: types.Message, bot: Bot):
    await update_user_activity(message.from_user.id, message.from_user.first_name, message.from_user.username)
    text_raw = message.text.strip()

    calc_match = re.search(r'^(?:درصد\s+)?(\d+)\s+(\d+)\s+(\d+)$', text_raw)
    if calc_match:
        c, i, t = int(calc_match.group(1)), int(calc_match.group(2)), int(calc_match.group(3))
        res = calculate_exam_percentage(c, i, t)
        if res:
            ans = (
                "📊 <b>کارنامه و نتیجه محاسبه درصد آزمون:</b>\n\n"
                f"✅ <b>تعداد پاسخ درست:</b> {res['correct']}\n"
                f"❌ <b>تعداد پاسخ نادرست:</b> {res['incorrect']}\n"
                f"⚪ <b>تعداد نزده:</b> {res['unanswered']}\n"
                f"📑 <b>تعداد کل سوالات:</b> {res['total']}\n\n"
                f"📉 <b>امتیاز منفی (جریمه):</b> {res['incorrect']}-\n"
                f"🏆 <b>درصد نهایی شما:</b> <code>{res['percentage']}%</code>\n\n"
                f"{res['evaluation']}"
            )
            await message.answer(ans, parse_mode="HTML")
            return

    query = text_raw
    if len(query) < 2:
        await message.answer("⚠️ لطفاً حداقل ۲ حرف برای جستجو وارد کنید.")
        return

    async with async_session() as session:
        log = SearchLog(user_id=message.from_user.id, query=query)
        session.add(log)
        
        docs, total = await SQLiteSearchEngine.search_documents(session, query, page=1, page_size=5)
        log.results_count = total
        await session.commit()

        if total == 0:
            await message.answer(
                f"❌ مدرکی با عبارت «<b>{html.escape(query)}</b>» یافت نشد.\n\n"
                "💡 <i>راهنما:</i> کلمات کلیدی کوتاه‌تر (مثلاً فقط نام درس یا ناشر) را امتحان کنید.",
                parse_mode="HTML"
            )
            return

        text = f"🔎 <b>نتایج جستجو برای:</b> {html.escape(query)}\n📊 <b>تعداد یافت شده:</b> {total} مورد\n\n"

        for idx, doc in enumerate(docs, 1):
            title = html.escape(doc.title or "بدون عنوان")
            text += f"{idx}. 📖 <b>{title}</b>\n"
            
            if doc.publisher or doc.grade:
                meta_parts = []
                if doc.publisher:
                    meta_parts.append(f"🏢 ناشر: {html.escape(doc.publisher)}")
                if doc.grade:
                    meta_parts.append(f"🎓 پایه: {html.escape(doc.grade)}")
                text += " | ".join(meta_parts) + "\n"

            keywords = doc.keywords or []
            if isinstance(keywords, list) and keywords:
                kw_preview = " ".join([f"+{html.escape(str(k))}+" for k in keywords[:6]])
                text += f"🏷 کلمات کلیدی: {kw_preview}\n"
                
            text += f"👁 بازدید: {doc.views} | 📥 دانلود: {doc.downloads}\n\n"

        reply_markup = build_search_results_keyboard(
            docs=docs,
            page=1,
            total=total,
            query=query
        )

        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=reply_markup, parse_mode=None)

# --- Inline Query ---
@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, bot: Bot):
    query = inline_query.query.strip()
    
    async with async_session() as session:
        if not query:
            stmt = select(Document).order_by(Document.views.desc(), Document.id.desc()).limit(15)
            res = await session.execute(stmt)
            docs = res.scalars().all()
        else:
            docs, total = await SQLiteSearchEngine.search_documents(session, query, page=1, page_size=20)

    if not docs:
        no_res_article = InlineQueryResultArticle(
            id="no_res",
            title=f"❌ هیچ کتابی برای «{query}» یافت نشد",
            description="کلمات کلیدی کوتاه‌تر را امتحان کنید.",
            input_message_content=InputTextMessageContent(
                message_text=f"❌ کتابی با عبارت «<b>{html.escape(query)}</b>» یافت نشد.",
                parse_mode="HTML"
            )
        )
        await inline_query.answer([no_res_article], cache_time=1)
        return

    results = []
    for doc in docs:
        caption_text = (
            f"📖 <b>نام:</b> {html.escape(doc.title or 'نامشخص')}\n"
            f"🏢 <b>ناشر:</b> {html.escape(doc.publisher or 'نامشخص')}\n"
            f"🎓 <b>پایه:</b> {html.escape(doc.grade or 'نامشخص')}\n"
            f"📚 <b>درس:</b> {html.escape(doc.subject or 'نامشخص')}\n"
            f"📁 <b>نام فایل:</b> <code>{html.escape(doc.file_name or 'نامشخص')}</code>\n\n"
            "🆔 @Akonkoribot - @STrekker"
        )

        if doc.telegram_file_id:
            try:
                results.append(
                    InlineQueryResultCachedDocument(
                        id=f"doc_{doc.id}",
                        title=f"📖 {doc.title or 'کتاب بدون عنوان'}",
                        document_file_id=doc.telegram_file_id,
                        description=f"🏢 {doc.publisher or 'ناشر نامشخص'} | 🎓 {doc.grade or 'پایه نامشخص'}",
                        caption=caption_text,
                        parse_mode="HTML"
                    )
                )
                continue
            except Exception:
                pass

        builder = InlineKeyboardBuilder()
        builder.button(text="📥 دریافت فایل کتاب", callback_data=f"dl_{doc.id}")
        results.append(
            InlineQueryResultArticle(
                id=str(doc.id),
                title=f"📖 {doc.title or 'کتاب بدون عنوان'}",
                description=f"🏢 {doc.publisher or 'ناشر نامشخص'} | 🎓 {doc.grade or 'پایه نامشخص'}",
                input_message_content=InputTextMessageContent(
                    message_text=caption_text,
                    parse_mode="HTML"
                ),
                reply_markup=builder.as_markup()
            )
        )

    await inline_query.answer(results, cache_time=1)

# --- Download Callback ---
@router.callback_query(F.data.startswith("dl_"))
async def handle_download(callback: types.CallbackQuery, bot: Bot):
    doc_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        stmt = select(Document).where(Document.id == doc_id)
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            await callback.answer("❌ فایل مورد نظر یافت نشد.", show_alert=True)
            return

        doc.downloads += 1
        doc.views += 1
        await session.commit()
        likes, dislikes = await get_doc_ratings(session, doc.id)

        await callback.answer("⏳ در حال ارسال فایل...")
        
        caption_text = (
            f"📖 <b>نام:</b> {html.escape(doc.title or 'نامشخص')}\n"
            f"🏢 <b>ناشر:</b> {html.escape(doc.publisher or 'نامشخص')}\n"
            f"🎓 <b>پایه:</b> {html.escape(doc.grade or 'نامشخص')}\n"
            f"📚 <b>درس:</b> {html.escape(doc.subject or 'نامشخص')}\n"
            f"📁 <b>نام فایل:</b> <code>{html.escape(doc.file_name or 'نامشخص')}</code>\n\n"
            "🆔 @Akonkoribot - @STrekker"
        )

        reply_markup = build_file_delivery_keyboard(doc.id, likes, dislikes)

        try:
            await callback.message.answer_document(
                document=doc.telegram_file_id,
                caption=caption_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer_document(
                document=doc.telegram_file_id,
                caption=caption_text,
                reply_markup=reply_markup,
                parse_mode=None
            )

# --- Pagination Callback ---
@router.callback_query(F.data.startswith("p_"))
async def handle_pagination(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_", 2)
    page = int(parts[1])
    query = parts[2]

    async with async_session() as session:
        docs, total = await SQLiteSearchEngine.search_documents(session, query, page=page, page_size=5)

    if not docs:
        await callback.answer("صفحه دیگری وجود ندارد.", show_alert=True)
        return

    text = f"🔎 <b>نتایج جستجو برای:</b> {html.escape(query)} (صفحه {page})\n📊 <b>کل موارد:</b> {total}\n\n"

    for idx, doc in enumerate(docs, 1):
        title = html.escape(doc.title or "بدون عنوان")
        text += f"{idx}. 📖 <b>{title}</b>\n"
        
        if doc.publisher or doc.grade:
            meta_parts = []
            if doc.publisher:
                meta_parts.append(f"🏢 ناشر: {html.escape(doc.publisher)}")
            if doc.grade:
                meta_parts.append(f"🎓 پایه: {html.escape(doc.grade)}")
            text += " | ".join(meta_parts) + "\n"

        keywords = doc.keywords or []
        if isinstance(keywords, list) and keywords:
            kw_preview = " ".join([f"+{html.escape(str(k))}+" for k in keywords[:6]])
            text += f"🏷 کلمات کلیدی: {kw_preview}\n"

        text += f"👁 بازدید: {doc.views} | 📥 دانلود: {doc.downloads}\n\n"

    reply_markup = build_search_results_keyboard(
        docs=docs,
        page=page,
        total=total,
        query=query
    )

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=None)
