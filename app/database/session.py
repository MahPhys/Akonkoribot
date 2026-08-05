from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from ..config import settings
from .models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migrate columns if missing in pre-existing SQLite database
        try:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN file_name VARCHAR(500);"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_active DATETIME;"))
        except Exception:
            pass

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
