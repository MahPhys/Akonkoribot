import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    CHANNEL_ID: int
    MAIN_CHANNEL_USERNAME: str = "@STrekker"
    DATABASE_URL: str = "sqlite+aiosqlite:///bot.db"
    
    # پروکسی اختیاری (برای لوکال و ویندوز)
    PROXY_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

# اگر در سرور ابری Railway بودیم، پروکسی را کلاً صفر کن
IS_CLOUD = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT") or os.getenv("RAILWAY_STATIC_URL")

if IS_CLOUD:
    settings.PROXY_URL = None
