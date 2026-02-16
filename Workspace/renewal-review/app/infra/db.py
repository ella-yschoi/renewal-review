from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None and settings.db_url:
        _engine = create_async_engine(settings.db_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    global _session_factory
    engine = get_engine()
    if engine is None:
        return None
    if _session_factory is None:
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def init_db():
    engine = get_engine()
    if engine is None:
        return
    import app.infra.db_models  # noqa: F401  — register all models with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
