"""Port for vector store operations."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VectorStorePort(Protocol):
    async def search(self, query: str, *, limit: int = 5) -> list[dict]:
        ...
