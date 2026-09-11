"""Local LLM adapter using Ollama."""

import logging
from collections.abc import Sequence

import httpx

from application.ports.llm_port import LLMPort
from domain.knowledge.value_objects import ChunkRef

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """Adapter for local LLM via Ollama."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a completion using Ollama.

        Raises RuntimeError if Ollama is unreachable or returns an error,
        so the pipeline trace records a genuine failure rather than a mock answer.
        """
        prompt = system_prompt or "You are a helpful assistant."
        full_prompt = f"{prompt}\n\n{query}"

        logger.info(
            "[ollama] Sending request to %s with model '%s' (prompt len=%d chars)...",
            self.base_url,
            self.model,
            len(full_prompt),
        )

        try:
            response = await self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            text = result.get("response", "").strip()

            if not text:
                raise RuntimeError(
                    f"Ollama returned an empty response for model '{self.model}'. "
                    "Check that the model is pulled and loaded."
                )

            logger.info(
                "[ollama] ✓ Response received. Output len=%d chars.", len(text)
            )
            return text

        except RuntimeError:
            raise
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            ) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"Ollama request timed out (model='{self.model}'). "
                "The model may be loading — try again in a few seconds."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Ollama generate() failed: {e}") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

