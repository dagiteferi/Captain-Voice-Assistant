"""Port for text-to-speech services."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSPort(Protocol):
    async def synthesize(self, text: str, *, voice_id: str | None = None) -> bytes:
        ...
