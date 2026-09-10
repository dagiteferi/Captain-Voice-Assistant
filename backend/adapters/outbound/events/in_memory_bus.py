"""In-memory event bus for application events."""


class InMemoryBus:
    def __init__(self):
        self._handlers = []

    async def publish(self, event) -> None:
        for handler in self._handlers:
            await handler(event)

    def subscribe(self, handler) -> None:
        self._handlers.append(handler)
