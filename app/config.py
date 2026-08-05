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