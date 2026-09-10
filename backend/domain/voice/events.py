from dataclasses import dataclass
from uuid import UUID

from domain.conversation.value_objects import Language
from domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TranslationCompleted(DomainEvent):
    command_id: UUID
    translation_id: UUID
    target_language: Language


@dataclass(frozen=True, kw_only=True)
class AudioSynthesized(DomainEvent):
    command_id: UUID
    audio_response_id: UUID
    voice_profile_id: UUID
