from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config.di_container import DIContainer
from config.settings import settings
from adapters.inbound.api.routers import commands, conversations, knowledge


_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get the global DI container."""
    global _container
    if _container is None:
        _container = DIContainer(db_url=settings.sqlite_url)
    return _container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: setup on startup, cleanup on shutdown."""
    container = get_container()
    await container.init_db()
    yield
    await container.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    @app.get("/api/v1/health")
    async def health():
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    # Register routers
    app.include_router(commands.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(knowledge.router, prefix="/api/v1")

    @app.exception_handler(Exception)
    async def exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)

