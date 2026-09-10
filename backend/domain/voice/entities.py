from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.conversation.value_objects import Language
from domain.exceptions import MissingVoiceProfileError


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    language: Language
    id: UUID = field(default_factory=uuid4)


CAPTAIN_PRESET = VoiceProfile(
    id=UUID("00000000-0000-4000-8000-000000000001"),
    name="captain-preset",
    language=Language("en"),
)


@dataclass
class Translation:
    answer_id: UUID
    target_language: Language
    translated_text: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.translated_text.strip():
            raise ValueError("translated text is empty")


@dataclass
class AudioResponse:
    translation_id: UUID
    voice_profile_id: UUID
    audio_path: str
    duration_ms: int = 0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.audio_path.strip():
            raise ValueError("audio_path is required")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")

    @classmethod
    def create(
        cls,
        translation_id: UUID,
        voice_profile: VoiceProfile | None,
        audio_path: str,
        duration_ms: int = 0,
    ) -> "AudioResponse":
        if voice_profile is None:
            raise MissingVoiceProfileError("TTS requires a resolved voice profile")
        return cls(
            translation_id=translation_id,
            voice_profile_id=voice_profile.id,
            audio_path=audio_path,
            duration_ms=duration_ms,
        )
