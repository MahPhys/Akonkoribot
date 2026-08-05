import datetime
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from sqlalchemy import select, func
from ...database.session import async_session
from ...database.models import Document, User, SearchLog, BookRating, BookComment
from ...services.indexer import sync_channel_history
from ...config import settings

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_USER_IDS

async def generate_stats_report() -> str:
    now = datetime.datetime.utcnow()
    one_day_ago = now - datetime.timedelta(days=1)
    thirty_days_ago = now - datetime.timedelta(days=30)

    async with async_session() as session:
        doc_count = (await session.execute(select(func.count(Document.id)))).scalar() or 0
        total_users = (await session.execute(select(func.count(User.telegram_id)))).scalar() or 0
        
        dau = (await session.execute(select(func.count(User.telegram_id)).where(User.last_active >= one_day_ago))).scalar() or 0
        mau = (await session.execute(select(func.count(User.telegram_id)).where(User.last_active >= thirty_days_ago))).scalar() or 0
        
        search_count = (await session.execute(select(func.count(SearchLog.id)))).scalar() or 0
        likes_count = (await session.execute(select(func.count(BookRating.id)).where(BookRating.is_like == True))).scalar() or 0
        dislikes_count = (await session.execute(select(func.count(BookRating.id)).where(BookRating.is_like == False))).scalar() or 0
        comments_count = (await session.execute(select(func.count(BookComment.id)))).scalar() or 0

        top_searches_res = await session.execute(
            select(SearchLog.query, func.count(SearchLog.id).label("c"))
            .group_by(SearchLog.query)
            .order_by(func.count(SearchLog.id).desc())
            .limit(5)
        )
        top_searches = top_searches_res.all()

    report = (
        "📊 <b>آمار و گزارش جامع سیستم (Akonkoribot)</b>\n\n"
        f"👥 <b>کل کاربران:</b> {total_users:,}\n"
        f"⚡ <b>کاربران فعال روزانه (DAU):</b> {dau:,}\n"
        f"📅 <b>کاربران فعال ماهانه (MAU):</b> {mau:,}\n\n"
        f"📚 <b>تعداد اسناد و کتب آرشیو شده:</b> {doc_count:,}\n"
        f"🔍 <b>تعداد کل جستجوها:</b> {search_count:,}\n"
        f"👍 <b>کل لایک‌ها:</b> {likes_count:,} | 👎 <b>کل دیس‌لایک‌ها:</b> {dislikes_count:,}\n"
        f"💬 <b>تعداد کل نظرات ثبت شده:</b> {comments_count:,}\n\n"
        "🔥 <b>۵ عبارت پرجستجوی اخیر:</b>\n"
    )

    if top_searches:
        for q, count in top_searches:
            report += f"• <code>{q}</code> ({count} بار)\n"
    else:
        report += "<i>هنوز هیچ جستجویی ثبت نشده است.</i>\n"

    report += f"\n🕒 <i>زمان بروزرسانی: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
    return report

@router.message(Command("sync_channel", "sync"))
async def cmd_sync(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.answer(
        "⏳ <b>در حال اسکن و همگام‌سازی کانال ذخیره‌سازی...</b>\n"
        "پیام‌های اسکن‌شده: 0",
        parse_mode="HTML"
    )

    last_update_time = [0.0]

    async def progress_cb(scanned: int, added: int, updated: int):
        import time
        now = time.time()
        if now - last_update_time[0] >= 3.0:
            last_update_time[0] = now
            try:
                await status_msg.edit_text(
                    f"⏳ <b>در حال اسکن و همگام‌سازی کانال ذخیره‌سازی...</b>\n\n"
                    f"🔍 پیام‌های اسکن‌شده: <b>{scanned:,}</b>\n"
                    f"➕ کتاب‌های جدید: <b>{added:,}</b>\n"
                    f"🔄 موارد بروزرسانی‌شده: <b>{updated:,}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    added_count, updated_count = await sync_channel_history(
        bot,
        target_user_id=message.from_user.id,
        progress_callback=progress_cb
    )

    await status_msg.edit_text(
        f"✅ <b>همگام‌سازی کانال با موفقیت کامل شد!</b>\n\n"
        f"➕ کتاب‌های جدید افزوده‌شده: <b>{added_count:,}</b> مورد\n"
        f"🔄 کتاب‌های بروزرسانی‌شده: <b>{updated_count:,}</b> مورد",
        parse_mode="HTML"
    )

@router.message(Command("stats"))
async def cmd_stats(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    report = await generate_stats_report()
    await message.answer(report, parse_mode="HTML")
    
    try:
        if str(message.chat.id) != str(settings.CHANNEL_ID):
            await bot.send_message(chat_id=settings.CHANNEL_ID, text=report, parse_mode="HTML")
    except Exception:
        pass
