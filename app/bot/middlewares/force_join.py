from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings

class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot: Bot = data.get("bot")

        # Determine user & event source
        user: types.User = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)

        # Allow admins to bypass force join
        if user.id in settings.ADMIN_USER_IDS:
            return await handler(event, data)

        # Allow channel posts to bypass force join
        if isinstance(event, types.Message) and event.chat and event.chat.type == "channel":
            return await handler(event, data)

        # Allow check_join callback to be handled
        if isinstance(event, types.CallbackQuery) and event.data == "check_join":
            return await handler(event, data)

        channel_user = settings.MAIN_CHANNEL_USERNAME
        if not channel_user:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(chat_id=channel_user, user_id=user.id)
            if member.status in ["creator", "administrator", "member"]:
                return await handler(event, data)
        except Exception:
            # If bot fails to inspect chat member status, pass through gracefully
            return await handler(event, data)

        # User is not a member, block access
        builder = InlineKeyboardBuilder()
        channel_clean = channel_user.replace("@", "")
        builder.button(text="📢 عضویت در کانال", url=f"https://t.me/{channel_clean}")
        builder.button(text="🔄 بررسی عضویت", callback_data="check_join")
        builder.adjust(1)

        msg_text = (
            "⚠️ <b>عضویت اجباری در کانال</b>\n\n"
            "برای استفاده از امکانات ربات و دریافت فایل‌ها، لطفاً ابتدا در کانال رسمی ما عضو شوید:\n\n"
            f"👉 {channel_user}\n\n"
            "پس از عضویت، روی دکمه <b>«🔄 بررسی عضویت»</b> کلیک کنید."
        )

        if isinstance(event, types.Message):
            await event.answer(msg_text, reply_markup=builder.as_markup(), parse_mode="HTML")
            return None
        elif isinstance(event, types.CallbackQuery):
            await event.answer("⚠️ برای استفاده از ربات باید ابتدا در کانال عضو شوید.", show_alert=True)
            try:
                await event.message.answer(msg_text, reply_markup=builder.as_markup(), parse_mode="HTML")
            except Exception:
                pass
            return None

        return None
