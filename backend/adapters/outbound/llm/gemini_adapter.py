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

# Google retires dated model names, and a retired name answers 404. These
# aliases always point at a current model, so they outlive any single release.
# Tried in order when the configured model turns out to be gone.
FALLBACK_MODELS = (
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
)

# A 403 here means the key itself was rejected, not the request.
SUSPENDED_KEY_HINT = (
    "the Gemini API key has been suspended. Create a new key at "
    "https://aistudio.google.com/apikey (or resolve the suspension on the "
    "Google Cloud project) and set GEMINI_API_KEY."
)


class ModelUnavailable(RuntimeError):
    """The named model does not exist or is closed to this key."""


class GeminiLLMAdapter(LLMPort):
    """Adapter for Google Gemini via REST API (free tier)."""

    def __init__(self, api_key: str, model: str = "gemini-flash-latest") -> None:
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
        """Generate a grounded response, surviving a retired model name."""
        system = system_prompt or "You are a helpful assistant."
        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{query}"}]}],
            "generationConfig": {
                "temperature": 0.0,
                # Answers quote short KB facts; 500 only bought unused headroom.
                "maxOutputTokens": 320,
            },
        }

        tried: list[str] = []
        for model in self._candidate_models():
            tried.append(model)
            try:
                text = await self._generate_with(model, payload, len(query))
            except ModelUnavailable as exc:
                logger.warning("[gemini] Model %s unavailable (%s); trying next.", model, exc)
                continue
            if model != self._model:
                # Pin the working name so later calls skip the dead one.
                logger.warning("[gemini] Switched model %s -> %s.", self._model, model)
                self._model = model
            return text

        raise RuntimeError(
            "No Gemini model available. Tried: "
            + ", ".join(tried)
            + ". Set GEMINI_MODEL to a model your key can use "
            "(see https://aistudio.google.com/)."
        )

    def _candidate_models(self) -> list[str]:
        """The configured model first, then the evergreen aliases."""
        return [self._model] + [m for m in FALLBACK_MODELS if m != self._model]

    async def _generate_with(self, model: str, payload: dict, query_len: int) -> str:
        url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
        logger.info("[gemini] Calling %s (prompt len=%d chars)...", model, query_len)

        for attempt in range(3):
            try:
                response = await self._client.post(
                    url, json=payload, params={"key": self._api_key}
                )
                # Overload is transient and worth waiting out; a quota verdict
                # is not — retrying 429 just spends more of an exhausted quota.
                if response.status_code == 503 and attempt < 2:
                    logger.warning("[gemini] HTTP 503, retrying (%s/3)...", attempt + 1)
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"Gemini returned no candidates. Full response: {data}")

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
            except ModelUnavailable:
                raise
            except RuntimeError:
                raise
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 503 and attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                if status == 404:
                    message = e.response.json().get("error", {}).get("message", "")
                    raise ModelUnavailable(message[:200] or f"model {model} not found") from e
                if status == 403:
                    raise RuntimeError(f"Generation refused: {SUSPENDED_KEY_HINT}") from e
                if status == 429:
                    raise RuntimeError(
                        "Gemini quota exceeded (HTTP 429). The free tier allows a "
                        "limited number of requests per day; wait for the quota to "
                        "reset or use a key with billing enabled."
                    ) from e
                raise RuntimeError(
                    f"Gemini API HTTP {status}: {e.response.text[:200]}"
                ) from e
            except httpx.ConnectError as e:
                raise RuntimeError("Cannot reach Gemini API. Check network connectivity.") from e
            except Exception as e:
                raise RuntimeError(f"Gemini generate() failed: {e}") from e

        raise RuntimeError(f"Gemini generate() failed after retries for model {model}")

    async def aclose(self) -> None:
        await self._client.aclose()
