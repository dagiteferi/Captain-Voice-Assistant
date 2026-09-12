from __future__ import annotations

import logging

from domain.conversation.value_objects import Language

logger = logging.getLogger(__name__)

_LANG_NAMES = {
    "am": "Amharic",
    "en": "English",
    "fr": "French",
}


class ResilientTranslator:
    """Try the fast primary translator; if it fails, use the LLM. Never stall the demo."""

    def __init__(self, primary, llm=None) -> None:
        self._primary = primary
        self._llm = llm

    async def translate(
        self,
        text: str,
        target_language: Language,
        *,
        source_language: Language | None = None,
    ) -> str:
        source = (source_language.code if source_language else "en").replace("-", "_")
        target = target_language.code.replace("-", "_")
        if source == target or not text.strip():
            return text

        try:
            return await self._primary.translate(
                text, target_language, source_language=source_language
            )
        except Exception as exc:
            logger.warning("Primary translator failed (%s); trying LLM fallback.", exc)

        if self._llm is not None:
            try:
                return await self._via_llm(text, target)
            except Exception as exc:
                logger.warning("LLM translator failed (%s).", exc)

        raise RuntimeError(f"Could not translate to {target}")

    async def _via_llm(self, text: str, target: str) -> str:
        name = _LANG_NAMES.get(target, target)
        prompt = (
            f"Translate the following text into {name}. "
            "Return only the translation, no quotes or notes.\n\n"
            f"{text}"
        )
        result = await self._llm.generate(
            query=prompt,
            chunks=[],
            system_prompt="You are a precise translator.",
        )
        if not result.strip():
            raise RuntimeError("LLM returned an empty translation")
        return result.strip()

    async def aclose(self) -> None:
        if hasattr(self._primary, "aclose"):
            await self._primary.aclose()
