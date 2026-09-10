"""Local LLM adapter using Ollama."""

from collections.abc import Sequence

import httpx

from application.ports.llm_port import LLMPort
from domain.knowledge.value_objects import ChunkRef


class OllamaAdapter:
    """Adapter for local LLM via Ollama."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url
        self.model = model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a completion using Ollama."""
        prompt = system_prompt or "You are a helpful assistant."
        full_prompt = f"{prompt}\n\n{query}"

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
            return result.get("response", "").strip()
        except Exception as e:
            # Fallback for development when Ollama isn't running
            return f"[Mock LLM response for: {query[:50]}...]"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

