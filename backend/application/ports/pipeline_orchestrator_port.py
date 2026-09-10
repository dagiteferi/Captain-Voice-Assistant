from dataclasses import dataclass
from typing import Protocol

from domain.conversation.entities import Command, GroundedAnswer
from domain.conversation.value_objects import PipelineStatus
from domain.voice.entities import AudioResponse, Translation


@dataclass
class PipelineOutcome:
    command: Command
    status: PipelineStatus
    grounded_answer: GroundedAnswer | None = None
    translation: Translation | None = None
    audio_response: AudioResponse | None = None
    fallback_reason: str | None = None


class PipelineOrchestratorPort(Protocol):
    async def execute(self, command: Command) -> PipelineOutcome: ...
