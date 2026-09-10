"""Edge TTS fallback adapter."""


class EdgeTTSAdapter:
    async def synthesize(self, text: str, *, voice_id: str | None = None) -> bytes:
        return text.encode("utf-8")
