import re
import asyncio
from aiogram import Router, F, types, Bot
from sqlalchemy import select
from ...database.session import async_session
from ...database.models import User
from ...services.indexer import ChannelIndexer, sync_channel_history
from ...config import settings
from .admin import generate_stats_report

router = Router()

def extract_file_info(message: types.Message):
    caption = message.caption or message.text or ""
    if message.document:
        doc = message.document
        return doc.file_id, doc.file_unique_id, doc.file_name or "document", doc.file_size, caption
    elif message.audio:
        aud = message.audio
        name = aud.file_name or f"{aud.title or 'audio'}.mp3"
        return aud.file_id, aud.file_unique_id, name, aud.file_size, caption
    elif message.video:
        vid = message.video
        name = vid.file_name or f"video_{vid.file_unique_id}.mp4"
        return vid.file_id, vid.file_unique_id, name, vid.file_size, caption
    elif message.photo:
        ph = message.photo[-1]
        name = f"photo_{ph.file_unique_id}.jpg"
        return ph.file_id, ph.file_unique_id, name, ph.file_size, caption
    return None

async def process_channel_message(message: types.Message):
    info = extract_file_info(message)
    if not info:
        return
    
    file_id, file_unique_id, file_name, file_size, caption = info
    async with async_session() as session:
        await ChannelIndexer.index_message(
            session=session,
            message_id=message.message_id,
            channel_id=str(message.chat.id),
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_name=file_name,
            caption=caption,
            file_size=file_size
        )

async def handle_channel_broadcast(message: types.Message, bot: Bot) -> bool:
    text_or_caption = message.caption or message.text or ""
    if not ("#BROADCAST" in text_or_caption or "#ارسال_همگانی" in text_or_caption or "#broadcast" in text_or_caption):
        return False

    status_msg = await bot.send_message(
        chat_id=message.chat.id,
        text="📢 <b>پیام همگانی شناسایی شد! در حال آماده‌سازی و ارسال به کاربران...</b>",
        parse_mode="HTML"
    )

    clean_text = re.sub(r'#(?:BROADCAST|ارسال_همگانی|broadcast)', '', text_or_caption, flags=re.IGNORECASE).strip()

    async with async_session() as session:
        users = (await session.execute(select(User.telegram_id))).scalars().all()

    total_users = len(users)
    success = 0
    failed = 0

    for uid in users:
        try:
            if message.document or message.photo or message.video or message.audio:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=clean_text if clean_text else None,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=clean_text,
                    parse_mode="HTML"
                )
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    report = (
        "📢 <b>گزارش ارسال پیام همگانی:</b>\n\n"
        f"✅ <b>ارسال موفق:</b> {success:,} کاربر\n"
        f"❌ <b>ناموفق (بلاک/غیرفعال):</b> {failed:,} کاربر\n"
        f"📊 <b>مجموع کل کاربران:</b> {total_users:,} کاربر"
    )

    await status_msg.edit_text(report, parse_mode="HTML")
    return True

@router.channel_post()
async def handle_channel_post(message: types.Message, bot: Bot):
    text_or_caption = message.caption or message.text or ""
    
    if "#STATS" in text_or_caption or "#آمار" in text_or_caption or text_or_caption.strip() == "/stats":
        rep = await generate_stats_report()
        await bot.send_message(chat_id=message.chat.id, text=rep, parse_mode="HTML")
        return

    if "#SYNC" in text_or_caption or "#همگام_سازی" in text_or_caption or text_or_caption.strip() in ["/sync", "/sync_channel"]:
        status_msg = await bot.send_message(
            chat_id=message.chat.id,
            text="⏳ <b>در حال اسکن و همگام‌سازی کانال ذخیره‌سازی...</b>\nپیام‌های اسکن‌شده: 0",
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
                        f"➕ جدید: <b>{added:,}</b> | 🔄 بروزرسانی: <b>{updated:,}</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        added_count, updated_count = await sync_channel_history(
            bot,
            target_user_id=None,
            progress_callback=progress_cb
        )
        await status_msg.edit_text(
            f"✅ <b>همگام‌سازی کانال با موفقیت کامل شد!</b>\n\n"
            f"➕ کتاب‌های جدید افزوده‌شده: <b>{added_count:,}</b> مورد\n"
            f"🔄 کتاب‌های بروزرسانی‌شده: <b>{updated_count:,}</b> مورد",
            parse_mode="HTML"
        )
        return

    is_broadcast = await handle_channel_broadcast(message, bot)
    if is_broadcast:
        return

    if message.document or message.photo or message.video or message.audio:
        await process_channel_message(message)

@router.edited_channel_post()
async def handle_edited_channel_post(message: types.Message, bot: Bot):
    if message.document or message.photo or message.video or message.audio:
        await process_channel_message(message)
