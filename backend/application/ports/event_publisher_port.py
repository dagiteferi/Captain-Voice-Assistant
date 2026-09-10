"""Port for publishing domain events."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventPublisherPort(Protocol):
    async def publish(self, event) -> None:
        ...
