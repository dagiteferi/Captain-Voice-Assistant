"""Dependency Injection container — wires all adapters from settings."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from adapters.outbound.events.in_memory_bus import InMemoryBus
from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from adapters.outbound.llm.gemini_adapter import GeminiLLMAdapter
from adapters.outbound.orchestration.orchestrator_agent import FlatLangGraphOrchestrator
from adapters.outbound.persistence.migrations import create_session_factory, create_sqlite_engine, run_migrations
from adapters.outbound.persistence.sqlite_repository import SQLiteConversationRepository
from adapters.outbound.translation.mymemory_adapter import MyMemoryTranslateAdapter
from adapters.outbound.translation.resilient_adapter import ResilientTranslator
from adapters.outbound.tts.edge_tts_adapter import EdgeTTSAdapter
from adapters.outbound.tts.google_tts_adapter import GoogleTTSAdapter
from adapters.outbound.vector_store.chroma_adapter import ChromaVectorStoreAdapter
from adapters.outbound.vector_store.gemini_embedder import GeminiEmbedderAdapter
from application.knowledge.ingest import IngestDocuments
from config.settings import settings
from tests.fakes import HashingEmbedder


class DIContainer:
    def __init__(
        self,
        db_url: str | None = None,
        chroma_dir: str | None = None,
        audio_dir: str | None = None,
        embedder: object | None = None,
        llm: object | None = None,
        translator: object | None = None,
        tts: object | None = None,
    ):
        self._db_url = db_url or settings.sqlite_url
        self._chroma_dir = Path(chroma_dir or settings.chroma_dir)
        self._chroma_dir.mkdir(parents=True, exist_ok=True)
        self._audio_dir = Path(audio_dir or settings.audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)

        # Database
        self.engine: AsyncEngine = create_sqlite_engine(self._db_url)
        self.session_factory: async_sessionmaker = create_session_factory(self.engine)
        self.conversation_repository = SQLiteConversationRepository(self.session_factory)

        # Embedder (Gemini Embedding API or override or fallback)
        if embedder is not None:
            self._embedder = embedder
        elif settings.gemini_api_key:
            self._embedder = GeminiEmbedderAdapter(api_key=settings.gemini_api_key)
        else:
            self._embedder = HashingEmbedder()

        # Vector store
        self.vector_store = ChromaVectorStoreAdapter(self._chroma_dir, self._embedder)

        # LLM (Gemini API or override or fallback)
        if llm is not None:
            self.llm = llm
        elif settings.gemini_api_key:
            self.llm = GeminiLLMAdapter(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
        else:
            self.llm = FakeLLMAdapter()

        # Translation (MyMemory or override)
        if translator is not None:
            self.translator = translator
        else:
            self.translator = ResilientTranslator(
                MyMemoryTranslateAdapter(email=settings.mymemory_email),
                llm=self.llm,
            )

        # TTS (Google Cloud TTS API or override or fallback)
        if tts is not None:
            self.tts = tts
        elif settings.google_tts_api_key:
            self.tts = GoogleTTSAdapter(
                api_key=settings.google_tts_api_key,
                voice_en=settings.google_tts_voice_en,
                voice_am=settings.google_tts_voice_am,
            )
        else:
            self.tts = EdgeTTSAdapter()


        # Event bus
        self.event_bus = InMemoryBus()

        # Orchestrator pipeline
        self.orchestrator = FlatLangGraphOrchestrator(
            llm_port=self.llm,
            vector_store_port=self.vector_store,
            translator_port=self.translator,
            tts_port=self.tts,
            event_publisher=self.event_bus,
            repository=self.conversation_repository,
            audio_dir=self._audio_dir,
        )

        # Knowledge ingestion
        self.ingest_documents = IngestDocuments(self.vector_store)

    async def init_db(self) -> None:
        await run_migrations(self.engine)

    async def close(self) -> None:
        await self.engine.dispose()
        if hasattr(self.llm, "aclose"):
            await self.llm.aclose()
        if hasattr(self.translator, "aclose"):
            await self.translator.aclose()
        if hasattr(self.tts, "aclose"):
            await self.tts.aclose()
        if hasattr(self._embedder, "close"):
            self._embedder.close()
