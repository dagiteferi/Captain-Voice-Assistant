from collections.abc import Sequence
from typing import Protocol

from domain.knowledge.value_objects import ChunkRef


class LLMPort(Protocol):
    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str: ...
