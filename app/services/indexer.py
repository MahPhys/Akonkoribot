import re
import logging
import asyncio
from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.models import Document
from ..database.session import async_session
from .search_engine import normalize_persian
from ..config import settings

logger = logging.getLogger(__name__)

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

class ChannelIndexer:
    @staticmethod
    def parse_caption(caption: str) -> dict:
        """
        Parses Telegram caption with support for:
        1) Keywords enclosed in + (e.g. +حسابان+ +خیلی سبز+ +دوازدهم+)
        2) Key-value pairs (Title: ..., Publisher: ...)
        3) Plain caption text lines
        """
        if not caption:
            return {}

        data = {}
        
        # Extract all phrases inside +...(+)
        # Handles both +کلمه+ and +کلمه1+کلمه2+
        plus_keywords = [k.strip() for k in re.findall(r'\+([^+]+)', caption) if k.strip()]
        data['keywords'] = plus_keywords

        lines = [l.strip() for l in caption.split('\n') if l.strip()]
        for line in lines:
            if ':' in line:
                key, val = line.split(':', 1)
                key_clean = key.strip().lower()
                val_clean = val.strip()

                if key_clean in ['عنوان', 'title', 'نام کتاب']:
                    data['title'] = val_clean
                elif key_clean in ['ناشر', 'انتشارات', 'publisher']:
                    data['publisher'] = val_clean
                elif key_clean in ['درس', 'موضوع', 'ماده', 'subject']:
                    data['subject'] = val_clean
                elif key_clean in ['پایه', 'کلاس', 'مقطع', 'grade']:
                    data['grade'] = val_clean
                elif key_clean in ['سال', 'سال چاپ', 'year']:
                    data['year'] = val_clean
                elif key_clean in ['نویسنده', 'مولف', 'authors']:
                    data['authors'] = val_clean

        # If no explicit title key was found, derive title from caption first
        if not data.get('title'):
            if plus_keywords:
                # Use top plus tags as clean title
                data['title'] = " | ".join(plus_keywords[:3])
            elif lines:
                # Use first line of caption
                data['title'] = lines[0]

        return data

    @staticmethod
    async def index_message(
        session: AsyncSession,
        message_id: int,
        channel_id: str,
        file_id: str,
        file_unique_id: str,
        file_name: str | None,
        caption: str | None,
        file_size: int | None = None
    ) -> tuple[Document, bool]:
        parsed = ChannelIndexer.parse_caption(caption or "")
        
        # Caption is strictly prioritized over file_name
        raw_title = parsed.get("title") or (caption.strip().split('\n')[0] if caption and caption.strip() else None) or file_name or "سند بدون عنوان"
        norm_title = normalize_persian(raw_title)

        stmt = select(Document).where(Document.file_unique_id == file_unique_id)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        formatted_size = f"{round(file_size / (1024 * 1024), 2)} MB" if file_size else None
        extracted_keywords = parsed.get("keywords", [])

        if existing:
            existing.telegram_file_id = file_id
            existing.message_id = message_id
            existing.title = raw_title
            existing.normalized_title = norm_title
            existing.publisher = parsed.get("publisher") or existing.publisher
            existing.subject = parsed.get("subject") or existing.subject
            existing.grade = parsed.get("grade") or existing.grade
            existing.year = parsed.get("year") or existing.year
            existing.authors = parsed.get("authors") or existing.authors
            existing.keywords = extracted_keywords if extracted_keywords else existing.keywords
            existing.file_name = file_name or existing.file_name
            existing.description = caption
            if formatted_size:
                existing.file_size = formatted_size
            await session.commit()
            return existing, False
        else:
            new_doc = Document(
                telegram_file_id=file_id,
                file_unique_id=file_unique_id,
                message_id=message_id,
                channel_id=str(channel_id),
                title=raw_title,
                normalized_title=norm_title,
                publisher=parsed.get("publisher"),
                subject=parsed.get("subject"),
                grade=parsed.get("grade"),
                year=parsed.get("year"),
                authors=parsed.get("authors"),
                keywords=extracted_keywords,
                file_name=file_name,
                description=caption,
                file_size=formatted_size
            )
            session.add(new_doc)
            await session.commit()
            return new_doc, True


async def sync_channel_history(
    bot: Bot,
    target_user_id: int | None = None,
    progress_callback = None
) -> tuple[int, int]:
    """
    Scans and indexes all historical messages from CHANNEL_ID.
    Returns (added_count, updated_count).
    """
    channel_id = settings.CHANNEL_ID
    if not channel_id or str(channel_id) in ["0", ""]:
        logger.warning("No CHANNEL_ID configured for history sync.")
        return 0, 0

    target_chat_id = target_user_id or (settings.ADMIN_USER_IDS[0] if settings.ADMIN_USER_IDS else None) or channel_id

    logger.info(f"🔄 Starting historical channel post sync for channel {channel_id}...")

    # Find highest message_id in database
    async with async_session() as session:
        res = await session.execute(select(func.max(Document.message_id)).where(Document.channel_id == str(channel_id)))
        max_id = res.scalar() or 0

    msg_id = 1
    added_count = 0
    updated_count = 0
    scanned_count = 0
    consecutive_not_found = 0

    while True:
        try:
            try:
                fwd = await bot.forward_message(
                    chat_id=target_chat_id,
                    from_chat_id=channel_id,
                    message_id=msg_id
                )
            except (TelegramBadRequest, Exception) as fwd_err:
                # If target_chat_id failed, fallback to forwarding to channel_id itself
                if target_chat_id != channel_id:
                    target_chat_id = channel_id
                    fwd = await bot.forward_message(
                        chat_id=target_chat_id,
                        from_chat_id=channel_id,
                        message_id=msg_id
                    )
                else:
                    raise fwd_err

            # Instantly delete temp forwarded message
            try:
                await bot.delete_message(chat_id=target_chat_id, message_id=fwd.message_id)
            except Exception:
                pass

            scanned_count += 1
            info = extract_file_info(fwd)
            if info:
                file_id, file_unique_id, file_name, file_size, caption = info
                async with async_session() as session:
                    _, created = await ChannelIndexer.index_message(
                        session=session,
                        message_id=msg_id,
                        channel_id=str(channel_id),
                        file_id=file_id,
                        file_unique_id=file_unique_id,
                        file_name=file_name,
                        caption=caption,
                        file_size=file_size
                    )
                    if created:
                        added_count += 1
                    else:
                        updated_count += 1

            consecutive_not_found = 0

            if progress_callback:
                try:
                    await progress_callback(scanned_count, added_count, updated_count)
                except Exception:
                    pass

            msg_id += 1
            await asyncio.sleep(0.08)

        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramBadRequest:
            consecutive_not_found += 1
            if consecutive_not_found >= 30 and msg_id > max_id:
                break
            msg_id += 1
        except Exception as e:
            logger.warning(f"Sync msg #{msg_id} error: {e}")
            consecutive_not_found += 1
            if consecutive_not_found >= 30 and msg_id > max_id:
                break
            msg_id += 1

    logger.info(f"✅ Channel history sync complete. Added: {added_count}, Updated: {updated_count}")
    return added_count, updated_count


