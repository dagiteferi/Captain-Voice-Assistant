"""Voice and audio domain entities."""

from dataclasses import dataclass, field


@dataclass
class VoiceProfile:
    id: str
    name: str
    language: str = "en"
    voice_settings: dict[str, float] = field(default_factory=dict)


@dataclass
class Translation:
    source_text: str
    target_text: str
    source_language: str
    target_language: str


@dataclass
class AudioResponse:
    text: str
    audio_bytes: bytes
    format: str = "wav"
    voice_id: str | None = None
