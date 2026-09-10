from typing import Protocol

from domain.knowledge.entities import Chunk
from domain.knowledge.value_objects import ChunkRef


class VectorStorePort(Protocol):
    async def search(self, query: str, *, limit: int = 5) -> list[ChunkRef]: ...

    async def upsert(self, chunk: Chunk) -> None: ...
