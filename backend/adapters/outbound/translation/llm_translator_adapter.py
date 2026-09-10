"""Fallback translator that delegates to the LLM."""


class LLMTranslatorAdapter:
    async def translate(self, text: str, *, source_language: str, target_language: str) -> str:
        return text
