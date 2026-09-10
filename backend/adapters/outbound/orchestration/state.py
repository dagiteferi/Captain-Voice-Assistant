"""State objects for orchestration workflow execution."""

from dataclasses import dataclass, field
from uuid import UUID

from domain.conversation.entities import GroundedAnswer, Command
from domain.conversation.value_objects import PipelineStatus
from domain.knowledge.value_objects import ChunkRef, RetrievalResult
from domain.voice.entities import AudioResponse, Translation


@dataclass
class PipelineState:
    """Shared state passed through LangGraph nodes."""
    command: Command
    target_language: str
    
    retrieved_chunks: list[ChunkRef] = field(default_factory=list)
    retrieval_attempts: int = 0
    retrieval_relevant: bool = False
    
    grounded_answer: GroundedAnswer | None = None
    
    translation: Translation | None = None
    
    audio_response: AudioResponse | None = None
    
    status: PipelineStatus = PipelineStatus.IN_PROGRESS
    fallback_reason: str | None = None
    
    events: list[object] = field(default_factory=list)

