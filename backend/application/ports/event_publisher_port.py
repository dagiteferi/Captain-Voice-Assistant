from typing import Protocol

from domain.events import DomainEvent


class EventPublisherPort(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
