"""Google Gemini Embedding adapter — uses Gemini Embedding REST API (free tier).

Replaces sentence-transformers (local model download) with the Gemini API.
Same GEMINI_API_KEY as the LLM adapter.
Model: text-embedding-004 (768 dims, free tier)
"""

from __future__ import annotations

import logging
from collections import OrderedDict

import httpx

from adapters.outbound.vector_store.embedder import TextEmbedder

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Bounded so a long session cannot grow it without limit.
CACHE_SIZE = 512

# A 403 here means the key itself was rejected, not the request.
SUSPENDED_KEY_HINT = (
    "the Gemini API key has been suspended. Create a new key at https://aistudio.google.com/apikey (or resolve the suspension on the Google Cloud project) and set GEMINI_API_KEY."
)


class GeminiEmbedderAdapter(TextEmbedder):
    """Text embedder via Gemini Embedding API — no local install needed."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> None:
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Get a free key at https://ai.google.dev/"
            )
        self._api_key = api_key
        self._model = model
        self._task_type = task_type
        # Sync client for embed_texts (Chroma calls this synchronously)
        self._client = httpx.Client(timeout=30.0)
        # Each embedding is a billed request, and the same question gets asked
        # again constantly during a demo. Remember what we have already spent.
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts synchronously (Chroma interface)."""
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for text in texts:
            embedding = self._embed_one(text)
            embeddings.append(embedding)
        return embeddings

    def _embed_one(self, text: str) -> list[float]:
        cached = self._cache.get(text)
        if cached is not None:
            self._cache.move_to_end(text)
            logger.debug("[gemini-embed] cache hit (%d cached)", len(self._cache))
            return cached

        values = self._request_embedding(text)
        self._cache[text] = values
        if len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return values

    def _request_embedding(self, text: str) -> list[float]:
        url = (
            f"{GEMINI_API_BASE}/models/{self._model}:embedContent"
        )
        payload = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "taskType": self._task_type,
        }
        try:
            response = self._client.post(
                url,
                json=payload,
                params={"key": self._api_key},
            )
            response.raise_for_status()
            data = response.json()
            values = data.get("embedding", {}).get("values", [])
            if not values:
                raise RuntimeError(
                    f"Gemini embedding API returned empty values. Response: {data}"
                )
            return values
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Embedding model '{self._model}' is no longer available. Set a "
                    "current one and re-index the knowledge base — embeddings from "
                    "different models are not comparable, so the existing index "
                    "cannot be reused."
                ) from e
            if e.response.status_code == 403:
                raise RuntimeError(f"Cannot embed text: {SUSPENDED_KEY_HINT}") from e
            if e.response.status_code == 429:
                raise RuntimeError(
                    "Gemini embedding quota exceeded (HTTP 429). Wait for the free-tier "
                    "quota to reset or use a key with billing enabled."
                ) from e
            body = e.response.text[:200]
            raise RuntimeError(
                f"Gemini Embedding API HTTP {e.response.status_code}: {body}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Gemini embed_one() failed: {e}") from e

    def close(self) -> None:
        self._client.close()
