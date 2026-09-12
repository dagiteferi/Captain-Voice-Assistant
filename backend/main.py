import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.di_container import DIContainer
from config.settings import settings
from adapters.inbound.api.routers import audio, commands, conversations, knowledge

# Configure logging so all INFO+ messages are visible in the console at startup
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

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
    logger.info("=== Captain Voice Assistant startup ===")
    logger.info("Stack: Gemini LLM + Gemini Embeddings + MyMemory Translate + Google TTS")
    container = get_container()

    logger.info("[startup] Initializing database...")
    await container.init_db()
    logger.info("[startup] Database ready.")

    if hasattr(container.translator, "initialize"):
        logger.info("[startup] Initializing translation adapter...")
        await container.translator.initialize()

    logger.info("[startup] All components ready. Serving requests.")
    yield

    logger.info("[shutdown] Closing connections...")
    await container.close()
    logger.info("[shutdown] Done.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def health():
        return JSONResponse({
            "status": "ok",
            "version": "0.1.0",
            "stack": {
                "llm": f"gemini ({settings.gemini_model})",
                "embeddings": "gemini (text-embedding-004)",
                "translation": "mymemory (free)",
                "tts": "google-cloud-tts",
                "vector_store": "chroma",
                "database": "sqlite",
            },
        })

    # Register routers
    app.include_router(commands.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(audio.router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        errors = exc.errors()
        if errors:
            msg = "; ".join([f"{'.'.join(str(l) for l in err.get('loc', []))}: {err.get('msg', 'invalid')}" for err in errors])
        else:
            msg = "Validation error"
        return JSONResponse(
            status_code=422,
            content={"detail": msg},
        )

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
