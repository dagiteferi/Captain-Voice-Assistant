from pathlib import Path
from uuid import UUID

import chromadb

from adapters.outbound.vector_store.embedder import TextEmbedder
from domain.knowledge.entities import Chunk
from domain.knowledge.value_objects import ChunkRef


class ChromaVectorStoreAdapter:
    def __init__(self, persist_dir: str | Path, embedder: TextEmbedder) -> None:
        self._embedder = embedder
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name="knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(self, chunk: Chunk) -> None:
        embedding = self._embedder.embed_texts([chunk.content])[0]
        self._collection.upsert(
            ids=[str(chunk.id)],
            documents=[chunk.content],
            embeddings=[embedding],
            metadatas=[{"document_id": str(chunk.document_id)}],
        )

    async def search(self, query: str, *, limit: int = 5) -> list[ChunkRef]:
        if limit < 1:
            return []
        count = self._collection.count()
        if count == 0:
            return []
        query_embedding = self._embedder.embed_texts([query])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, count),
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        hits: list[ChunkRef] = []
        for chunk_id, content, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            if content is None:
                continue
            document_id = UUID(str(metadata["document_id"]))
            hits.append(
                ChunkRef(
                    chunk_id=UUID(chunk_id),
                    document_id=document_id,
                    content=content,
                    similarity_score=max(0.0, 1.0 - float(distance)),
                )
            )
        return hits
