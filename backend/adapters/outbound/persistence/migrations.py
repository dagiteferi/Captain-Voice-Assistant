from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from adapters.outbound.persistence.models import Base


def create_sqlite_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


def _add_missing_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "commands" not in inspector.get_table_names():
        return
    cols = {column["name"] for column in inspector.get_columns("commands")}
    if "voice_id" not in cols:
        sync_conn.execute(text("ALTER TABLE commands ADD COLUMN voice_id VARCHAR(128)"))


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_add_missing_columns)
