from typing import Protocol

from domain.conversation.value_objects import Language


class TranslatorPort(Protocol):
    async def translate(
        self,
        text: str,
        target_language: Language,
        *,
        source_language: Language | None = None,
    ) -> str: ...
