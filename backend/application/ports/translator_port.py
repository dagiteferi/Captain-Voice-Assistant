"""Port for translation services."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TranslatorPort(Protocol):
    async def translate(self, text: str, *, source_language: str, target_language: str) -> str:
        ...
