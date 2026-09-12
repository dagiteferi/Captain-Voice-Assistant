"""Google Gemini LLM adapter — uses Gemini REST API (free tier).

Requires: GEMINI_API_KEY in environment.
No local model installation needed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

import httpx

from application.ports.llm_port import LLMPort
from domain.knowledge.value_objects import ChunkRef

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiLLMAdapter:
    """Adapter for Google Gemini via REST API (free tier)."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Get a free key at https://ai.google.dev/"
            )
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=25.0)

    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a grounded response using Gemini."""
        system = system_prompt or "You are a helpful assistant."

        contents = [
            {"role": "user", "parts": [{"text": f"{system}\n\n{query}"}]}
        ]

        url = f"{GEMINI_API_BASE}/models/{self._model}:generateContent"
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 400,
            },
        }

        logger.info(
            "[gemini] Calling %s (prompt len=%d chars)...",
            self._model,
            len(query),
        )

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    params={"key": self._api_key},
                )
                if response.status_code in (429, 503) and attempt < 2:
                    logger.warning(
                        "[gemini] HTTP %s, retrying (%s/3)...",
                        response.status_code,
                        attempt + 1,
                    )
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError(
                        f"Gemini returned no candidates. Full response: {data}"
                    )

                text = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )

                if not text:
                    raise RuntimeError(
                        "Gemini returned an empty text response. "
                        "Check model availability and API key quota."
                    )

                logger.info("[gemini] ✓ Response: %d chars.", len(text))
                return text
            except RuntimeError:
                raise
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (429, 503) and attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                body = e.response.text[:400]
                raise RuntimeError(
                    f"Gemini API HTTP {e.response.status_code}: {body}"
                ) from e
            except httpx.ConnectError as e:
                raise RuntimeError(
                    "Cannot reach Gemini API. Check network connectivity."
                ) from e
            except Exception as e:
                last_error = e
                raise RuntimeError(f"Gemini generate() failed: {e}") from e

        raise RuntimeError(f"Gemini generate() failed after retries: {last_error}")

    async def aclose(self) -> None:
        await self._client.aclose()
