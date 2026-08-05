import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from app.config import settings
from app.database.session import init_db
from app.bot.handlers import user, admin, channel
from app.bot.middlewares import ForceJoinMiddleware
from app.services.indexer import sync_channel_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 شروع و منوی اصلی"),
        BotCommand(command="advanced", description="🎯 جستجوی پیشرفته (رشته و پایه)"),
        BotCommand(command="search", description="🔍 راهنمای جستجوی کتاب"),
        BotCommand(command="calc", description="📊 درصدگیر آزمون (با نمره منفی)"),
        BotCommand(command="feedback", description="💡 ثبت انتقادات و پیشنهادات"),
        BotCommand(command="sync_channel", description="🔄 همگام‌سازی تاریخچه کانال (مدیران)"),
        BotCommand(command="help", description="ℹ️ راهنمای استفاده و کپشن‌نویسی"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands menu registered successfully.")
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

async def main():
    logger.info("Initializing SQLite database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # مدیریت هوشمند پروکسی (تفکیک خودکار ویندوز لوکال از Railway)
    session = None
    proxy = settings.PROXY_URL
    
    # بررسی وجود محیط سرور ابری یا Railway
    is_cloud_env = any([
        os.getenv("RAILWAY_ENVIRONMENT"),
        os.getenv("RAILWAY_SERVICE_ID"),
        os.getenv("RAILWAY_PROJECT_ID"),
        os.getenv("PORT")  # سرورهای ابری معمولا متغیر PORT دارند
    ])
    
    # اگر پروکسی وجود دارد بررسی کن که لوکال نباشد یا روی سرور اجرا نشده باشد
    if proxy and proxy.strip():
        is_local_proxy = "127.0.0.1" in proxy or "localhost" in proxy
        
        if is_cloud_env or is_local_proxy:
            # اگر روی سرور باشیم پروکسی لوکال ۱۲۷ را کلاً نادیده می‌گیریم
            if is_cloud_env:
                logger.info("🌐 Running on Cloud/Railway: Disabling local proxy automatically.")
            else:
                logger.info(f"Connecting to Telegram via Proxy: {proxy}")
                session = AiohttpSession(proxy=proxy)
        else:
            logger.info(f"Connecting to Telegram via Proxy: {proxy}")
            session = AiohttpSession(proxy=proxy)
    else:
        logger.info("Connecting directly to Telegram (No Proxy)...")

    bot = Bot(token=settings.BOT_TOKEN, session=session) if session else Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    @dp.startup()
    async def on_startup(bot: Bot):
        logger.info("🚀 Bot started successfully. Launching background channel history sync task...")
        asyncio.create_task(sync_channel_history(bot))

    # Attach Force Join Middleware to user router
    force_join_mw = ForceJoinMiddleware()
    user.router.message.middleware(force_join_mw)
    user.router.callback_query.middleware(force_join_mw)

    # Include routers
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(channel.router)

    # Register command menu in Telegram
    await setup_bot_commands(bot)

    # Delete existing webhooks to ensure clean polling state
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Cleared pending Telegram updates & webhooks successfully.")
    except Exception as e:
        logger.warning(f"Could not clear webhooks: {e}")

    logger.info("🚀 Bot is running continuously!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")