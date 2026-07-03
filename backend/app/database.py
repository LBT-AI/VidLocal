import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create any missing tables. Uses alembic if available, else create_all."""
    alembic_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic")
    alembic_ini = os.path.join(alembic_dir, "alembic.ini")
    if os.path.exists(alembic_ini):
        try:
            from alembic.config import Config
            from alembic import command
            cfg = Config(alembic_ini)
            cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            cfg.set_main_option("script_location", alembic_dir)
            command.upgrade(cfg, "head")
            return
        except Exception:
            logger.warning("Alembic migration failed, falling back to create_all", exc_info=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_engine():
    return engine


def get_async_session():
    return async_session
