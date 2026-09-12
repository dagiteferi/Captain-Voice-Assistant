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

        # Answer from the chunks only. Echoing the prompt back would make the
        # reply contain the prompt's own "say you do not have it" wording, which
        # the refusal check would then read as a refusal.
        chunk_ids = ", ".join(str(c.chunk_id) for c in chunks[:3])
        excerpt = chunks[0].content.strip().replace("\n", " ")[:200] if chunks else ""
        return f"Answer (fake): {excerpt} [chunks: {chunk_ids}]"
