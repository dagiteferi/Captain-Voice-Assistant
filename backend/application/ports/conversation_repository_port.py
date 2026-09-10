"""Port for conversation persistence."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConversationRepositoryPort(Protocol):
    async def get_trace(self, conversation_id: str):
        ...

    async def save(self, conversation):
        ...
