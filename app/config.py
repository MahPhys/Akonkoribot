from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str = "8381976795:AAHTfpY5zGTmgwS2wTjTCelaKKfjE5Jq2Mk"
    CHANNEL_ID: str = "-1004160056658"
    MAIN_CHANNEL_USERNAME: str = "@STrekker"
    ADMIN_USER_IDS: list[int] = [8936968493]
    DATABASE_URL: str = "sqlite+aiosqlite:///archive.db"
    PROXY_URL: str | None = None
    
    SEARCH_PAGE_SIZE: int = 5
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
