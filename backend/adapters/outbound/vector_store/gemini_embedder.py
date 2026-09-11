"""Google Gemini Embedding adapter — uses Gemini Embedding REST API (free tier).

Replaces sentence-transformers (local model download) with the Gemini API.
Same GEMINI_API_KEY as the LLM adapter.
Model: text-embedding-004 (768 dims, free tier)
"""

from __future__ import annotations

import logging

import httpx

from adapters.outbound.vector_store.embedder import TextEmbedder

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiEmbedderAdapter(TextEmbedder):
    """Text embedder via Gemini Embedding API — no local install needed."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
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
            body = e.response.text[:400]
            raise RuntimeError(
                f"Gemini Embedding API HTTP {e.response.status_code}: {body}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Gemini embed_one() failed: {e}") from e

    def close(self) -> None:
        self._client.close()
