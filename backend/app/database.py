import os
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_session_maker = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
            # Celery dùng asyncio.run cho từng task, mỗi lần là một event loop mới.
            # Không giữ connection asyncpg giữa các loop để tránh lỗi "Future attached to a different loop".
            poolclass=NullPool,
        )
    return _engine


def get_session_maker():
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


def dispose_engine():
    """Dispose the async engine. Used after Celery fork to avoid sharing connections."""
    global _engine, _session_maker
    if _engine is not None:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_engine.dispose())
            loop.close()
        except Exception:
            pass
    _engine = None
    _session_maker = None


async def get_db() -> AsyncSession:
    async with get_session_maker()() as session:
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
            app_root = os.path.dirname(os.path.dirname(__file__))
            original_path = list(sys.path)
            sys.path = [path for path in sys.path if os.path.abspath(path or os.getcwd()) != app_root]
            from alembic.config import Config
            from alembic import command
            sys.path = original_path
            cfg = Config(alembic_ini)
            cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            cfg.set_main_option("script_location", alembic_dir)
            command.upgrade(cfg, "head")
            return
        except Exception:
            sys.path = original_path if "original_path" in locals() else sys.path
            logger.warning("Alembic migration failed, falling back to create_all", exc_info=True)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def get_async_session():
    return get_session_maker()
