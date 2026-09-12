from pathlib import Path
from uuid import UUID

import chromadb

from adapters.outbound.vector_store.embedder import TextEmbedder
from application.knowledge.retrieval import lexical_overlap_score
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

    def reset(self) -> None:
        """Drop and recreate the knowledge collection (replaces sample KB)."""
        self._client.delete_collection("knowledge")
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
        # Pull the whole small KB (or a wide candidate set) then rerank.
        # New one-line facts otherwise lose to long CV chunks in vector-only top-5.
        n_results = count if count <= 40 else min(count, max(limit * 5, 20))
        query_embedding = self._embedder.embed_texts([query])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        ranked: list[tuple[float, ChunkRef]] = []
        for chunk_id, content, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            if content is None:
                continue
            document_id = UUID(str(metadata["document_id"]))
            cosine = max(0.0, 1.0 - float(distance))
            lexical = lexical_overlap_score(query, content)
            combined = 0.5 * cosine + 0.5 * min(lexical, 1.0)
            ranked.append(
                (
                    combined,
                    ChunkRef(
                        chunk_id=UUID(chunk_id),
                        document_id=document_id,
                        content=content,
                        similarity_score=combined,
                    ),
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [hit for _, hit in ranked[:limit]]

    async def delete_by_document_id(self, document_id: UUID) -> None:
        """Delete all chunks associated with a document_id from vector store."""
        try:
            self._collection.delete(where={"document_id": str(document_id)})
        except Exception:
            pass

    async def delete_chunk(self, chunk_id: UUID) -> None:
        """Delete a single chunk by chunk_id from vector store."""
        try:
            self._collection.delete(ids=[str(chunk_id)])
        except Exception:
            pass

    async def list_all_chunks(self) -> list[dict]:
        """List all indexed items in the Chroma vector store."""
        count = self._collection.count()
        if count == 0:
            return []
        result = self._collection.get(include=["documents", "metadatas"])
        items = []
        for cid, doc_text, meta in zip(result["ids"], result["documents"], result["metadatas"]):
            items.append({
                "chunk_id": cid,
                "document_id": meta.get("document_id") if meta else None,
                "content": doc_text,
            })
        return items
