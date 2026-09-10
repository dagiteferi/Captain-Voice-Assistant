"""ElevenLabs voice cloning adapter placeholder."""


class ElevenLabsAdapter:
    async def synthesize(self, text: str, *, voice_id: str | None = None) -> bytes:
        return text.encode("utf-8")
