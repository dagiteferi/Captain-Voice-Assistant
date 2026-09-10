from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from adapters.outbound.persistence.models import Base


def create_sqlite_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
