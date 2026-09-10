"""Dependency injection container for adapters and ports."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from adapters.outbound.events.in_memory_bus import InMemoryBus
from adapters.outbound.llm.ollama_adapter import OllamaAdapter
from adapters.outbound.orchestration.orchestrator_agent import FlatLangGraphOrchestrator
from adapters.outbound.persistence.migrations import create_session_factory, create_sqlite_engine, run_migrations
from adapters.outbound.persistence.sqlite_repository import SQLiteConversationRepository
from adapters.outbound.translation.argos_adapter import ArgosTranslateAdapter
from adapters.outbound.tts.coqui_adapter import CoquiTTSAdapter
from adapters.outbound.vector_store.chroma_adapter import ChromaVectorStoreAdapter
from adapters.outbound.vector_store.sentence_transformer_embedder import SentenceTransformerEmbedder
from application.knowledge.ingest import IngestDocuments


class DIContainer:
    """Central dependency container."""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///./captain.db", chroma_dir: str = "./chroma"):
        self._db_url = db_url
        self._chroma_dir = Path(chroma_dir)
        self._chroma_dir.mkdir(exist_ok=True)

        # Persistence
        self.engine: AsyncEngine = create_sqlite_engine(db_url)
        self.session_factory: async_sessionmaker = create_session_factory(self.engine)
        self.conversation_repository = SQLiteConversationRepository(self.session_factory)

        # Vector store
        embedder = SentenceTransformerEmbedder()
        self.vector_store = ChromaVectorStoreAdapter(self._chroma_dir, embedder)

        # LLM
        self.llm = OllamaAdapter()

        # Translation
        self.translator = ArgosTranslateAdapter()

        # TTS
        self.tts = CoquiTTSAdapter()

        # Event bus
        self.event_bus = InMemoryBus()

        # Orchestrator
        self.orchestrator = FlatLangGraphOrchestrator(
            llm_port=self.llm,
            vector_store_port=self.vector_store,
            translator_port=self.translator,
            tts_port=self.tts,
            event_publisher=self.event_bus,
            repository=self.conversation_repository,
        )

        # Knowledge ingestion
        self.ingest_documents = IngestDocuments(self.vector_store)

    async def init_db(self) -> None:
        """Initialize the database schema."""
        await run_migrations(self.engine)

    async def close(self) -> None:
        """Clean up resources."""
        await self.engine.dispose()

