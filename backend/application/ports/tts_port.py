from typing import Protocol

from domain.voice.entities import VoiceProfile


class TTSPort(Protocol):
    async def synthesize(self, text: str, voice_profile: VoiceProfile) -> bytes: ...
