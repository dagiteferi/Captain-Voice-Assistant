"""Local translation adapter using Argos Translate."""

from domain.conversation.value_objects import Language


class ArgosTranslateAdapter:
    """Adapter for offline translation using Argos Translate."""

    def __init__(self):
        try:
            import argostranslate.package
            import argostranslate.translate
            self.argos = argostranslate.translate
            self.argos_package = argostranslate.package
            # Auto-download language packs on first use if needed
            self._initialized = False
        except ImportError:
            self.argos = None
            self._initialized = False

    async def translate(
        self,
        text: str,
        target_language: Language,
        *,
        source_language: Language | None = None,
    ) -> str:
        """Translate text to target language."""
        if not self.argos:
            # Fallback: return text unchanged if Argos not installed
            return text

        try:
            source = (source_language.code if source_language else "en").replace("-", "_")
            target = target_language.code.replace("-", "_")
            translated = self.argos.translate(text, source, target)
            return translated.strip()
        except Exception:
            # Fallback on any translation error
            return text

