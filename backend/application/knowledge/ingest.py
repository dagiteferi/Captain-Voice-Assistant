from typing import Protocol

from domain.knowledge.entities import Chunk, Document
from domain.knowledge.chunking import split_content
from application.ports.vector_store_port import VectorStorePort


class IngestDocuments:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self._vector_store = vector_store

    async def ingest(self, document: Document, raw_text: str) -> list[Chunk]:
        chunks = [
            Chunk(document_id=document.id, content=part)
            for part in split_content(raw_text)
        ]
        for chunk in chunks:
            await self._vector_store.upsert(chunk)
        return chunks
