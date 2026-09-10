from typing import Sequence

from application.ports.llm_port import LLMPort
from domain.knowledge.value_objects import ChunkRef


class FakeLLMAdapter(LLMPort):
    """Very small deterministic LLM adapter used for fast local tests.

    Behaviour:
    - If `system_prompt` mentions "relevance grader" returns "RELEVANT".
    - Otherwise returns a short answer that echoes the query and lists chunk ids.
    """

    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str:
        if system_prompt and "relevance grader" in system_prompt.lower():
            return "RELEVANT"

        # Simple grounded answer: include a sentence and the ids of chunks used
        chunk_ids = ", ".join(str(c.chunk_id) for c in chunks[:3])
        return f"Answer (fake): Based on chunks [{chunk_ids}].\nQuery: {query}"
